#!/usr/bin/env python3
"""
fetch_stock_data.py - 获取 A 股股票基本面数据（akshare）

用法：
    python3 fetch_stock_data.py <股票代码>
    python3 fetch_stock_data.py 300750

输出：公司简介 + 核心财务数据（利润表/资产负债表/现金流量表）+ 实时行情
"""

import sys
import json
import warnings
import pandas as pd

warnings.filterwarnings("ignore")

# ---------- 工具函数 ----------

def _safe_get(df: pd.DataFrame, label: str) -> str:
    """从 DataFrame 的 index 或 column 中查找值"""
    if df is None or df.empty:
        return "N/A"
    # 尝试 index 匹配
    if label in df.index:
        row = df.loc[label]
        if hasattr(row, 'iloc'):
            return str(row.iloc[0])
        return str(row)
    # 尝试 column 匹配
    for col in df.columns:
        if label in str(col):
            return str(df[col].iloc[0])
    return "N/A"


def _fmt(val) -> str:
    """格式化数值"""
    if val is None or val == "N/A" or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        v = float(val)
        if abs(v) >= 1e8:
            return f"{v/1e8:.2f}亿"
        elif abs(v) >= 1e4:
            return f"{v/1e4:.2f}万"
        else:
            return f"{v:.2f}"
    except (ValueError, TypeError):
        return str(val)


# ---------- 主要逻辑 ----------

def fetch_stock_data(symbol: str) -> dict:
    import akshare as ak

    result = {"股票代码": symbol, "error": None}

    # 1. 公司基本信息
    try:
        profile = ak.stock_profile_cninfo(symbol=symbol)
        if not profile.empty:
            row = profile.iloc[0]
            result["公司名称"] = row.get("公司名称", "N/A")
            result["A股简称"] = row.get("A股简称", "N/A")
            result["所属行业"] = row.get("所属行业", "N/A")
            result["成立日期"] = row.get("成立日期", "N/A")
            result["上市日期"] = row.get("上市日期", "N/A")
            result["法人代表"] = row.get("法人代表", "N/A")
            result["主营业务"] = row.get("主营业务", "N/A")
    except Exception as e:
        result["公司信息_error"] = str(e)

    # 2. 财务数据（利润表）
    for report_fn, report_name in [
        ("stock_profit_sheet_by_report_em", "利润表"),
        ("stock_balance_sheet_by_report_em", "资产负债表"),
        ("stock_cash_flow_sheet_by_report_em", "现金流量表"),
    ]:
        try:
            fn = getattr(ak, report_fn)
            df = fn(symbol=symbol)
            if not df.empty:
                # 取最新一期（第一行）和上一期（第二行）
                latest = df.iloc[0]
                prev = df.iloc[1] if len(df) > 1 else None
                result[report_name] = {
                    "报告期": str(latest.name) if hasattr(latest, 'name') else "最新",
                    "最新一期": {str(idx): str(val) for idx, val in latest.items()},
                }
                if prev is not None:
                    result[report_name]["上一期"] = {str(idx): str(val) for idx, val in prev.items()}
        except Exception as e:
            result[f"{report_name}_error"] = str(e)

    # 3. 实时行情
    try:
        spot = ak.stock_zh_a_spot_em()
        row = spot[spot["代码"] == symbol]
        if not row.empty:
            r = row.iloc[0]
            for col in ["最新价", "涨跌幅", "成交量", "成交额", "市盈率-动态", "市净率", "总市值", "流通市值"]:
                if col in r:
                    result[col] = str(r[col])
    except Exception as e:
        result["行情_error"] = str(e)

    return result


def main():
    args = sys.argv[1:]
    if not args:
        print("用法：python3 fetch_stock_data.py <股票代码>")
        sys.exit(1)

    symbol = args[0]
    print(f"正在获取 {symbol} 的数据...")

    data = fetch_stock_data(symbol)

    if data.get("error"):
        print(f"❌ 错误: {data['error']}")
        sys.exit(1)

    # 格式化输出
    lines = []
    lines.append(f"股票代码: {data.get('股票代码', symbol)}")
    lines.append(f"公司名称: {data.get('公司名称', 'N/A')}")
    lines.append(f"A股简称: {data.get('A股简称', 'N/A')}")
    lines.append(f"所属行业: {data.get('所属行业', 'N/A')}")
    lines.append(f"成立日期: {data.get('成立日期', 'N/A')}")
    lines.append(f"上市日期: {data.get('上市日期', 'N/A')}")
    lines.append(f"主营业务: {data.get('主营业务', 'N/A')}")

    # 财务数据摘要
    for report_name in ["利润表", "资产负债表", "现金流量表"]:
        if report_name in data:
            report = data[report_name]
            lines.append(f"\n--- {report_name} ---")
            lines.append(f"报告期: {report.get('报告期', 'N/A')}")
            if "最新一期" in report:
                for k, v in list(report["最新一期"].items())[:15]:
                    lines.append(f"  {k}: {_fmt(v)}")

    # 行情
    if "最新价" in data:
        lines.append(f"\n--- 实时行情 ---")
        for key in ["最新价", "涨跌幅", "成交量", "成交额", "市盈率-动态", "市净率", "总市值"]:
            if key in data:
                lines.append(f"  {key}: {data[key]}")

    print("\n".join(lines))

    # 同时输出 JSON（供程序处理）
    json_path = f"/tmp/{symbol}_stock_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n完整数据已保存到: {json_path}")


if __name__ == "__main__":
    main()
