---
name: knowledge-router
description: 根据当前工作目录自动识别项目，从知识库按任务类型加载对应的项目知识文件（概览/决策/踩坑/规范）。在会话启动时由钩子自动触发，或开发新功能、排查故障、代码评审前手动运行。触发词：加载项目知识、加载知识库、项目上下文、/knowledge-router。
---

# knowledge-router — 项目知识库路由加载

> 一句话：自动识别你当前在哪个项目，按任务类型加载最相关的知识文件，让 Claude 动手前就理解项目上下文。

## 核心定位

- 这是知识库系统的**读取端**：只加载、不写入知识库
- 两个触发路径：
  - **自动**：会话启动时由 `SessionStart` 钩子（见下文）识别项目并提示
  - **手动**：用户运行 `/knowledge-router`，按任务类型智能加载

## 🔌 自动加载（SessionStart 钩子）

钩子脚本 `scripts/session_start_hook.py` 已在 `~/.claude/settings.json` 注册，每次新会话启动或恢复时自动运行：

1. 从 stdin 读取当前工作目录
2. 匹配 `~/.claude/knowledge/index.json` 中已注册的项目
3. 匹配到 → 在会话开头输出提示（建议加载哪些文件）
4. 匹配不到或知识库未初始化 → 静默退出，不打扰

看到钩子提示后，**主动 Read 它建议的文件**（overview/decisions/gotchas），或运行 `/knowledge-router` 按任务精细加载。

## 🎯 手动加载（本技能主体）

### 步骤 1：识别当前项目

读取 `~/.claude/knowledge/index.json` 的 `projects` 数组，按以下优先级匹配当前工作目录：

1. **路径前缀匹配**：当前目录是否落在某项目的 `paths`（注册的本地路径）之下——取最长前缀匹配（最具体的项目）
2. **slug 兜底**：当前目录名（或父目录名）是否等于某项目的 `slug`
3. **git remote 兜底**：读当前目录（或祖目录）的 `git remote get-url origin`，提取 `owner/repo`，匹配项目的 `repo` 字段

三个都匹配不到 → 告知用户「当前项目未注册知识库」，建议运行 `/knowledge-distill` 注册。

### 步骤 2：按任务类型确定加载清单

用 `AskUserQuestion` 确认任务类型（用户已明确则跳过）：

| 任务类型 | 加载文件 |
|---|---|
| 新功能开发 | overview + decisions + specs/（相关模块） |
| 排查故障 | overview + gotchas + decisions |
| 代码评审 | overview + decisions（设计意图）+ gotchas（检查是否引入已知坑） |
| 重构 | overview + decisions + gotchas + specs/（相关模块） |
| 快速了解 | overview |

### 步骤 3：加载并摘要

- Read 选定的 `.md` 文件，将内容注入当前会话上下文
- 输出加载摘要：每个文件的 3-5 条要点
- 某文件不存在 → 明确告知（如「该项目尚未编写 gotchas.md」），建议用 `/knowledge-distill` 补充

## ⚠️ 关键约束

- **只读不改**：本技能绝不修改知识库文件
- **优雅降级**：`index.json` 不存在 → 告知「知识库未初始化，请运行 /knowledge-distill」，不报错
- **路径展开**：所有 `~` 路径读取时展开为 `$HOME`
- **长文件处理**：文件过长时先读 frontmatter 摘要，让用户决定是否加载全文
