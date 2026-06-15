#!/usr/bin/env python3
"""
从 Java 源文件中提取待翻译的注释，输出为 JSON。

用法:
    python3 extract_comments.py <文件列表.txt> <输出comments.json> [--yaml]

文件列表.txt 每行一个文件的绝对路径。
输出的 JSON 是一个数组，每个元素:
    {
      "id": "C00000",
      "file": "相对项目根的路径",
      "type": "javadoc" | "inline",
      "start": 起始行号(从1开始),
      "end":   结束行号(从1开始),
      "indent": "    ",          # 仅 javadoc，用于重建时的缩进
      "source": "原文..."
    }

设计原则:
- 已包含中文字符的文件整体跳过（视为已翻译）。
- License 头部（前 20 行内的 Copyright / Apache License / 链接）跳过。
- 只提取注释文本，不碰代码、字符串字面量。
"""

import argparse
import json
import os
import re
import sys

HAS_CHINESE = re.compile(r"[一-鿿]")


def has_chinese(text: str) -> bool:
    return bool(HAS_CHINESE.search(text))


def is_license_line(line: str, idx: int) -> bool:
    """判断某一行是否属于文件顶部的 License 头部。"""
    if idx >= 20:
        return False
    s = line.strip()
    if s.startswith("/*") or s.startswith("*"):
        return True
    markers = (
        "Copyright",
        "Licensed under the Apache License",
        "http://www.apache.org/licenses",
        "limitations under the License",
        "distributed under the License",
    )
    return any(m in s for m in markers)


def find_inline_comment_pos(line: str) -> int:
    """返回 // 在字符串字面量之外的位置，找不到返回 -1。"""
    in_str = False
    str_char = None
    for i, ch in enumerate(line):
        if ch in ('"', "'") and (i == 0 or line[i - 1] != "\\"):
            if not in_str:
                in_str = True
                str_char = ch
            elif str_char == ch:
                in_str = False
                str_char = None
        elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/" and not in_str:
            return i
    return -1


def _content_after_star(line: str) -> str:
    """返回行内第一个 '*' 之后的内容（去行尾空白，保留行首空白）。
    保留行首空白对 Javadoc 里的 <pre>{@code} 代码块缩进至关重要。
    '     *     code'  -> '     code'
    '     * @param x'  -> ' @param x'
    '     *'           -> ''
    """
    idx = line.find("*")
    if idx == -1:
        return line.strip()
    return line[idx + 1 :].rstrip()


def extract_javadoc_inner(jd_lines):
    """
    把 Javadoc 块（含 /** 与 */）折算成纯文本内容行。
    每行保留 '*' 之后的内容（含代码缩进所需的前导空格）。
    单行 Javadoc / /** 紧跟文本 / 文本紧贴 */ 均兼容。
    """
    n = len(jd_lines)
    raws = [l.rstrip("\n") for l in jd_lines]

    # 单行 Javadoc: /** text */
    if n == 1 and "/**" in raws[0] and "*/" in raws[0]:
        seg = raws[0].split("/**", 1)[1]
        seg = seg.rsplit("*/", 1)[0].strip()
        return [seg] if seg else []

    inner = []
    # 第一行: /** [text]
    first_after = raws[0].split("/**", 1)[1]
    if "*/" in first_after:
        first_after = first_after.split("*/")[0]
    first_text = first_after.rstrip()
    if first_text:
        inner.append(first_text)
    # 中间行: 保留 * 之后的内容（含前导空格）
    for k in range(1, n - 1):
        inner.append(_content_after_star(raws[k]))
    # 最后行: [text] */
    last_before = raws[-1].rsplit("*/", 1)[0]
    last_content = _content_after_star(last_before)
    if last_content:
        inner.append(last_content)

    # 去掉首尾空内容行
    while inner and inner[0].strip() == "":
        inner.pop(0)
    while inner and inner[-1].strip() == "":
        inner.pop()
    return inner


