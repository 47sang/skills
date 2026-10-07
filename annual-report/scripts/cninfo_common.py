#!/usr/bin/env python3
"""
cninfo_common.py — 巨潮资讯定期报告的查询、筛选、下载与校验公共逻辑

被 download_report.py 与 list_reports.py 共用，避免两处逻辑各自漂移。

本模块修复了历史上导致批量下载系统性出错的几类缺陷：
  1. 搜「年度报告」时混入「半年度报告」——「年度报告」是「半年度报告」的子串，
     且巨潮返回的标题带 <em> 高亮标签会把「半年度」与「报告」打断，直接
     子串匹配失效，必须先去标签再做「半年度」排除。
  2. 港股与 A 股双重上市的沪深公司（如中芯国际 688981）会同时挂出
     「港股公告：2025年年报」，该文件常为无文字层的扫描版、体积远大于
     A 股正文，若按「最新一份」或「体积最大」选取会下错文件。
  3. 指定年份但按公告时间倒序取第一条 → 下到相邻年份的报告。
     旧实现年份筛选无命中时会静默回退到未筛选列表，等于没筛。
  4. 「一季度报告」与「第一季度报告」两种写法并存，只匹配前者会漏。
  5. 公司简称依赖 akshare 私有函数 __get_stock_json，版本升级即失效。
     改为直接用巨潮 topSearch 接口返回的 zwjc 字段。
  6. column 参数写死 szse，沪市/科创板标的可能漏结果。
  7. 只看公告标题不校验 PDF 首页，仍可能把半年报、摘要、提示性公告
     当成年报存进库。本模块提供 verify_cover_page() 做二次校验。
"""

import os
import re
import shutil
import subprocess
import sys
import time

import requests

# ---------- 接口地址与请求头 ----------

QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
TOPSEARCH_URL = "http://www.cninfo.com.cn/new/information/topSearch/query"
PDF_BASE_URL = "http://static.cninfo.com.cn/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}

# 巨潮接口偶发抖动，重试次数与间隔
RETRY_TIMES = 3
RETRY_SLEEP = 1.5

# ---------- 报告类型 ----------

# 报告类型简写 → 巨潮 searchkey
KEYWORD_MAP = {
    "年报": "年度报告",
    "年度": "年度报告",
    "年度报告": "年度报告",
    "半年报": "半年度报告",
    "半年度": "半年度报告",
    "半年度报告": "半年度报告",
    "一季报": "一季度报告",
    "一季度": "一季度报告",
    "一季度报告": "一季度报告",
    "三季报": "三季度报告",
    "三季度": "三季度报告",
    "三季度报告": "三季度报告",
}

# 报告类型 → 文件名与校验用的中文标识
REPORT_TYPE_NAME = {
    "年度报告": "年度报告",
    "半年度报告": "半年度报告",
    "一季度报告": "一季度报告",
    "第三季度报告": "三季度报告",
}

# 标题里出现这些片段的公告一律不是定期报告正文，必须排除。
# 覆盖：摘要、英文版、非正文类临时公告、港股重复披露。
EXCLUDE_TOKENS = [
    "摘要",
    "英文版",
    "英文",
    "提示性公告",
    "披露的提示",
    "披露提示性公告",
    "业绩说明会",
    "更正公告",
    "更正后",
    "补充公告",
    "董事会决议",
    "监事会决议",
    "股东会决议",
    "股东大会决议",
    "持续督导",
    "监管问询",
    "问询函",
    "关注函",
    "募集说明书",
    "招股说明书",
    "专项核查",
    "核查意见",
    "审计报告",
    "内部控制",
    "履职报告",
    "社会责任",
    "独立董事",
    "港股公告",
    "H股公告",
    "香港联合交易所",
    "境外上市",
]


class ReportError(Exception):
    """查询或下载过程中的可预期错误，调用方应捕获后记录，不中断整批任务。"""


# ---------- 基础工具 ----------


def clean_title(title):
    """
    去掉巨潮返回标题中的 <em> 高亮标签。

    入参 title：巨潮 announcementTitle 原始字符串，可能含 <em>/</em>。
    返回：去除标签后的纯文本标题。

    不去标签会导致「半年度」「一季度」等关键词匹配全部失效，这是历史 bug 的根因之一。
    """
    return re.sub(r"<[^>]+>", "", title or "")


def normalize_type(report_type_input):
    """
    把用户输入的报告类型简写标准化为巨潮 searchkey。

    入参 report_type_input：如「年报」「一季报」「半年度报告」。
    返回：标准化后的 key（年度报告/半年度报告/一季度报告/第三季度报告）之一。
    异常：类型不受支持时抛 ValueError。
    """
    key = KEYWORD_MAP.get(report_type_input, report_type_input)
    if key not in REPORT_TYPE_NAME:
        raise ValueError(
            f"不支持的报告类型：{report_type_input}；"
            f"可选：年报、半年报、一季报、三季报（或完整中文名称）"
        )
    return key


