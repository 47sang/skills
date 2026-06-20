#!/usr/bin/env python3
"""
list_reports.py - 查询 A 股上市公司定期报告列表（巨潮资讯）
用法：
    python3 list_reports.py <股票代码> [关键词] [年份]
    python3 list_reports.py 300750                # 查全部定期报告
    python3 list_reports.py 300750 年度报告       # 只查年报
    python3 list_reports.py 300750 一季报 2026    # 查某年一季报
    python3 list_reports.py 300750 年报           # 支持简写
"""
import sys
import json
import math
import requests
import pandas as pd

# ---------- 配置 ----------
QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}

# 关键词映射：支持简写
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

# ---------- 工具函数 ----------

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


def _query_cninfo(symbol: str, org_id: str, searchkey: str = "", start_date: str = "", end_date: str = "", page_size: int = 100) -> pd.DataFrame:
    """调用巨潮资讯 hisAnnouncement/query 接口获取公告列表"""
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
        "seDate": f"{start_date}~{end_date}" if start_date and end_date else "",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    r = requests.post(QUERY_URL, data=payload, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    total = int(data.get("totalAnnouncement", 0))
    if total == 0:
        return pd.DataFrame()

    page_num = math.ceil(total / page_size)
    frames = []
    for page in range(1, page_num + 1):
        payload["pageNum"] = str(page)
        r = requests.post(QUERY_URL, data=payload, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        anns = data.get("announcements", [])
        if not anns:
            break
        df = pd.DataFrame(anns)
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    big = pd.concat(frames, ignore_index=True)
    big["公告时间"] = pd.to_datetime(big["announcementTime"], unit="ms", errors="coerce").dt.strftime("%Y-%m-%d")
    big["公告链接"] = (
        "http://www.cninfo.com.cn/"
        + big["adjunctUrl"].astype(str)
    )
    big["PDF链接"] = (
        "http://static.cninfo.com.cn/"
        + big["adjunctUrl"].astype(str)
    )
    big["文件大小KB"] = pd.to_numeric(big["adjunctSize"], errors="coerce").fillna(0).astype(int)
    big = big.rename(columns={
        "announcementTitle": "公告标题",
        "announcementId": "公告ID",
        "adjunctType": "文件类型",
    })
    return big[["公告时间", "公告标题", "文件类型", "文件大小KB", "PDF链接", "公告链接"]]


# ---------- 主逻辑 ----------

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    symbol = args[0]
    keyword_input = args[1] if len(args) > 1 else ""
    year_input = args[2] if len(args) > 2 else ""

    # 关键词标准化
    searchkey = KEYWORD_MAP.get(keyword_input, keyword_input) if keyword_input else ""

    # 日期范围：不指定年份时不限年份，直接取最新公布
    if year_input:
        start_date = f"{year_input}-01-01"
        end_date = f"{int(year_input)+1}-12-31"
    else:
        # 不限年份，取最新公布
        start_date = ""
        end_date = ""

    try:
        org_id = _get_org_id(symbol)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(f"正在查询 {symbol} 的定期报告列表（关键词: {searchkey or '全部'}, 年份: {year_input or '近两年'}）...")

    df = _query_cninfo(
        symbol=symbol,
        org_id=org_id,
        searchkey=searchkey,
        start_date=start_date,
        end_date=end_date,
        page_size=100,
    )

    if df.empty:
        print("未找到符合条件的报告。")
        sys.exit(0)

    # 先去掉高亮标签再过滤
    df["公告标题_raw"] = df["公告标题"].str.replace(r"<em>", "", regex=False).str.replace(r"</em>", "", regex=False)

    # 进一步按标题精确过滤（排除摘要，区分年度/半年度，年份对齐）
    if searchkey:
        if searchkey == "年度报告":
            mask = df["公告标题_raw"].str.contains("年度报告", na=False) & ~df["公告标题_raw"].str.contains("半年度", na=False)
            # 如果指定了年份，标题中的年份应为该年份（年报在次年发布，标题年份=报告年份）
            if year_input:
                mask = mask & df["公告标题_raw"].str.contains(f"{year_input}年", na=False)
        elif searchkey == "半年度报告":
            mask = df["公告标题_raw"].str.contains("半年度报告", na=False)
            if year_input:
                mask = mask & df["公告标题_raw"].str.contains(f"{year_input}年", na=False)
        elif searchkey == "一季度报告":
            mask = df["公告标题_raw"].str.contains("一季度报告", na=False)
            if year_input:
                mask = mask & df["公告标题_raw"].str.contains(f"{year_input}年", na=False)
        elif searchkey == "三季度报告":
            mask = df["公告标题_raw"].str.contains("三季度报告", na=False)
            if year_input:
                mask = mask & df["公告标题_raw"].str.contains(f"{year_input}年", na=False)
        else:
            mask = df["公告标题_raw"].str.contains(searchkey, na=False)
        # 排除摘要（保留正文）
        mask = mask & ~df["公告标题_raw"].str.contains("摘要", na=False)
        df = df[mask].copy()
    else:
        # 无关键词时也排除摘要
        df = df[~df["公告标题_raw"].str.contains("摘要", na=False)].copy()

    # 清理临时列（如果存在）
    if "公告标题_raw" in df.columns:
        df = df.drop(columns=["公告标题_raw"])

    # 排序：按公告时间降序
    df = df.sort_values("公告时间", ascending=False).reset_index(drop=True)

    print(f"\n共找到 {len(df)} 份报告：\n")
    for i, row in df.iterrows():
        title = row["公告标题"]
        date = row["公告时间"]
        size_kb = row["文件大小KB"]
        size_mb = size_kb / 1024
        pdf_url = row["PDF链接"]
        idx = i + 1
        size_str = f"{size_mb:.1f}MB" if size_mb >= 1 else f"{size_kb}KB"
        print(f"[{idx}] {date} | {title} | {size_str}")
        print(f"     {pdf_url}")

    # 输出供 download_report.py 使用的编号映射
    print("\n--- 供 download_report.py 使用 ---")
    for i, row in df.iterrows():
        print(f"  [{i+1}] {row['公告标题']} | {row['PDF链接']}")


if __name__ == "__main__":
    main()