def extract_java_file(filepath: str, project_root: str):
    comments = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return comments

    full = "".join(lines)
    if has_chinese(full):
        return comments  # 整个文件已含中文，跳过

    rel = os.path.relpath(filepath, project_root)
    i = 0
    while i < len(lines):
        line = lines[i]

        if is_license_line(line, i):
            i += 1
            continue

        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # ---- Javadoc 块 ----
        if "/**" in line:
            after_open = line.split("/**", 1)[1]
            # 单行 Javadoc: /** text */ （同行闭合，不能误吞后续代码）
            if "*/" in after_open:
                if not has_chinese(line):
                    inner = extract_javadoc_inner([line])
                    if inner:
                        indent = line[: len(line) - len(line.lstrip())]
                        comments.append(
                            {
                                "id": f"C{len(comments):05d}",
                                "file": rel,
                                "type": "javadoc",
                                "start": i + 1,
                                "end": i + 1,
                                "indent": indent,
                                "source": "\n".join(inner),
                            }
                        )
                i += 1
                continue

            # 多行 Javadoc
            block = [line]
            j = i + 1
            closed = False
            while j < len(lines):
                block.append(lines[j])
                if "*/" in lines[j]:
                    j += 1
                    closed = True
                    break
                j += 1

            if closed:
                full_block = "".join(block)
                if not has_chinese(full_block):
                    inner = extract_javadoc_inner(block)
                    if inner:  # 跳过空注释 /** */
                        indent = line[: len(line) - len(line.lstrip())]
                        comments.append(
                            {
                                "id": f"C{len(comments):05d}",
                                "file": rel,
                                "type": "javadoc",
                                "start": i + 1,
                                "end": j,
                                "indent": indent,
                                "source": "\n".join(inner),
                            }
                        )
                i = j
                continue

        # ---- 行内注释 ----
        cpos = find_inline_comment_pos(line)
        if cpos >= 0:
            text = line[cpos + 2 :].rstrip("\n")
            if text.strip() and not has_chinese(text):
                comments.append(
                    {
                        "id": f"C{len(comments):05d}",
                        "file": rel,
                        "type": "inline",
                        "start": i + 1,
                        "end": i + 1,
                        "indent": "",
                        "source": text,
                    }
                )

        i += 1

    return comments


def extract_yaml_file(filepath: str, project_root: str):
    """YAML 只提取注释行（以 # 开头），跳过已含中文的行。"""
    comments = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return comments

    rel = os.path.relpath(filepath, project_root)
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("#"):
            text = s[1:].strip()
            if text and not has_chinese(text):
                comments.append(
                    {
                        "id": f"C{len(comments):05d}",
                        "file": rel,
                        "type": "yaml",
                        "start": i + 1,
                        "end": i + 1,
                        "indent": "",
                        "source": text,
                    }
                )
    return comments


def main():
    ap = argparse.ArgumentParser(description="提取 Java/YAML 注释为 JSON")
    ap.add_argument("file_list", help="文件列表 txt，每行一个绝对路径")
    ap.add_argument("output", help="输出 JSON 路径")
    ap.add_argument("--root", default=os.getcwd(), help="项目根目录（用于计算相对路径）")
    ap.add_argument("--yaml", action="store_true", help="同时处理 yaml/yml 文件")
    args = ap.parse_args()

    if not os.path.exists(args.file_list):
        print(f"文件列表不存在: {args.file_list}", file=sys.stderr)
        sys.exit(1)

    with open(args.file_list, "r") as f:
        files = [ln.strip() for ln in f if ln.strip()]

    all_comments = []
    scanned = translated = 0
    for fp in files:
        if not os.path.exists(fp):
            continue
        scanned += 1
        if fp.endswith(".java"):
            cs = extract_java_file(fp, args.root)
        elif args.yaml and fp.endswith((".yaml", ".yml")):
            cs = extract_yaml_file(fp, args.root)
        else:
            continue
        if cs:
            all_comments.extend(cs)
        else:
            translated += 1  # 已含中文，跳过

    # 重新编号（全局连续）
    for idx, c in enumerate(all_comments):
        c["id"] = f"C{idx:05d}"

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_comments, f, ensure_ascii=False, indent=1)

    total = len(all_comments)
    print(f"扫描文件: {scanned}")
    print(f"已含中文跳过: {translated}")
    print(f"待翻译注释条数: {total}")
    by_type = {}
    for c in all_comments:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
    for t, n in sorted(by_type.items()):
        print(f"  {t}: {n}")
    print(f"输出: {args.output}")


if __name__ == "__main__":
    main()
