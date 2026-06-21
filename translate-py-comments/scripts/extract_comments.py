#!/usr/bin/env python3
"""
extract_comments v2 —— 修复两个 bug:
1. 漏译条件块(if/try/for/with)内的 docstring: 改用 ast.walk 遍历所有层级。
2. URL 锚点 # 被误判为注释 #: inline 提取时跳过 URL 锚点。
"""

import argparse
import ast
import json
import os
import re
import sys

HAS_CHINESE = re.compile(r"[一-鿿]")
SPECIAL_INLINE_RE = re.compile(
    r"^\s*(?:pragma:\s*no\s*cover|type:\s*ignore|TODO|FIXME|HACK|noqa|no\s*inspection)",
    re.IGNORECASE,
)
LICENSE_MARKERS = (
    "Copyright", "Licensed under the",
    "http://www.apache.org/licenses", "MIT License", "BSD License",
    "GNU General Public License", "All rights reserved",
    "Permission is hereby granted",
)


def has_chinese(text: str) -> bool:
    return bool(HAS_CHINESE.search(text))


def is_license_line(line: str, idx: int) -> bool:
    if idx >= 20:
        return False
    stripped = line.strip()
    # shebang 与编码声明始终跳过(不应翻译)
    if stripped.startswith("#!") or (stripped.startswith("#") and "coding" in stripped):
        return True
    # 注释风格开头且含 license 标志词才视为 license 行
    # (避免误跳 # TODO / # 配置说明 等合法行内注释)
    if stripped.startswith(("#", "/*", "*")):
        return any(m in stripped for m in LICENSE_MARKERS)
    return False


def is_special_inline_comment(text: str) -> bool:
    return bool(SPECIAL_INLINE_RE.match(text))


COMMENTED_CODE_RE = re.compile(
    r"(?:"
    r"[\{\}\[\]]"
    r"|^\s*[A-Za-z_][\w.]*\s*="
    r"|(?:^|\s)[A-Za-z_]\w*\.[A-Za-z_]\w*\s*\("
    r")"
)


def is_commented_code(text: str) -> bool:
    return bool(COMMENTED_CODE_RE.search(text))


def find_docstring_info(node, source_lines):
    if not hasattr(node, "body") or not node.body:
        return None
    first_stmt = node.body[0]
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

    prefix = ""
    stripped_first = first_line.strip()
    m = re.match(r'^(?P<prefix>[rRuU]?)"""', stripped_first)
    if not m:
        m = re.match(r"^(?P<prefix>[rRuU]?)'''", stripped_first)
    if m:
        prefix = m.group("prefix")

    indent = first_line[: len(first_line) - len(first_line.lstrip())]
    content = _extract_docstring_content(first_line, last_line, start_0, end_0, source_lines)
    if not content.strip():
        return None

    docstring_style = "single" if start_line == end_line else "multi"
    return {
        "start": start_line, "end": end_line, "prefix": prefix,
        "indent": indent, "content": content, "docstring_style": docstring_style,
    }


def _extract_docstring_content(first_line, last_line, start_0, end_0, source_lines):
    q1 = first_line.find('"""')
    if q1 == -1:
        q1 = first_line.find("'''")
    if q1 == -1:
        return ""
    after_open = first_line[q1 + 3:]
    q2 = after_open.find('"""')
    if q2 == -1:
        q2 = after_open.find("'''")
    if q2 != -1:
        return after_open[:q2].strip()

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
    lines = [ln.lstrip() for ln in lines]
    return "\n".join(lines)


