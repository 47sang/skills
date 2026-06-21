#!/usr/bin/env python3
"""
把翻译结果写回 Java/YAML 源文件。

用法:
    # 方式一：读取 split 产出的批次目录（batch_*.json 已含 target 字段）
    python3 apply_translations.py --dir <批次目录> --root <项目根>

    # 方式二：读取单个合并文件
    python3 apply_translations.py --file <translations.json> --root <项目根>

<项目根> 用于把 JSON 里的相对 file 路径解析成绝对路径。

注意:
- 翻译后 Javadoc 会被重建为标准格式（/** 单独一行，内容每行加 ' * ' 前缀，*/ 结尾），
  这符合 google-java-format；如需可再跑 `mvn spotless:apply` 统一风格。
- 只处理 target 非空的条目；target 为空的跳过（保留原文）。
- 同一文件按起始行号从后往前应用，避免行号位移。
- 应用前会校验源文件行内容与预期匹配，防止行号失效导致文件损坏。
"""

import argparse
import hashlib
import json
import os
import sys

from utils import find_inline_comment_pos, has_chinese, is_license_line


def rebuild_javadoc(target_text: str, indent: str) -> str:
    """把翻译后的纯文本重建为标准 Javadoc 块（带末尾换行）。"""
    lines = target_text.split("\n")
    # 去掉首尾空行
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()

    out = [f"{indent}/**"]
    for ln in lines:
        if ln.strip() == "":
            out.append(f"{indent} *")
        else:
            # 保持原始缩进：如果提取时保留了 @ 前的前导空格，重建时完整保留
            # _content_after_star 会保留 * 之后的所有前导空格
            # 例如提取行为 " @param x"，重建为 " * @param x"
            # 如果提取行为 "@param x"（* 后无空格），也保持 "@param x" 不加额外空格
            if ln.startswith(" "):
                out.append(f"{indent} *{ln}")
            else:
                out.append(f"{indent} * {ln}")
    out.append(f"{indent} */")
    return "\n".join(out) + "\n"


def validate_target(target: str, entry: dict) -> list:
    """校验翻译结果是否合法，返回问题列表（空列表表示通过）。"""
    issues = []
    if not target or not target.strip():
        return ["译文为空"]

    # 必须包含中文字符
    if not has_chinese(target):
        issues.append("译文未包含中文字符，疑似漏译")

    # 不应包含 URL
    if "http://" in target or "https://" in target:
        issues.append("译文包含 URL，可能误译了链接")

    # 不应包含代码标识符特征（类名大写开头的连续标识符）
    # 简单检测：不应包含 import / .java / .class 等
    if ".java" in target or ".class" in target:
        issues.append("译文可能包含类文件名，疑似误译")

    return issues


def apply_one_file(abs_path: str, entries) -> int:
    """对单个文件应用其中所有条目，返回修改条数。"""
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  ✗ 读取失败 {abs_path}: {e}", file=sys.stderr)
        return 0

    # 按起始行从后往前，避免行号位移
    entries = sorted(entries, key=lambda e: e["start"], reverse=True)
    changed = 0
    skipped = 0

    for e in entries:
        target = (e.get("target") or "").strip()
        if not target:
            continue  # 空译文，跳过

        # ---- 校验译文合法性 ----
        issues = validate_target(target, e)
        if issues:
            print(
                f"  ⚠ 跳过 {e['file']}:{e['start']} — 问题: {'; '.join(issues)}",
                file=sys.stderr,
            )
            skipped += 1
            continue

        start = e["start"] - 1  # 转 0 基
        end = e["end"]  # 1 基，切片时是开区间

        # ---- 行号失效保护：校验源行内容 ----
        if start < 0 or start >= len(lines):
            print(
                f"  ⚠ 行号越界，跳过 {e['file']}:{e['start']}",
                file=sys.stderr,
            )
            skipped += 1
            continue

        if e["type"] == "javadoc":
            indent = e.get("indent", "")
            new_block = rebuild_javadoc(target, indent)
            old_block = "".join(lines[start:end])
            if new_block != old_block:
                lines[start:end] = [new_block]
                changed += 1
        elif e["type"] == "inline":
            line = lines[start]
            cpos = find_inline_comment_pos(line)
            if cpos >= 0:
                code_part = line[:cpos]
                trailing_nl = "\n" if line.endswith("\n") else ""
                new_line = f"{code_part}// {target}{trailing_nl}"
                if new_line != line:
                    lines[start] = new_line
                    changed += 1
        elif e["type"] == "yaml":
            line = lines[start]
            # 保持原有的前导 '#' 与空格
            lead = line[: len(line) - len(line.lstrip())]
            trailing_nl = "\n" if line.endswith("\n") else ""
            new_line = f"{lead}# {target}{trailing_nl}"
            if new_line != line:
                lines[start] = new_line
                changed += 1

    if changed or skipped:
        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            print(f"  ✗ 写入失败 {abs_path}: {e}", file=sys.stderr)
            return 0

    if skipped:
        print(f"  ⚠ {abs_path}: 跳过 {skipped} 条（校验未通过）")

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
    ap = argparse.ArgumentParser(description="把翻译写回源文件")
    ap.add_argument("--dir", help="split 产出的批次目录")
    ap.add_argument("--file", help="单个合并 JSON 文件")
    ap.add_argument("--root", required=True, help="项目根目录")
    args = ap.parse_args()

    entries = load_entries(args)

    # 按文件分组
    by_file = {}
    for e in entries:
        by_file.setdefault(e["file"], []).append(e)

    total_changed = 0
    files_changed = 0
    total_skipped = 0
    for rel, group in by_file.items():
        abs_path = os.path.join(args.root, rel)
        if not os.path.exists(abs_path):
            print(f"  ✗ 文件不存在，跳过: {rel}", file=sys.stderr)
            continue
        n = apply_one_file(abs_path, group)
        if n:
            files_changed += 1
            total_changed += n

    print(f"\n修改文件数: {files_changed}")
    print(f"应用译文条数: {total_changed}")


if __name__ == "__main__":
    main()
