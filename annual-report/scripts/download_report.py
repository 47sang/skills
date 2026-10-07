#!/usr/bin/env python3
"""
download_report.py - 下载 A 股定期报告 PDF（巨潮资讯）

用法：
    单只：
    python3 download_report.py <股票代码> <报告类型> [年份] [保存目录]
    python3 download_report.py 300750 年报
    python3 download_report.py 300750 一季报 2026
    python3 download_report.py 300750 年报 2025 /tmp/

    批量：
    python3 download_report.py --batch <清单文件> [选项]
    python3 download_report.py --batch todo.json --types 年报,一季报 --base-dir /path/年报PDF
    python3 download_report.py --batch todo.json --types 半年报 --check-only

不指定年份时默认使用当前年份；不指定年份的批量任务取「最新公布」的一期。

清单文件为 JSON 数组，每项形如：
    [{"name": "宁德时代", "symbol": "300750"}, ...]
仅写 symbol 也可以，name 会自动用巨潮官方简称补齐：
    ["300750", "300308", ...]

设计说明（相对旧版的修复点见 cninfo_common.py 顶部注释）：
  - 「年度报告」与「半年度报告」的子串混淆已修复，去高亮标签后再做双向排除
  - 港股重复披露的「港股公告：XXXX年报」已排除，不再下到无文字层的扫描版
  - 指定年份时按标题年份精确筛选，筛选无命中直接报「未找到」，不再静默回退
  - 公司简称取自巨潮 topSearch 接口，不再依赖 akshare 私有函数
  - column 参数按交易所自动选择，沪市/科创板不再漏结果
  - 每份 PDF 下载后用 pdftotext 校验首页标题，校验不通过自动换候选并删除错文件
  - 新增 --batch 批量模式：一份清单可覆盖上百家公司，支持仅补缺失、强制重下、只检查不下载
"""

import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cninfo_common as cc


def _resolve_targets(items):
    """
    把清单里的每一项解析为 (公司简称, 证券代码)。

    入参 items：dict 列表、字符串列表，或二者混合。
    返回：解析成功的 (name, symbol) 列表。
    异常：某项无法解析时抛 ValueError，由调用方决定跳过还是整体失败。
    """
    out = []
    for it in items:
        if isinstance(it, str):
            out.append((None, it.strip()))
        elif isinstance(it, dict):
            symbol = str(it.get("symbol") or it.get("code") or "").strip()
            name = (it.get("name") or it.get("stock_name") or "").strip() or None
            if not symbol:
                raise ValueError(f"清单项缺少股票代码：{it}")
            out.append((name, symbol))
        else:
            raise ValueError(f"清单项格式无法识别：{it!r}")
    return out


def _batch(args):
    """
    批量下载入口。

    入参 args：argparse 解析后的命名空间，需含 batch/types/base_dir/force/check_only/interval。
    返回：进程退出码，0 表示全部成功或有据可查的失败，1 表示清单不可用。
    """
    try:
        with open(args.batch, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        print(f"❌ 读取清单失败：{e}")
        return 1
    if isinstance(raw, dict):
        raw = raw.get("items") or raw.get("stocks") or []
    if not isinstance(raw, list) or not raw:
        print("❌ 清单为空或格式不是数组")
        return 1

    try:
        targets = _resolve_targets(raw)
        report_keys = cc.parse_types(args.types)
    except ValueError as e:
        print(f"❌ {e}")
        return 1

    years = [args.year] if args.year else [str(time.localtime().tm_year), str(time.localtime().tm_year - 1)]

    base_dir = args.base_dir
    if not base_dir:
        print("❌ 批量模式必须用 --base-dir 指定公司目录的父目录")
        return 1

    print(f"批量任务：{len(targets)} 家公司 × 报告类型 {report_keys} × 年份 {years}")
    if args.check_only:
        print("模式：仅检查（不下载），用于盘点缺失")
    print("-" * 72)

    ok_count = miss_count = err_count = 0
    records = []
    for idx, (name, symbol) in enumerate(targets, 1):
        try:
            org_id, official_name = cc.get_org_info(symbol)
        except cc.ReportError as e:
            print(f"[{idx}/{len(targets)}] {symbol} ❌ {e}")
            err_count += 1
            records.append({"symbol": symbol, "name": name, "error": str(e)})
            continue

        final_name = name or official_name
        # 简称不一致时提示但不阻断：本地目录名以用户既有命名为准
        note = ""
        if name and official_name and name != official_name:
            note = f"（巨潮现用简称「{official_name}」）"

        dest_dir = os.path.join(base_dir, final_name)
        statuses = []
        for rk in report_keys:
            for year in years:
                if args.check_only:
                    fn = cc.make_filename(final_name, symbol, year, rk)
                    path = os.path.join(dest_dir, fn)
                    if os.path.exists(path):
                        statuses.append((rk, year, "exists", fn))
                    else:
                        statuses.append((rk, year, "missing", fn))
                    continue
                try:
                    res = cc.fetch_report(
                        symbol, org_id, rk, year, dest_dir,
                        stock_name=final_name, verify=not args.no_verify, force=args.force,
                    )
                    statuses.append((rk, year, res["status"], res["message"]))
                except cc.ReportError as e:
                    statuses.append((rk, year, "error", str(e)))
                time.sleep(args.interval)

        marks = {"downloaded": "✅", "exists": "⏭", "missing": "❓",
                 "not_found": "➖", "verify_failed": "⚠️", "error": "❌"}
        line = " ".join(f"{marks.get(s, '?')}{rk[:2]}{year}:{s}" for rk, year, s, _ in statuses)
        print(f"[{idx}/{len(targets)}] {final_name}({symbol}) {note} {line}")

        for rk, year, st, msg in statuses:
            if st in ("downloaded", "exists"):
                ok_count += 1
            elif st in ("not_found", "missing"):
                miss_count += 1
            else:
                err_count += 1
            records.append({"symbol": symbol, "name": final_name, "type": rk,
                            "year": year, "status": st, "message": msg})

    print("-" * 72)
    print(f"汇总：成功/已存在 {ok_count}，缺失或巨潮无 {miss_count}，异常 {err_count}")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=1)
        print(f"明细已写入：{args.report}")

    if err_count:
        print("\n异常明细：")
        for r in records:
            if r.get("status") in ("error", "verify_failed"):
                print(f"  ❌ {r.get('name')}({r.get('symbol')}) {r.get('type')}{r.get('year', '')}: {r.get('message') or r.get('error')}")
    return 0


