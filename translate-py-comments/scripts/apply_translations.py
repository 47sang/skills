#!/usr/bin/env python3
"""
把翻译结果写回 Python 源文件。

用法:
    python3 apply_translations.py --dir <批次目录> --root <项目根>
    python3 apply_translations.py --file <translations.json> --root <项目根>

注意:
- 文档字符串按标准 Python 格式重建 (r''' 前缀保留, 多行时 ''' 单独一行, 内容每行加缩进, ''' 结尾)
- 只处理 target 非空的条目; target 为空的跳过 (保留原文)
- 同一文件按起始行号从后往前应用, 避免行号位移
"""

import argparse
import json
import os
import sys


def rebuild_docstring(target_text, indent, prefix, style):
    """把翻译后的纯文本重建为标准 Python 文档字符串。"""
    lines = target_text.split("\n")
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()

    if not lines:
        return ""

    pfx = prefix if prefix else ""
    quote = '"""'

    if style == "single" and len(lines) == 1:
        return f"{indent}{pfx}{quote}{lines[0]}{quote}\n"
    else:
        out = [f"{indent}{pfx}{quote}"]
        for ln in lines:
            if ln.strip() == "":
                out.append(f"{indent} *")
            else:
                stripped = ln.lstrip()
                out.append(f"{indent} * {stripped}")
        out.append(f"{indent}{quote}")
        return "\n".join(out) + "\n"


def find_hash_outside_string(line):
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


def apply_one_file(abs_path, entries):
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  读取失败 {abs_path}: {e}", file=sys.stderr)
        return 0

    entries = sorted(entries, key=lambda e: e["start"], reverse=True)
    changed = 0

    for e in entries:
        target = (e.get("target") or "").strip()
        if not target:
            continue
        start = e["start"] - 1
        end = e["end"]
        etype = e["type"]

        if etype in ("module_docstring", "class_docstring", "function_docstring"):
            indent = e.get("indent", "")
            prefix = e.get("prefix", "")
            style = e.get("docstring_style", "multi")
            new_block = rebuild_docstring(target, indent, prefix, style)
            old_block = "".join(lines[start:end])
            if new_block != old_block:
                lines[start:end] = [new_block]
                changed += 1
        elif etype == "inline":
            line = lines[start]
            cpos = find_hash_outside_string(line)
            if cpos >= 0:
                code_part = line[:cpos]
                trailing_nl = "\n" if line.endswith("\n") else ""
                new_line = f"{code_part}# {target}{trailing_nl}"
                if new_line != line:
                    lines[start] = new_line
                    changed += 1

    if changed:
        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            print(f"  写入失败 {abs_path}: {e}", file=sys.stderr)
            return 0
    return changed


def load_entries(args):
    entries = []
    if args.dir:
        for name in sorted(os.listdir(args.dir)):
            if name.endswith(".json"):
                with open(os.path.join(args.dir, name), "r", encoding="utf-8") as f:
                    entries.extend(json.load(f))
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            entries = json.load(f)
    else:
        print("必须指定 --dir 或 --file", file=sys.stderr)
        sys.exit(1)
    return entries


def main():
    ap = argparse.ArgumentParser(description="把翻译写回 Python 源文件")
    ap.add_argument("--dir", help="split 产出的批次目录")
    ap.add_argument("--file", help="单个合并 JSON 文件")
    ap.add_argument("--root", required=True, help="项目根目录")
    args = ap.parse_args()

    entries = load_entries(args)
    by_file = {}
    for e in entries:
        by_file.setdefault(e["file"], []).append(e)

    total_changed = 0
    files_changed = 0
    for rel, group in by_file.items():
        abs_path = os.path.join(args.root, rel)
        if not os.path.exists(abs_path):
            print(f"  文件不存在,跳过: {rel}", file=sys.stderr)
            continue
        n = apply_one_file(abs_path, group)
        if n:
            files_changed += 1
            total_changed += n

    print(f"修改文件数: {files_changed}")
    print(f"应用译文条数: {total_changed}")


if __name__ == "__main__":
    main()
