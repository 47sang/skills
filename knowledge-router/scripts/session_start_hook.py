#!/usr/bin/env python3
"""
SessionStart hook for knowledge-router.

会话启动时读取 stdin（含 cwd），匹配 ~/.claude/knowledge/index.json 中
已注册的项目，匹配到则在 stdout 输出加载提示（注入会话上下文）。

设计原则：任何异常都静默 exit(0)，绝不阻断会话启动。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


KNOWLEDGE_INDEX = Path.home() / ".claude" / "knowledge" / "index.json"


def load_index():
    """读取知识库索引；不存在或损坏返回 None。"""
    if not KNOWLEDGE_INDEX.is_file():
        return None
    try:
        with KNOWLEDGE_INDEX.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def resolve_cwd(input_data):
    """从 stdin JSON 取 cwd，取不到回退 os.getcwd()。"""
    if isinstance(input_data, dict):
        cwd = input_data.get("cwd", "")
        if isinstance(cwd, str) and cwd:
            return cwd
    try:
        return os.getcwd()
    except OSError:
        return ""


def _norm(p):
    """展开 ~ 并规范化，末尾加分隔符便于前缀匹配。"""
    return os.path.normpath(os.path.expanduser(p)) + os.sep


def match_project(cwd, index):
    """
    匹配当前目录到已注册项目。
    策略：路径前缀（最长优先）> slug（目录名/父目录名）。
    返回匹配到的 project dict，或 None。
    """
    if not cwd:
        return None
    projects = index.get("projects", [])
    if not projects:
        return None

    cwd_norm = os.path.normpath(cwd) + os.sep

    # 第一轮：路径前缀匹配，最长前缀优先
    best = None
    best_len = -1
    for proj in projects:
        for rp in proj.get("paths", []) or []:
            if not isinstance(rp, str):
                continue
            try:
                rp_norm = _norm(rp)
            except (TypeError, ValueError):
                continue
            if cwd_norm.startswith(rp_norm) and len(rp_norm) > best_len:
                best, best_len = proj, len(rp_norm)
    if best is not None:
        return best

    # 第二轮：slug 兜底（目录名 / 父目录名）
    cwd_path = Path(cwd).resolve()
    candidate_slugs = {cwd_path.name.lower()}
    if cwd_path.parent != cwd_path:
        candidate_slugs.add(cwd_path.parent.name.lower())
    for proj in projects:
        slug = (proj.get("slug") or "").lower()
        if slug and slug in candidate_slugs:
            return proj

    return None


def main():
    try:
        # 1. 读 stdin
        input_data = None
        try:
            raw = sys.stdin.read()
            if raw.strip():
                input_data = json.loads(raw)
        except (json.JSONDecodeError, ValueError, OSError):
            input_data = None

        # 2. 解析 cwd
        cwd = resolve_cwd(input_data)

        # 3. 读索引
        index = load_index()
        if index is None:
            sys.exit(0)  # 知识库未初始化，静默

        # 4. 匹配
        proj = match_project(cwd, index)
        if proj is None:
            sys.exit(0)  # 无匹配，静默

        # 5. 输出提示（stdout 注入会话上下文）
        slug = proj.get("slug", "unknown")
        title = proj.get("title", slug)
        project_dir = Path.home() / ".claude" / "knowledge" / "projects" / slug

        print(
            f"\n[知识库] 检测到项目「{title}」（slug: {slug}）。\n"
            f"动手开发前，建议先加载以下知识文件：\n"
            f"  - {project_dir}/overview.md   （项目概览：技术栈/模块/约束）\n"
            f"  - {project_dir}/decisions.md  （技术决策：为什么这么设计）\n"
            f"  - {project_dir}/gotchas.md    （踩坑记录：已知陷阱）\n"
            f"运行 /knowledge-router 可按任务类型智能加载；若文件缺失，运行 /knowledge-distill 补充。",
            flush=True,
        )
    except Exception:
        # 兜底：任何意外都静默，绝不阻断会话
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
