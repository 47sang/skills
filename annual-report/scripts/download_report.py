#!/usr/bin/env python3
"""
download_report.py - 下载 A 股定期报告 PDF（巨潮资讯）

用法：
    python3 download_report.py <股票代码> <报告类型> [年份] [保存目录]
    python3 download_report.py 300750 年度报告
    python3 download_report.py 300750 一季报 2026
    python3 download_report.py 300750 年报 2025 /tmp/

不指定年份时默认使用当前年份。
报告类型支持：年度报告、半年度报告、一季度报告、三季度报告（支持简写：年报、半年报、一季报、三季报）
"""

import sys
import os
import re
import requests
import math
from datetime import datetime

# ---------- 配置 ----------
QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
BASE_URL = "http://static.cninfo.com.cn/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}

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

REPORT_TYPE_NAME = {
    "年度报告": "年度报告",
    "半年度报告": "半年度报告",
    "一季度报告": "一季度报告",
    "三季度报告": "三季度报告",
}


def _get_org_id(symbol: str) -> str:
    """
    根据股票代码获取 orgId（巨潮资讯内部标识）。
    优先通过巨潮 topSearch 接口获取，akshare 私有函数已废弃。
    """
    url = "http://www.cninfo.com.cn/new/information/topSearch/query"
    payload = {"keyWord": symbol, "maxNum": 5}
    r = requests.post(url, data=payload, headers=HEADERS, timeout=20)
    r.raise_for_status()
    result = r.json()
    if not result or not isinstance(result, list):
        raise ValueError(f"无法获取 {symbol} 的 orgId，topSearch 返回异常。")
    for item in result:
        if item.get("code") == symbol:
            return item["orgId"]
    raise ValueError(f"无法获取 {symbol} 的 orgId，请手动查询后在脚本中添加映射。")


