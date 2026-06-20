#!/usr/bin/env python3
"""
从 Python 源文件中提取待翻译的注释与文档字符串，输出为 JSON。

用法:
    python3 extract_comments.py <文件列表.txt> <输出comments.json> [--root <项目根>]

文件列表.txt 每行一个文件的绝对路径。
输出的 JSON 是一个数组，每个元素:
    {
      "id": "C00000",
      "file": "相对项目根的路径",
      "type": "module_docstring" | "class_docstring" | "function_docstring" | "inline",
      "start": 起始行号(从1开始),
      "end": 结束行号(从1开始),
      "indent": "    ",        # 仅 docstring，用于重建时的缩进
      "source": "原文...",
      "prefix": "",            # 仅 docstring，原始前缀如 "r" 或 "R"
      "docstring_style": ""   # 仅 docstring: "single" | "multi"
    }

设计原则:
- 使用 Python AST 精确定位文档字符串，绝不误伤赋值语句中的字符串字面量。
- 已包含中文字符的文件整体跳过（视为已翻译）。
- License 头部（前 20 行内的版权/许可声明）跳过。
- # pragma: no cover / # type: ignore / # TODO: 等特殊注释在提取阶段过滤。
- 注释掉的 Python 代码行（包含赋值、字典/列表字面量、函数调用等代码语法）在提取阶段过滤。
- 只提取注释文本，不碰代码、字符串字面量（非 docstring）。
"""

import argparse
import ast
import json
import os
import re
import sys

HAS_CHINESE = re.compile(r"[一-鿿]")
SPECIAL_INLINE_RE = re.compile(
    r"^\s*(?:pragma:\s*no\s*cover|type:\s*ignore|TODO|FIXME|HACK|noqa)",
    re.IGNORECASE,
)
LICENSE_MARKERS = (
    "Copyright",
    "Licensed under the",
    "http://www.apache.org/licenses",
    "MIT License",
    "BSD License",
    "GNU General Public License",
    "All rights reserved",
    "Permission is hereby granted",
)


def has_chinese(text: str) -> bool:
    return bool(HAS_CHINESE.search(text))


def is_license_line(line: str, idx: int) -> bool:
    if idx >= 20:
        return False
    stripped = line.strip()
    if stripped.startswith("#"):
        return True
    if stripped.startswith("/*") or stripped.startswith("*"):
        return True
    return any(m in stripped for m in LICENSE_MARKERS)


def is_special_inline_comment(text: str) -> bool:
    return bool(SPECIAL_INLINE_RE.match(text))


COMMENTED_CODE_RE = re.compile(
    r"(?:"
    r"[\{\}\[\]]"  # 包含 {}[] 等代码字面量符号 → 几乎肯定是代码
    r"|^\s*[A-Za-z_][\w.]*\s*="  # 以 Python 赋值语句开头（identifier = value）
    r"|(?:^|\s)[A-Za-z_][\w.]*\.[A-Za-z_]\w*\s*\("  # obj.method( 或 self.attr( 点号调用
    r")"
)


def is_commented_code(text: str) -> bool:
    """检测是否为注释掉的 Python 代码行（而非普通说明性注释）。"""
    return bool(COMMENTED_CODE_RE.search(text))


def find_docstring_info(node, source_lines):
    """从 AST 节点提取文档字符串信息。"""
    if not hasattr(node, "body") or not node.body:
        return None

    first_stmt = node.body[0]

    # 仅处理 Expr(Constant(str)) — 排除赋值等
    if not isinstance(first_stmt, ast.Expr):
        return None
    if not isinstance(first_stmt.value, ast.Constant):
        return None
    if not isinstance(first_stmt.value.value, str):
        return None

    start_line = first_stmt.lineno
    end_line = first_stmt.end_lineno

    if start_line is None or end_line is None:
        return None

    start_0 = start_line - 1
    end_0 = end_line - 1

    first_line = source_lines[start_0]
    last_line = source_lines[end_0]

    # 提取前缀（r, R, u, U）
    prefix = ""
    stripped_first = first_line.strip()
    m = re.match(r'^(?P<prefix>[rRuU]?)"""', stripped_first)
    if not m:
        m = re.match(r"^(?P<prefix>[rRuU]?)'''", stripped_first)
    if m:
        prefix = m.group("prefix")

    # 计算缩进
    indent = first_line[: len(first_line) - len(first_line.lstrip())]

    # 提取纯文本内容
    content = _extract_docstring_content(
        first_line, last_line, start_0, end_0, source_lines
    )

    if not content.strip():
        return None

    docstring_style = "single" if start_line == end_line else "multi"

    return {
        "start": start_line,
        "end": end_line,
        "prefix": prefix,
        "indent": indent,
        "content": content,
        "docstring_style": docstring_style,
    }


