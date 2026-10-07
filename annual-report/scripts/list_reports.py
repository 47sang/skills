#!/usr/bin/env python3
"""
list_reports.py - 查询 A 股上市公司定期报告列表（巨潮资讯）

用法：
    python3 list_reports.py 300750                       # 查全部定期报告
    python3 list_reports.py 300750 年度报告              # 只查年报
    python3 list_reports.py 300750 一季报 2026           # 查某年一季报
    python3 list_reports.py 300750 年报                 # 支持简写

与 download_report.py 共用 cninfo_common.py 的过滤逻辑，
确保「看到的候选」和「实际下载的那份」是同一套标准，不会出现
「列表里显示年报、下载却拿到半年报」的情况。
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cninfo_common as cc


def main():
    """
    命令行入口：解析参数、查询并打印报告列表。
    """
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    symbol = args[0]
    keyword_input = args[1] if len(args) > 1 else ""
    year_input = args[2] if len(args) > 2 else ""

    try:
        searchkey = cc.normalize_type(keyword_input) if keyword_input else ""
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    try:
        org_id, stock_name = cc.get_org_info(symbol)
    except cc.ReportError as e:
        print(f"❌ {e}")
        sys.exit(1)

    if year_input:
        start_date = f"{int(year_input) - 1}-12-01"
        end_date = f"{int(year_input) + 1}-12-31"
    else:
        current_year = time.localtime().tm_year
        start_date = f"{current_year - 3}-01-01"
        end_date = f"{current_year + 1}-12-31"

    print(f"正在查询 {symbol}（{stock_name}）的定期报告"
          f"（类型：{searchkey or '全部'}，年份：{year_input or '不限'}）...")

    try:
        candidates = cc.query_reports(
            symbol, org_id, searchkey, start_date, end_date,
            year=year_input or None, stock_name=stock_name,
        )
    except cc.ReportError as e:
        print(f"❌ {e}")
        sys.exit(1)

    if not candidates:
        print("未找到符合条件的报告。")
        sys.exit(0)

    # 按报告年份分组展示，组内按公告时间倒序
    candidates.sort(key=lambda c: (c["year"], -c["ann_time"]), reverse=False)
    candidates.sort(key=lambda c: (c["year"], c["ann_time"]), reverse=False)

    print(f"\n共找到 {len(candidates)} 份报告：\n")
    for i, c in enumerate(candidates, 1):
        ann_date = time.strftime("%Y-%m-%d", time.localtime(c["ann_time"] / 1000)) if c["ann_time"] else "—"
        size_str = f"{c['size_kb']/1024:.1f}MB" if c["size_kb"] >= 1024 else f"{c['size_kb']}KB"
        print(f"[{i}] {c['year']} | 公告日 {ann_date} | {c['title']} | {size_str}")
        print(f"     {c['url']}")

    if searchkey:
        first_year = candidates[0]["year"]
        print("\n--- 下载其中任意一份 ---")
        print(f"  python3 download_report.py {symbol} "
              f"{cc.REPORT_TYPE_NAME[searchkey]} {first_year} \"目标目录/\"")


if __name__ == "__main__":
    main()
