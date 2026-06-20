#!/usr/bin/env python3
"""
read_pdf.py - 读取 A 股年报 PDF 指定页码范围的内容

用法：
    python3 read_pdf.py <PDF路径> [起始页] [结束页] [关键词]
    python3 read_pdf.py "年报.pdf"                # 读全部
    python3 read_pdf.py "年报.pdf" 1 10           # 读第1-10页
    python3 read_pdf.py "年报.pdf" 1 10 主营业务  # 读第1-10页，只返回包含关键词的页
    python3 read_pdf.py "年报.pdf" 1 20 "" 200    # 读第1-20页，关键词为空时返回2000字/页
"""

import sys
import os

try:
    import pdfplumber
except ImportError:
    print("❌ pdfplumber 未安装，请运行: pip install pdfplumber")
    sys.exit(1)


def _read_pdf(pdf_path: str, start_page: int = 1, end_page: int = 0, keyword: str = "", default_chars: int = 2000) -> str:
    """读取 PDF 指定页范围，返回文本内容"""
    if not os.path.exists(pdf_path):
        return f"❌ 文件不存在: {pdf_path}"

    try:
        pdf = pdfplumber.open(pdf_path)
    except Exception as e:
        return f"❌ 无法打开 PDF: {e}"

    total = len(pdf.pages)
    if end_page == 0 or end_page > total:
        end_page = total

    start_page = max(1, start_page)
    if start_page > total:
        pdf.close()
        return f"❌ 起始页 {start_page} 超出总页数 {total}"

    output_parts = []
    output_parts.append(f"📄 PDF: {os.path.basename(pdf_path)} | 总页数: {total} | 读取: 第{start_page}-{end_page}页")
    output_parts.append("=" * 60)

    found_pages = 0
    for i in range(start_page - 1, end_page):
        page = pdf.pages[i]
        text = page.extract_text() or ""

        if keyword:
            if keyword not in text:
                continue
            found_pages += 1
            output_parts.append(f"\n【第 {i+1} 页】 (包含「{keyword}」)")
            output_parts.append("-" * 40)
            # 关键词所在位置附近展开
            idx = text.find(keyword)
            start = max(0, idx - 300)
            end = min(len(text), idx + 1500)
            output_parts.append(text[start:end])
        else:
            output_parts.append(f"\n【第 {i+1} 页】")
            output_parts.append("-" * 40)
            output_parts.append(text[:default_chars])

    output_parts.append("\n" + "=" * 60)
    if keyword:
        output_parts.append(f"关键词「{keyword}」匹配到 {found_pages} 页")
    output_parts.append(f"读取完成: 第{start_page}-{end_page}页 / 共{total}页")

    pdf.close()
    return "\n".join(output_parts)


def main():
    args = sys.argv[1:]
    if not args:
        print("用法：python3 read_pdf.py <PDF路径> [起始页] [结束页] [关键词]")
        print("  python3 read_pdf.py \"年报.pdf\"              # 读全部")
        print("  python3 read_pdf.py \"年报.pdf\" 1 10          # 读第1-10页")
        print("  python3 read_pdf.py \"年报.pdf\" 1 20 主营业务 # 只返回包含关键词的页")
        sys.exit(1)

    pdf_path = args[0]
    start_page = int(args[1]) if len(args) > 1 else 1
    end_page = int(args[2]) if len(args) > 2 else 0
    keyword = args[3] if len(args) > 3 else ""

    result = _read_pdf(pdf_path, start_page, end_page, keyword)
    print(result)


if __name__ == "__main__":
    main()