def _extract_docstring_content(first_line, last_line, start_0, end_0, source_lines):
    """从文档字符串的首行和末行提取纯文本内容。"""
    q1 = first_line.find('"""')
    if q1 == -1:
        q1 = first_line.find("'''")
    if q1 == -1:
        return ""

    after_open = first_line[q1 + 3 :]

    q2 = after_open.find('"""')
    if q2 == -1:
        q2 = after_open.find("'''")

    if q2 != -1:
        # 单行文档字符串
        return after_open[:q2].strip()
    else:
        # 多行文档字符串
        inner_lines = []

        first_content = after_open.rstrip()
        if first_content.strip():
            inner_lines.append(first_content)

        for idx in range(start_0 + 1, end_0):
            inner_lines.append(source_lines[idx].rstrip("\n"))

        q_close = last_line.rfind('"""')
        if q_close == -1:
            q_close = last_line.rfind("'''")
        if q_close != -1:
            last_content = last_line[:q_close].rstrip()
            if last_content.strip():
                inner_lines.append(last_content)

        if not inner_lines:
            return ""

        raw = "\n".join(inner_lines)
        lines = raw.split("\n")
        non_empty = [ln for ln in lines if ln.strip()]
        if non_empty:
            min_indent = min(len(ln) - len(ln.lstrip()) for ln in non_empty)
            if min_indent > 0:
                lines = [ln[min_indent:] if len(ln) >= min_indent else ln for ln in lines]
        # 去掉每行前导空格（重建时统一用 " * " 前缀）
        lines = [ln.lstrip() for ln in lines]
        return "\n".join(lines)


def extract_docstrings_from_file(filepath, project_root):
    """提取文件中的所有文档字符串。"""
    comments = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return comments

    if has_chinese(source):
        return comments

    rel = os.path.relpath(filepath, project_root)

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return comments

    source_lines = source.split("\n")
    _seen: set = set()

    def _process(node, scope_type):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if id(node) not in _seen:
                _seen.add(id(node))
                info = find_docstring_info(node, source_lines)
                if info:
                    comments.append({
                        "id": f"C{len(comments):05d}",
                        "file": rel,
                        "type": f"{scope_type}_docstring",
                        "start": info["start"],
                        "end": info["end"],
                        "indent": info["indent"],
                        "source": info["content"],
                        "prefix": info["prefix"],
                        "docstring_style": info["docstring_style"],
                    })
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                _process(child, "class")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _process(child, "function")

    _process(tree, "module")
    return comments


def _find_hash_outside_string(line: str) -> int:
    in_str = False
    str_char = None
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and in_str:
            i += 2
            continue
        if ch in ('"', "'") and not in_str:
            if line[i : i + 3] in ('"""', "'''"):
                in_str = not in_str
                str_char = line[i : i + 3]
                i += 3
                continue
            in_str = True
            str_char = ch
            i += 1
            continue
        if in_str and ch == str_char:
            if line[i : i + 3] == str_char and len(str_char) == 3:
                in_str = False
                str_char = None
                i += 3
                continue
            if len(str_char) == 1:
                in_str = False
                str_char = None
                i += 1
                continue
        if ch == "#" and not in_str:
            return i
        i += 1
    return -1


def extract_inline_comments(filepath, project_root):
    """提取文件中的 # 行内注释。"""
    comments = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return comments

    if has_chinese("".join(lines)):
        return comments

    rel = os.path.relpath(filepath, project_root)

    for i, line in enumerate(lines):
        if is_license_line(line, i):
            continue
        stripped = line.strip()
        if not stripped:
            continue

        cpos = _find_hash_outside_string(line)
        if cpos >= 0:
            comment_text = line[cpos + 1 :].rstrip("\n").lstrip()
            if comment_text.strip() and not has_chinese(comment_text):
                if is_special_inline_comment(comment_text):
                    continue
                if is_commented_code(comment_text):
                    continue
                indent = line[: len(line) - len(line.lstrip())]
                comments.append({
                    "id": f"C{len(comments):05d}",
                    "file": rel,
                    "type": "inline",
                    "start": i + 1,
                    "end": i + 1,
                    "indent": indent,
                    "source": comment_text,
                })

    return comments


def extract_python_file(filepath, project_root):
    docstrings = extract_docstrings_from_file(filepath, project_root)
    inlines = extract_inline_comments(filepath, project_root)
    return docstrings + inlines


def main():
    ap = argparse.ArgumentParser(
        description="提取 Python 文件中的注释（docstring + # 行内注释）为 JSON"
    )
    ap.add_argument("file_list", help="文件列表 txt，每行一个绝对路径")
    ap.add_argument("output", help="输出 JSON 路径")
    ap.add_argument("--root", default=os.getcwd(), help="项目根目录")
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
        if not fp.endswith(".py"):
            continue
        scanned += 1
        comments = extract_python_file(fp, args.root)
        if comments:
            all_comments.extend(comments)
        else:
            translated += 1

    for idx, c in enumerate(all_comments):
        c["id"] = f"C{idx:05d}"

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_comments, f, ensure_ascii=False, indent=1)

    total = len(all_comments)
    print(f"扫描文件: {scanned}")
    print(f"已含中文/跳过: {translated}")
    print(f"待翻译注释条数: {total}")
    by_type = {}
    for c in all_comments:
        t = c["type"]
        by_type[t] = by_type.get(t, 0) + 1
    for t, n in sorted(by_type.items()):
        print(f"  {t}: {n}")
    print(f"输出: {args.output}")


if __name__ == "__main__":
    main()