def detect_column(symbol):
    """
    按证券代码判断应使用哪个 column 参数查询巨潮。

    入参 symbol：6 位证券代码字符串。
    返回：'sse'（沪市主板/科创板）、'szse'（深市）、'bjse'（北交所）。

    历史实现写死 'szse'，沪市与科创板标的会漏结果。实测两者的返回条数
    多处一致，但保持正确取值可避免接口调整后突然失效。
    """
    if symbol.startswith(("688", "689", "787")):
        return "sse"
    if symbol.startswith(("600", "601", "603", "605", "900")):
        return "sse"
    if symbol.startswith(("4", "8", "92")):
        return "bjse"
    return "szse"


def get_org_info(symbol):
    """
    查询某证券代码在巨潮的 orgId 与官方简称。

    入参 symbol：6 位证券代码字符串。
    返回：(org_id, stock_name) 二元组，stock_name 为巨潮登记的证券简称。
    异常：查不到时抛 ReportError。

    不再使用 akshare 私有函数 __get_stock_json——它是下划线开头的内部实现，
    akshare 升级即可能消失，改为直接调用巨潮 topSearch 接口。
    """
    last_err = None
    for attempt in range(RETRY_TIMES):
        try:
            r = requests.post(
                TOPSEARCH_URL,
                data={"keyWord": symbol, "maxNum": 5},
                headers=HEADERS,
                timeout=20,
            )
            r.raise_for_status()
            result = r.json()
            if not isinstance(result, list) or not result:
                raise ValueError("topSearch 返回空结果")
            for item in result:
                if item.get("code") == symbol:
                    return item["orgId"], item.get("zwjc") or symbol
            raise ValueError(f"topSearch 结果中没有代码 {symbol}")
        except Exception as e:  # 网络抖动与解析异常一并重试
            last_err = e
            if attempt < RETRY_TIMES - 1:
                time.sleep(RETRY_SLEEP)
    raise ReportError(f"无法获取 {symbol} 的 orgId：{last_err}")


# ---------- 查询 ----------