def _query_reports(symbol: str, org_id: str, searchkey: str, start_date: str, end_date: str, page_size: int = 50) -> list:
    """查询指定关键词的报告列表，返回 [(标题, PDF完整URL, 大小KB, 公告ID), ...]"""
    payload = {
        "pageNum": "1",
        "pageSize": str(page_size),
        "column": "szse",
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
    data = r.json()
    total = int(data.get("totalAnnouncement", 0))
    if total == 0:
        return []

    page_num = math.ceil(total / page_size)
    results = []
    for page in range(1, page_num + 1):
        payload["pageNum"] = str(page)
        r = requests.post(QUERY_URL, data=payload, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        anns = data.get("announcements", [])
        for a in anns:
            title = a.get("announcementTitle", "")
            # 过滤掉摘要、英文版和非报告类公告
            if "摘要" in title:
                continue
            if "英文版" in title:
                continue
            # 半年度报告的标题在巨潮中是"半<em>年度报告</em>"，
            # "半年度报告"被<em>标签打断，需要用正则匹配
            if re.search(r'半(?:<[^>]+>)*年度(?:<[^>]+>)*报告', title):
                continue
            # 过滤各种非报告正文的公告（均含"年度报告"关键字但非正文）
            if "披露提示性公告" in title:
                continue
            if "业绩说明会" in title:
                continue
            if "更正公告" in title:
                continue
            if "董事会决议公告" in title:
                continue
            if "监事会决议公告" in title:
                continue
            if "持续督导年度报告书" in title:
                continue
            if "持续督导" in title:
                continue
            if "监管问询函" in title:
                continue
            if "募集说明书" in title:
                continue
            if "专项核查意见" in title:
                continue
            if "核查意见" in title:
                continue
            url = BASE_URL + a.get("adjunctUrl", "")
            size = int(a.get("adjunctSize", 0) or 0)
            ann_id = a.get("announcementId", "")
            results.append((title, url, size, ann_id))

    # 去重（同一期报告可能返回多份）
    seen = set()
    unique = []
    for item in results:
        key = item[0]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _make_standard_filename(stock_name: str, symbol: str, year: str, report_type_key: str) -> str:
    """生成标准文件名"""
    report_name = REPORT_TYPE_NAME.get(report_type_key, report_type_key)
    return f"{stock_name}_{symbol}_{year}年{report_name}.pdf"


def _find_latest_annual_report(symbol: str, org_id: str) -> tuple:
    """
    查找最新的一份年报（正文，排除摘要），返回 (标题, PDF完整URL, 大小KB, 年份) 或 None。
    """
    # 年报在次年3-4月发布，搜索范围跨两个年度以覆盖
    from datetime import datetime
    current_year = datetime.now().year
    start_date = f"{current_year - 2}-01-01"
    end_date = f"{current_year + 1}-12-31"
    reports = _query_reports(symbol, org_id, "年度报告", start_date, end_date)
    if not reports:
        return None
    # 取最新一份（_query_reports 已按公告时间倒序）
    title, pdf_url, size_kb, _ = reports[0]
    # 从标题中提取年份
    import re
    m = re.search(r"(\d{4})年", title.replace("<em>", "").replace("</em>", ""))
    year = m.group(1) if m else str(current_year)
    return (title, pdf_url, size_kb, year)


def _download_file(url: str, dest_path: str) -> tuple:
    """下载文件到指定路径，返回 (成功?, 实际大小KB)"""
    try:
        r = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=60, stream=True)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        size = os.path.getsize(dest_path)
        return True, size
    except Exception as e:
        # 清理不完整文件
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False, str(e)


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("用法：python3 download_report.py <股票代码> <报告类型> [年份] [保存目录]")
        print("  报告类型：年报/年度报告/半年报/半年度报告/一季报/一季度报告/三季报/三季度报告")
        print("  示例：python3 download_report.py 300750 年报")
        print("  示例：python3 download_report.py 300750 一季报 2026")
        print("  示例：python3 download_report.py 300750 年报 2025 /tmp/")
        print("  不指定年份时默认使用当前年份。")
        sys.exit(1)

    symbol = args[0]
    report_type_input = args[1]
    save_dir = "/tmp"
    year = None

    # 智能解析可选参数：年份是纯数字，保存目录是路径
    if len(args) > 2:
        if args[2].isdigit():
            year = args[2]
            if len(args) > 3:
                save_dir = args[3]
        else:
            # 第三个参数是保存目录，年份留空
            save_dir = args[2]

    # 标准化报告类型
    searchkey = KEYWORD_MAP.get(report_type_input, report_type_input)
    if searchkey not in REPORT_TYPE_NAME:
        print(f"❌ 不支持的报告类型: {report_type_input}")
        print(f"   支持的类型: 年报、半年报、一季报、三季报（或完整名称）")
        sys.exit(1)

    report_type_key = searchkey

    # 获取 orgId
    try:
        org_id = _get_org_id(symbol)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # 日期范围：指定年份则限定，不指定则用极宽范围覆盖全部历史（取最新公布）
    if year:
        start_date = f"{year}-01-01"
        end_date = f"{int(year)+1}-12-31"
    else:
        start_date = "2000-01-01"
        end_date = "2099-12-31"

    year_display = year if year else "不限年份（最新）"
    print(f"正在查询 {symbol} {year_display}{report_type_key}...")
    reports = _query_reports(symbol, org_id, searchkey, start_date, end_date)

    if not reports:
        print(f"❌ 未找到 {symbol} {year_display}{report_type_key} 的报告")
        sys.exit(1)

    if len(reports) > 1:
        print(f"找到 {len(reports)} 份相关报告，取最新的一份：")
        for i, (title, url, size, _) in enumerate(reports):
            size_str = f"{size/1024:.1f}MB" if size >= 1024 else f"{size}KB"
            print(f"  [{i+1}] {title} ({size_str})")
        title, pdf_url, size_kb, _ = reports[0]
    else:
        title, pdf_url, size_kb, _ = reports[0]
        size_str = f"{size_kb/1024:.1f}MB" if size_kb >= 1024 else f"{size_kb}KB"
        print(f"找到报告: {title} ({size_str})")

    # 获取股票名称
    try:
        from akshare.stock_fundamental.stock_notice import __get_stock_json
        mapping = __get_stock_json(symbol)
        stock_name = None
        for k, v in mapping.items():
            if v == org_id:
                stock_name = k
                break
        if not stock_name:
            clean_title = title.replace("<em>", "").replace("</em>", "")
            m = re.match(r"^(.+?)(\d{4}年)", clean_title)
            if m:
                candidate = m.group(1)
                if not re.match(r"^\d{4}年$", candidate):
                    stock_name = candidate
    except Exception:
        stock_name = None

    if not stock_name:
        try:
            import akshare as ak
            profile = ak.stock_profile_cninfo(symbol=symbol)
            if not profile.empty:
                stock_name = profile.iloc[0].get("A股简称", symbol)
        except Exception:
            pass

    if not stock_name:
        stock_name = symbol

    # 从标题提取年份（不指定年份时从公告标题中取）
    if not year:
        clean_title = title.replace("<em>", "").replace("</em>", "")
        m = re.search(r"(\d{4})年", clean_title)
        year = m.group(1) if m else str(datetime.now().year)

    # 生成标准文件名
    std_filename = _make_standard_filename(stock_name, symbol, year, report_type_key)
    dest_path = os.path.join(save_dir, std_filename)

    # 如果文件已存在且大小一致，跳过
    if os.path.exists(dest_path):
        existing_size = os.path.getsize(dest_path)
        if abs(existing_size - size_kb * 1024) < 1024:
            print(f"⏭ 文件已存在且大小一致，跳过下载: {dest_path}")
        else:
            print(f"⚠ 文件已存在但大小不一致（已有 {existing_size/1024:.1f}KB，远程 {size_kb}KB），将重新下载")
            ok, result = _download_file(pdf_url, dest_path)
            if not ok:
                print(f"❌ 下载失败: {result}")
                sys.exit(1)
            actual_size = result if isinstance(result, int) else os.path.getsize(dest_path)
            print(f"✅ 下载完成: {dest_path} ({actual_size/1024:.1f}KB)")
            print(f"   文件名: {std_filename}")
    else:
        print(f"正在下载: {pdf_url}")
        print(f"保存到: {dest_path}")
        ok, result = _download_file(pdf_url, dest_path)
        if not ok:
            print(f"❌ 下载失败: {result}")
            sys.exit(1)
        actual_size = result if isinstance(result, int) else os.path.getsize(dest_path)
        print(f"✅ 下载完成: {dest_path} ({actual_size/1024:.1f}KB)")
        print(f"   文件名: {std_filename}")

    # 连带下载最新年报（如果本地尚未有）
    annual = _find_latest_annual_report(symbol, org_id)
    if annual:
        annual_title, annual_url, annual_size_kb, annual_year = annual
        annual_filename = _make_standard_filename(stock_name, symbol, annual_year, "年度报告")
        annual_dest = os.path.join(save_dir, annual_filename)
        if os.path.exists(annual_dest):
            existing_size = os.path.getsize(annual_dest)
            if abs(existing_size - annual_size_kb * 1024) < 1024:
                print(f"\n⏭ 最新年报已存在，跳过: {annual_filename}")
            else:
                print(f"\n⚠ 最新年报已存在但大小不一致，重新下载: {annual_filename}")
                ok2, result2 = _download_file(annual_url, annual_dest)
                if ok2:
                    print(f"✅ 年报下载完成: {annual_dest} ({result2/1024:.1f}KB)")
                else:
                    print(f"❌ 年报下载失败: {result2}")
        else:
            print(f"\n正在连带下载最新年报: {annual_title}")
            ok2, result2 = _download_file(annual_url, annual_dest)
            if ok2:
                print(f"✅ 年报下载完成: {annual_dest} ({result2/1024:.1f}KB)")
                print(f"   文件名: {annual_filename}")
            else:
                print(f"❌ 年报下载失败: {result2}")


if __name__ == "__main__":
    main()