def _single(args):
    """
    单只股票下载入口。

    入参 args：argparse 解析后的命名空间。
    返回：进程退出码。
    """
    try:
        report_key = cc.normalize_type(args.report_type)
    except ValueError as e:
        print(f"❌ {e}")
        return 1

    try:
        org_id, official_name = cc.get_org_info(args.symbol)
    except cc.ReportError as e:
        print(f"❌ {e}")
        return 1

    stock_name = args.name or official_name
    if args.name and official_name and args.name != official_name:
        print(f"ℹ️  本地命名为「{args.name}」，巨潮现用简称为「{official_name}」")

    year = args.pos_year
    if not year:
        # 不指定年份：年报取最新一期的实际年份，季报取当前年份
        if report_key == "年度报告":
            found = cc.find_latest_annual(args.symbol, org_id, stock_name)
            if not found:
                print(f"❌ 未找到 {args.symbol} 的年度报告")
                return 1
            year = found
        else:
            year = str(time.localtime().tm_year)

    print(f"正在下载 {stock_name}({args.symbol}) {year}年{cc.REPORT_TYPE_NAME[report_key]}...")
    try:
        res = cc.fetch_report(
            args.symbol, org_id, report_key, year, args.save_dir,
            stock_name=stock_name, verify=not args.no_verify, force=args.force,
        )
    except cc.ReportError as e:
        print(f"❌ {e}")
        return 1

    marks = {"downloaded": "✅", "exists": "⏭ 已存在，跳过下载",
             "not_found": "➖", "verify_failed": "⚠️"}
    print(f"{marks.get(res['status'], '?')} {res['message']}")
    if res["status"] in ("downloaded", "exists"):
        print(f"   保存位置：{res['path']}")
        if res["status"] == "downloaded":
            pages = _page_count(res["path"])
            if pages:
                print(f"   页数：{pages}")
    return 0 if res["status"] in ("downloaded", "exists", "not_found") else 1


def _page_count(pdf_path):
    """
    读取 PDF 总页数，失败返回 None。

    入参 pdf_path：PDF 路径。
    返回：页数 int，读取失败为 None。
    """
    try:
        proc = subprocess.run(["pdfinfo", pdf_path], capture_output=True, timeout=60)
        for line in proc.stdout.decode("utf-8", "ignore").splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        pass
    return None


def main():
    """
    命令行入口，解析参数并分发到单只或批量模式。
    """
    parser = argparse.ArgumentParser(
        description="下载 A 股定期报告 PDF（巨潮资讯）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("symbol", nargs="?", help="股票代码，如 300750")
    parser.add_argument("report_type", nargs="?", help="年报/半年报/一季报/三季报")
    parser.add_argument("pos_year", nargs="?", help="报告年份，如 2025；不填取最新")
    parser.add_argument("save_dir", nargs="?", default="/tmp", help="保存目录，默认 /tmp")
    parser.add_argument("--name", help="公司简称；不填自动取巨潮官方简称")
    parser.add_argument("--force", action="store_true", help="文件已存在时强制重新下载")
    parser.add_argument("--no-verify", action="store_true", help="跳过 PDF 首页标题校验")
    parser.add_argument("--batch", metavar="清单.json", help="批量模式：JSON 清单路径")
    parser.add_argument("--types", help="批量模式的报告类型，逗号分隔，默认 年报,一季报")
    parser.add_argument("--year", help="批量模式的目标报告年份；不填则当年+去年各查一次")
    parser.add_argument("--base-dir", help="批量模式的父目录，每家公司建一个子文件夹")
    parser.add_argument("--check-only", action="store_true", help="批量模式只检查缺失、不下载")
    parser.add_argument("--interval", type=float, default=0.35, help="批量模式每份之间的间隔秒数")
    parser.add_argument("--report", help="把批量结果明细写入 JSON 文件")
    args = parser.parse_args()

    if args.batch:
        return _batch(args)
    if not args.symbol or not args.report_type:
        parser.print_help()
        return 1
    return _single(args)


if __name__ == "__main__":
    sys.exit(main())