def _query_page(symbol, org_id, searchkey, column, start_date, end_date, page_num, page_size):
    """
    请求巨潮 hisAnnouncement/query 接口的指定页。

    入参：symbol 证券代码、org_id 巨潮内部标识、searchkey 检索关键词、
    column 板块参数、start_date/end_date 日期区间（YYYY-MM-DD）、
    page_num 页码（从 1 开始）、page_size 每页条数。
    返回：接口返回的原始 dict。
    """
    payload = {
        "pageNum": str(page_num),
        "pageSize": str(page_size),
        "column": column,
        "tabName": "fulltext",
        "plate": "",
        "stock": f"{symbol},{org_id}",
        "searchkey": searchkey,
        "secid": "",
        "category": "",
        "trade": "",
        "seDate": f"{start_date}~{end_date}",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    r = requests.post(QUERY_URL, data=payload, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def _query_once(symbol, org_id, searchkey, start_date, end_date, page_size=50):
    """
    在指定 column 下检索全部匹配公告，不做任何业务过滤。

    入参：symbol、org_id、searchkey、start_date、end_date、page_size。
    返回：公告 dict 列表（未过滤、未去重）。
    异常：接口连续失败时抛 ReportError。
    """
    column = detect_column(symbol)
    last_err = None
    for attempt in range(RETRY_TIMES):
        try:
            first = _query_page(symbol, org_id, searchkey, column, start_date, end_date, 1, page_size)
            total = int(first.get("totalAnnouncement", 0) or 0)
            if total == 0:
                # 板块参数可能选错，回落到另一板块重试一次，避免漏结果
                alt = "szse" if column == "sse" else "sse"
                first = _query_page(symbol, org_id, searchkey, alt, start_date, end_date, 1, page_size)
                total = int(first.get("totalAnnouncement", 0) or 0)
                if total == 0:
                    return []
            announcements = list(first.get("announcements") or [])
            page_count = (total + page_size - 1) // page_size
            for page in range(2, page_count + 1):
                data = _query_page(symbol, org_id, searchkey, column, start_date, end_date, page, page_size)
                announcements.extend(data.get("announcements") or [])
                time.sleep(0.2)
            return announcements
        except Exception as e:
            last_err = e
            if attempt < RETRY_TIMES - 1:
                time.sleep(RETRY_SLEEP)
    raise ReportError(f"{symbol} 查询公告失败：{last_err}")


def query_reports(symbol, org_id, searchkey, start_date, end_date, year=None, stock_name=None):
    """
    查询并过滤出指定报告类型的正文公告。

    入参：
      symbol       证券代码
      org_id       巨潮 orgId
      searchkey    报告类型（年度报告/半年度报告/一季度报告/第三季度报告）
      start_date   检索起始日 YYYY-MM-DD
      end_date     检索结束日 YYYY-MM-DD
      year         目标报告年份，None 表示不限年份（取最新公布）
      stock_name   公司简称，用于给候选排序，正文标题通常含该简称
    返回：候选列表，每项为 {'title','year','url','size_kb','ann_time'}，按可信度排序。
    """
    announcements = _query_once(symbol, org_id, searchkey, start_date, end_date)

    candidates = []
    seen = set()
    for a in announcements:
        title = clean_title(a.get("announcementTitle", ""))
        if not title or title in seen:
            continue
        # 排除摘要、英文版、决议公告、港股重复披露等一切非正文公告
        if any(tok in title for tok in EXCLUDE_TOKENS):
            continue
        # 搜年报时排除半年报；搜半年报时排除年报。两者互为子串，必须双向限定。
        if searchkey == "年度报告" and "半年度" in title:
            continue
        if searchkey == "半年度报告" and "半年度报告" not in title:
            continue
        # 季报存在「一季度报告」与「第一季度报告」两种官方写法
        if searchkey == "一季度报告" and "一季度" not in title and "第一季度" not in title:
            continue
        if searchkey == "第三季度报告" and "三季度" not in title and "第三季度" not in title:
            continue

        m = re.search(r"(\d{4})\s*年", title)
        if not m:
            continue
        report_year = m.group(1)
        if year is not None and report_year != year:
            continue

        seen.add(title)
        candidates.append(
            {
                "title": title,
                "year": report_year,
                "url": PDF_BASE_URL + a.get("adjunctUrl", ""),
                "size_kb": int(a.get("adjunctSize", 0) or 0),
                "ann_time": a.get("announcementTime", 0) or 0,
            }
        )

    # 排序规则：标题含公司简称的通常是正文（如「中芯国际2025年年度报告」），
    # 不含的多为泛化标题；同优先级下取公告时间早的（同一期报告的初版），
    # 长度短者优先（正文标题不会带大量补充说明后缀）。
    candidates.sort(
        key=lambda c: (0 if stock_name and stock_name in c["title"] else 1, len(c["title"]), c["ann_time"])
    )
    return candidates


# ---------- 下载与校验 ----------


def download_pdf(url, dest_path):
    """
    下载 PDF 到指定路径，先写 .part 临时文件再原子替换，避免中断留下半截文件。

    入参 url：PDF 直链（static.cninfo.com.cn 域）。
    返回：落地文件的字节数。
    异常：下载失败时抛 ReportError，且已清理临时文件。
    """
    last_err = None
    for attempt in range(RETRY_TIMES):
        tmp_path = dest_path + ".part"
        try:
            r = requests.get(
                url,
                headers={"User-Agent": HEADERS["User-Agent"]},
                timeout=180,
                stream=True,
            )
            r.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            os.replace(tmp_path, dest_path)
            return os.path.getsize(dest_path)
        except Exception as e:
            last_err = e
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if attempt < RETRY_TIMES - 1:
                time.sleep(RETRY_SLEEP)
    raise ReportError(f"下载失败 {url}：{last_err}")


def has_pdftotext():
    """
    检查系统是否装有 poppler 的 pdftotext 命令。

    返回：True 表示可用，False 表示不可用（此时应跳过首页校验并明确告警）。
    """
    return shutil.which("pdftotext") is not None


def verify_cover_page(pdf_path, expect_year, report_key, max_pages=3):
    """
    校验 PDF 首页确实是目标年份、目标类型的报告正文。

    入参：
      pdf_path     PDF 路径
      expect_year  期望的报告年份，如 '2025'
      report_key   报告类型（年度报告/半年度报告/一季度报告/第三季度报告）
      max_pages    最多读取前几页文本
    返回：(是否通过, 失败原因)。通过时原因为 'OK'。

    两个必须处理的细节：
      1. 巨潮 PDF 首页常在数字与「年」之间插空格（「2026 年第一季度报告」），
         校验前必须去掉所有空白字符，否则会误判为「首页未含 2026 年」。
      2. 个别公司的封面是中英双语设计版式（如中信证券），年份字样可能晚到
         第 4~5 页才出现，因此不能只看第 1 页。
    """
    try:
        proc = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", "-l", str(max_pages), pdf_path, "-"],
            capture_output=True,
            timeout=180,
        )
    except Exception as e:
        return False, f"pdftotext 执行失败：{e}"
    text = proc.stdout.decode("utf-8", "ignore")
    if not text.strip():
        return False, "首页无文字层（可能是扫描版）"
    head = re.sub(r"\s+", "", text)

    if f"{expect_year}年" not in head:
        return False, f"前 {max_pages} 页未出现 {expect_year} 年"
    if report_key == "年度报告":
        if "年度报告" not in head:
            return False, "未出现「年度报告」字样"
        if "半年度报告" in head:
            return False, "出现「半年度报告」，是半年报"
    elif report_key == "半年度报告":
        if "半年度报告" not in head:
            return False, "未出现「半年度报告」字样"
    elif report_key == "一季度报告":
        if "一季度" not in head and "第一季度" not in head:
            return False, "未出现「一季度」字样"
    elif report_key == "第三季度报告":
        if "三季度" not in head and "第三季度" not in head:
            return False, "未出现「三季度」字样"
    return True, "OK"


def fetch_report(symbol, org_id, report_key, year, dest_dir, stock_name=None, verify=True, force=False):
    """
    下载单只股票的指定一期报告，下载后自动做首页校验，校验不通过则删除并换下一个候选。

    入参：
      symbol      证券代码
      org_id      巨潮 orgId
      report_key  报告类型（年度报告/半年度报告/一季度报告/第三季度报告）
      year        报告年份，如 '2025'
      dest_dir    落地目录
      stock_name  公司简称，用于文件命名；None 时回退为股票代码
      verify      是否做首页校验，系统无 pdftotext 时自动降级为不做校验
      force       目标文件已存在时是否强制重新下载
    返回：结果 dict，字段 {'status','path','message'}，status 取值
      'downloaded' 已下载并通过校验、'exists' 已存在且跳过、
      'skipped' 已存在但 force=False、'not_found' 巨潮无该期报告、
      'verify_failed' 候选全部校验不通过。
    """
    name = stock_name or symbol
    filename = f"{name}_{symbol}_{year}年{REPORT_TYPE_NAME[report_key]}.pdf"
    dest_path = os.path.join(dest_dir, filename)
    os.makedirs(dest_dir, exist_ok=True)

    if os.path.exists(dest_path) and not force:
        return {"status": "exists", "path": dest_path, "message": "已存在，跳过"}

    # 年报在次年 3~4 月披露，检索区间必须跨年
    start_date = f"{int(year) - 1}-12-01"
    end_date = f"{int(year) + 1}-12-31"
    candidates = query_reports(symbol, org_id, report_key, start_date, end_date, year=year, stock_name=name)
    if not candidates:
        return {"status": "not_found", "path": dest_path, "message": f"巨潮无 {year} 年{REPORT_TYPE_NAME[report_key]}"}

    do_verify = verify and has_pdftotext()
    tried = []
    for cand in candidates[:3]:  # 最多试 3 个候选，避免在异常公司上无限重试
        size = download_pdf(cand["url"], dest_path)
        if not do_verify:
            return {
                "status": "downloaded",
                "path": dest_path,
                "message": f"{cand['title'][:30]}（{size // 1024}KB，未做首页校验）",
            }
        ok, why = verify_cover_page(dest_path, year, report_key)
        if ok:
            return {"status": "downloaded", "path": dest_path, "message": f"{cand['title'][:30]}（{size // 1024}KB）"}
        os.remove(dest_path)
        tried.append(f"{cand['title'][:24]}→{why}")

    return {"status": "verify_failed", "path": dest_path, "message": "；".join(tried)}


def find_latest_annual(symbol, org_id, stock_name=None):
    """
    查找该股票最新一期年度报告的年份（不下载）。

    入参：symbol、org_id、stock_name。
    返回：年份字符串，如 '2025'；查不到返回 None。
    """
    current_year = time.localtime().tm_year
    cands = query_reports(
        symbol, org_id, "年度报告",
        f"{current_year - 3}-01-01", f"{current_year + 1}-12-31",
        stock_name=stock_name,
    )
    if not cands:
        return None
    return cands[0]["year"]


def make_filename(stock_name, symbol, year, report_key):
    """
    生成符合命名规范的完整文件名（含 .pdf）。

    入参：stock_name 公司简称、symbol 证券代码、year 报告年份、report_key 报告类型。
    返回：形如「宁德时代_300750_2025年年度报告.pdf」的字符串。
    """
    return f"{stock_name}_{symbol}_{year}年{REPORT_TYPE_NAME[report_key]}.pdf"


# ---------- 命令行辅助 ----------


def parse_types(types_arg):
    """
    把逗号分隔的报告类型参数解析为 searchkey 列表。

    入参 types_arg：如 '年报,一季报'；None 或空串时返回默认的年报+一季报。
    返回：searchkey 列表。
    异常：含不受支持类型时抛 ValueError。
    """
    if not types_arg:
        return ["年度报告", "一季度报告"]
    out = []
    for t in types_arg.replace("，", ",").split(","):
        t = t.strip()
        if not t:
            continue
        out.append(normalize_type(t))
    if not out:
        return ["年度报告", "一季度报告"]
    return out
