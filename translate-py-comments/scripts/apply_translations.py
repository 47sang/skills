#!/usr/bin/env python3
"""
改进版 apply_translations.py —— 保留原始文档字符串布局。

与原版区别:
- docstring: 采用「物理行就地替换」,保留原始布局(indent / 引号位置 / 空行 /
  Args 子项的相对缩进)。原始代码本身合规,换文字后天然合规,不依赖 ruff。
- inline: 沿用原逻辑(`# 译文`)。

用法:
    python3 apply_translations_v2.py --dir <批次目录> --root <项目根>
"""

import argparse
import json
import os
import sys


def find_hash_outside_string(line):
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


def apply_inline(lines, idx, target):
    """行内注释: 把 # 后文字替换为 target。"""
    line = lines[idx]
    cpos = find_hash_outside_string(line)
    if cpos < 0:
        return False
    code_part = line[:cpos]
    trailing_nl = "\n" if line.endswith("\n") else ""
    new_line = f"{code_part}# {target}{trailing_nl}"
    if new_line != line:
        lines[idx] = new_line
        return True
    return False


def _split_nl(raw):
    """拆出 (无换行内容, 换行符)。"""
    if raw.endswith("\n"):
        return raw[:-1], "\n"
    return raw, ""


def apply_docstring_inplace(lines, entry, target):
    """
    物理行就地替换 docstring 文字,保留原始布局。

    - 单行: {indent}{prefix}{quote}{content}{quote}  → 替换 content
    - 多行首行: {indent}{prefix}{quote}{摘要?}        → 替换摘要(若有)
    - 多行中间行: {indent}{相对缩进}{内容}            → 替换内容,保留相对缩进
    - 多行末行: {indent}{相对缩进}{末内容?}{quote}    → 替换末内容(若有)

    target 行数须与 source(即原始内容行)一致(由翻译子代理保证)。
    """
    start = entry["start"] - 1  # 0-based
    end = entry["end"]          # exclusive
    indent = entry.get("indent", "")

    region = lines[start:end]
    if not region:
        return False

    tgt_lines = target.split("\n")
    while tgt_lines and not tgt_lines[0].strip():
        tgt_lines.pop(0)
    while tgt_lines and not tgt_lines[-1].strip():
        tgt_lines.pop()
    if not tgt_lines:
        return False

    # 防御: 转义 target 中的 """ 以防提前闭合 docstring(r 前缀无法转义,跳过);
    # 并对每行做 lstrip —— 行缩进已由原始物理行的 extra 恢复,target 只需提供文字,
    # lstrip 可避免译者误留缩进导致的双重叠加。
    if entry.get("prefix", "").lower() != "r":
        tgt_lines = [ln.replace('"""', '\\"\\"\\"') for ln in tgt_lines]
    tgt_lines = [ln if not ln.strip() else ln.lstrip() for ln in tgt_lines]

    # 检测引号类型
    quote = '"""'
    if '"""' not in region[0] and "'''" in region[0]:
        quote = "'''"

    changed = False
    ti = 0

    if len(region) == 1:
        # 单行 docstring
        raw = region[0]
        body, nl = _split_nl(raw)
        q1 = body.find(quote)
        q2 = body.rfind(quote)
        if q1 == -1 or q2 <= q1:
            return False
        content = body[q1 + 3:q2]
        if not content.strip():
            return False
        if ti >= len(tgt_lines):
            return False
        new_body = body[:q1 + 3] + tgt_lines[ti] + body[q2:]
        new_raw = new_body + nl
        if new_raw != raw:
            region[0] = new_raw
            changed = True
            ti += 1
    else:
        # ---- 多行首行 ----
        raw0 = region[0]
        body0, nl0 = _split_nl(raw0)
        qpos = body0.find(quote)
        if qpos == -1:
            return False
        after = body0[qpos + 3:]
        if after.strip():
            # 首行带摘要 → 替换
            if ti < len(tgt_lines):
                new_body0 = body0[:qpos + 3] + tgt_lines[ti]
                new_raw0 = new_body0 + nl0
                if new_raw0 != raw0:
                    region[0] = new_raw0
                    changed = True
                ti += 1
        # else: """ 独占行 → 首行保持原样

        # ---- 多行中间行 ----
        for i in range(1, len(region) - 1):
            if ti >= len(tgt_lines):
                break
            raw_i = region[i]
            body_i, nl_i = _split_nl(raw_i)
            # 去掉 docstring 缩进,保留相对缩进(extra)
            if body_i.startswith(indent):
                content = body_i[len(indent):]
            else:
                content = body_i
            extra_len = len(content) - len(content.lstrip())
            extra = content[:extra_len]
            new_text = tgt_lines[ti]
            ti += 1
            if new_text.strip() == '':
                new_body_i = ''  # 空行保持真空行,避免尾随空格(W291)
            else:
                new_body_i = indent + extra + new_text
            new_raw_i = new_body_i + nl_i
            if new_raw_i != raw_i:
                region[i] = new_raw_i
                changed = True

        # ---- 多行末行 ----
        raw_last = region[-1]
        body_last, nl_last = _split_nl(raw_last)
        qpos_end = body_last.rfind(quote)
        if qpos_end != -1 and ti < len(tgt_lines):
            before = body_last[:qpos_end]
            if before.strip():
                # 末行带内容 → 替换
                if before.startswith(indent):
                    content = before[len(indent):]
                else:
                    content = before
                extra_len = len(content) - len(content.lstrip())
                extra = content[:extra_len]
                new_text = tgt_lines[ti]
                ti += 1
                new_body_last = indent + extra + new_text + body_last[qpos_end:]
                new_raw_last = new_body_last + nl_last
                if new_raw_last != raw_last:
                    region[-1] = new_raw_last
                    changed = True
            # else: """ 独占末行 → 保持

    if changed:
        lines[start:end] = region
    return changed


def apply_one_file(abs_path, entries):
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  读取失败 {abs_path}: {e}", file=sys.stderr)
        return 0

    # 同文件按起始行号倒序应用,避免行号位移(就地替换不改变行数,倒序仍更稳妥)
    entries = sorted(entries, key=lambda e: e["start"], reverse=True)
    changed = 0

    for e in entries:
        target = (e.get("target") or "").strip()
        if not target:
            continue
        etype = e["type"]
        if etype == "inline":
            idx = e["start"] - 1
            if apply_inline(lines, idx, target):
                changed += 1
        elif etype in ("module_docstring", "class_docstring", "function_docstring", "block_string"):
            if apply_docstring_inplace(lines, e, target):
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
    ap = argparse.ArgumentParser(description="把翻译写回 Python 源文件(保留原格式)")
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