def extract_docstrings_from_file(filepath, project_root):
    """v2: 用 ast.walk 提取所有层级(含 if/try/for/with 块内)的 docstring。"""
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

    def add(node, scope_type):
        info = find_docstring_info(node, source_lines)
        if info:
            comments.append({
                "file": rel,
                "type": f"{scope_type}_docstring",
                "start": info["start"], "end": info["end"],
                "indent": info["indent"], "source": info["content"],
                "prefix": info["prefix"], "docstring_style": info["docstring_style"],
            })

    add(tree, "module")
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            add(node, "class")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add(node, "function")

    # 收集所有 docstring 节点(各作用域 body[0])的 id,用于排除块内字符串
    docstring_node_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if hasattr(node, "body") and node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                    docstring_node_ids.add(id(first))

    # 块内字符串: 方法体/分支内的裸 """...""" (非 docstring),作为待翻译注释
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            continue
        if id(node) in docstring_node_ids:
            continue
        raw = node.value.value
        if not raw.strip() or has_chinese(raw):
            continue
        start_line = node.lineno
        end_line = node.end_lineno
        if start_line is None or end_line is None:
            continue
        first_line = source_lines[start_line - 1]
        indent = first_line[: len(first_line) - len(first_line.lstrip())]
        stripped = first_line.strip()
        prefix = ""
        m = re.match(r'^(?P<prefix>[rRuU]?)"""', stripped)
        if not m:
            m = re.match(r"^(?P<prefix>[rRuU]?)'''", stripped)
        if m:
            prefix = m.group("prefix")
        style = "single" if start_line == end_line else "multi"
        lines = raw.split("\n")
        non_empty = [ln for ln in lines if ln.strip()]
        if non_empty:
            mi = min(len(ln) - len(ln.lstrip()) for ln in non_empty)
            if mi > 0:
                lines = [ln[mi:] if len(ln) >= mi else ln for ln in lines]
        lines = [ln.lstrip() for ln in lines]
        content = "\n".join(lines)
        if content.strip():
            comments.append({
                "file": rel,
                "type": "block_string",
                "start": start_line,
                "end": end_line,
                "indent": indent,
                "source": content,
                "prefix": prefix,
                "docstring_style": style,
            })

    comments.sort(key=lambda c: c["start"])
    return comments


def _find_hash_outside_string(line: str) -> int:
    """定位行内 # 注释起始位置(忽略字符串内的 #)。

    正确处理三引号字符串的开关:原版用 ch == str_char 判断结束,但 str_char 为
    三引号(3 字符)时单字符 ch 永不相等,导致三引号字符串永不闭合、其后的 # 被
    误判在字符串内而被忽略。此处按 str_char 长度分支判断结束。
    """
    in_str = False
    str_char = None  # '"', "'", '"""' 或 "'''"
    i = 0
    while i < len(line):
        ch = line[i]
        if in_str:
            # 字符串内: 跳过转义字符
            if ch == "\\":
                i += 2
                continue
            # 检查字符串结束
            if len(str_char) == 3:
                if line[i:i + 3] == str_char:
                    in_str = False
                    str_char = None
                    i += 3
                    continue
                i += 1
                continue
            # 单字符字符串
            if ch == str_char:
                in_str = False
                str_char = None
            i += 1
            continue
        # 字符串外
        if line[i:i + 3] in ('"""', "'''"):
            in_str = True
            str_char = line[i:i + 3]
            i += 3
            continue
        if ch in ('"', "'"):
            in_str = True
            str_char = ch
            i += 1
            continue
        if ch == "#":
            return i
        i += 1
    return -1


def _hash_is_url_anchor(line: str, cpos: int) -> bool:
    """判断 line[cpos] 的 # 是否为 URL 锚点(# 前为 URL 字符,# 后紧跟非空字符,且前面有 http(s)://)。"""
    if cpos <= 0:
        return False
    before = line[:cpos]
    after = line[cpos + 1:]
    if not (before and (before[-1].isalnum() or before[-1] in "/._-~")):
        return False
    if not (after and not after[0].isspace()):
        return False
    return ("http://" in before) or ("https://" in before)


def extract_inline_comments(filepath, project_root):
    """v2: 跳过 URL 锚点 #。"""
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
            # v2: 跳过 URL 锚点 #
            if _hash_is_url_anchor(line, cpos):
                continue
            comment_text = line[cpos + 1:].rstrip("\n").lstrip()
            if comment_text.strip() and not has_chinese(comment_text):
                if is_special_inline_comment(comment_text):
                    continue
                if is_commented_code(comment_text):
                    continue
                indent = line[: len(line) - len(line.lstrip())]
                comments.append({
                    "file": rel, "type": "inline",
                    "start": i + 1, "end": i + 1,
                    "indent": indent, "source": comment_text,
                })
    return comments


def extract_python_file(filepath, project_root):
    docstrings = extract_docstrings_from_file(filepath, project_root)
    inlines = extract_inline_comments(filepath, project_root)
    return docstrings + inlines


def main():
    ap = argparse.ArgumentParser(description="提取 Python 注释为 JSON (v2, 修复条件块漏译+URL锚点)")
    ap.add_argument("file_list", help="文件列表 txt")
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
        if not os.path.exists(fp) or not fp.endswith(".py"):
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
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
    for t, n in sorted(by_type.items()):
        print(f"  {t}: {n}")
    print(f"输出: {args.output}")


if __name__ == "__main__":
    main()
