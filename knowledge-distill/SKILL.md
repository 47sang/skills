---
name: knowledge-distill
description: 从当前项目蒸馏结构化知识（项目概览/技术决策/踩坑记录/模块规范/通用模式/反模式），写入 ~/.claude/knowledge/ 知识库并同步双索引。当用户想沉淀项目知识、记录踩坑、归档技术决策，或说「蒸馏项目知识/记录这个坑/沉淀设计决策/生成项目规范」时使用。
---

# knowledge-distill — 项目知识蒸馏与沉淀

> 一句话：从项目源码、git 历史、开发经验中蒸馏结构化知识，写入知识库，让下一次 Claude 启动时自动理解项目。

## 核心定位

- 这是知识库系统的**写入端**：只写入、不加载（加载用 `/knowledge-router`）
- **知识库的内部结构**（写之前先判断写哪个目录）：
  - `projects/<slug>/`：**项目专属**——某个项目的概览、技术决策、踩坑、模块规范
  - `patterns/`：**跨项目通用**的工程模式（如幂等性、软删除、分页）
  - `anti-patterns/`：**跨项目通用**的反模式（多个项目踩过的同类坑）

## 前置条件

- 当前目录应在某 git 仓库内（蒸馏依赖 git log 和代码结构）
- 若 `~/.claude/knowledge/` 不存在 → 步骤 0 自动初始化骨架

## 工作流程

### 步骤 0：初始化知识库骨架（仅首次）

`knowledge/` 不存在时创建：`patterns/`、`anti-patterns/`、`projects/` 目录 + `index.md`（空表格）+ `index.json`（空 projects/entries 数组）。已存在则跳过。

### 步骤 1：确认蒸馏范围

用 `AskUserQuestion` 确认要沉淀什么：

| 范围 | 产出文件 | 何时用 |
|---|---|---|
| 整个项目概览 | `projects/<slug>/overview.md` | 接手/摸清一个新项目 |
| 某次技术决策 | `projects/<slug>/decisions.md`（追加一条） | 做完一个重要架构选择 |
| 某个踩坑 | `projects/<slug>/gotchas.md`（追加一条） | 刚填完一个坑 |
| 某模块深度规范 | `projects/<slug>/specs/<module>.md` | 某模块复杂、值得单独成文 |
| 跨项目通用模式 | `patterns/<name>.md` | 提炼出可在多个项目复用的工程做法 |
| 反模式 | `anti-patterns/<name>.md` | 多个项目踩过的同类坑 |

同时确认 `slug`（项目唯一标识，kebab-case）、注册的本地 `paths`（供路由匹配，写绝对路径）、业务领域。

### 步骤 2：采集素材

按范围定向采集（**广度优先，止于够用**）：

- **overview**：`README` / `CLAUDE.md` / 构建文件（`package.json`/`pom.xml`/`build.gradle`/`Cargo.toml`/`pyproject.toml`）/ 目录结构 / 核心模块入口
- **decisions**：`git log`（相关文件/模块的提交历史）/ PR 讨论 / 设计文档 / 代码中的设计说明注释
- **gotchas**：`git log`（fix/hotfix 提交）/ issue / 代码中的 `TODO`/`FIXME`/`HACK` / 测试中的边界用例
- **specs**：模块源码 / 接口定义 / 测试文件 / 相关 decisions

有 codegraph 索引优先 `codegraph_explore`（一次覆盖多文件），无则 `Glob`+`Read`。

### 步骤 3：生成知识文件

按 `references/templates.md` 的对应模板生成 `.md`，**必须带 frontmatter**。

### 步骤 4：双写索引

- `index.md`：在对应表格追加一行（项目表 / 模式表 / 反模式表）
- `index.json`：`projects` 数组追加/更新项目元信息（含 slug/title/paths/repo/domain/language/status）；`entries` 数组追加文件条目
- 两份索引的字段必须一致（否则 `/knowledge-maintain` 会标记不一致）

### 步骤 5：确认与提示

输出本次生成的文件清单 + 每个文件的摘要；提示用户可运行 `/knowledge-maintain` 校验一致性。

## ⚠️ 硬约束（不可跳过）

1. **decisions 的「适用条件」必须具体到本项目**——禁写「通用最佳实践」，必须写「因本项目 X 约束，所以 Y」
2. **gotchas 必须有「预防」措施**——不能只描述症状，必须给出可操作的预防（代码规范 / lint 规则 / 测试用例 / CI 检查）
3. **所有文件必须带 frontmatter**（title/type/project/updated_at 等）
4. **必须双写 index.md 和 index.json**，且字段一致
5. **patterns/anti-patterns 必须跨项目通用**——只在单一项目用过的做法放该项目的 `specs/`，不要放进 `patterns/`

## 详细模板

6 类模板（overview/decisions/gotchas/specs/patterns/anti-patterns）的 frontmatter 字段定义与正文骨架，见 [references/templates.md](references/templates.md)。
