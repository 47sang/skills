---
name: update-skill
description: 通过生成、编辑或优化本仓库中的 `SKILL.md` 文件来创建或更新技能。当编写新技能，或修订现有技能的结构、前置元数据（frontmatter）与说明时使用。
---

# update-skill

本指南提供了在本仓库中创建或更新技能的说明。涵盖了所需的结构、前置元数据以及技能的最佳实践。

## 快速开始

每个技能都是一个包含 `SKILL.md` 文件的目录，该文件具有 YAML 前置元数据和 Markdown 正文：

```markdown
---
name: pdf-processing
description: 从 PDF 文件中提取文本和表格，填写表单，合并文档。
---

# PDF 处理

## 何时使用此技能
当用户需要处理 PDF 文件时使用此技能...

## 如何提取文本
1. 使用 pdfplumber 进行文本提取...
```

## 要求

### 前置元数据（必需）

每个 `SKILL.md` 必须以包含以下内容的 YAML 前置元数据开头：

- **name**：短横线命名标识符（仅限小写字母、数字和连字符）
  - 示例：`add-feature-flag`、`rust-unit-tests`、`update-skill`
- **description**：技能功能和使用时机的具体描述
  - 必须非空
  - 应包含用于技能发现的关键词
  - 以动作动词开头，清晰说明技能完成什么（例如"添加特性标志..."，而不是"帮助处理功能..."），并立即跟一个具体用例或上下文（例如"在处理特性标志时使用"）
  - 使用第三人称（例如"添加特性标志..."，而非"我可以帮你添加..."）

### 编写有效的描述

描述字段对于技能发现至关重要。同时包含**做什么**和**何时使用**。一些好的示例：

- `git-commit`："通过分析 git 差异生成描述性的提交消息。当用户请求帮助编写提交消息或评审已暂存的更改时使用。"
- `pdf-processing`："从 PDF 文件中提取文本和表格，填写表单，合并文档。在处理 PDF 文件或用户提到 PDF、表单或文档提取时使用。"

避免使用模糊的描述，如"帮助处理代码"或"执行开发任务"。更多上下文请参阅 [references/best-practices.md](references/best-practices.md) 中的"描述最佳实践"。

### 技能结构

技能中的典型部分：

1. **标题和简要摘要** - 清晰的标题和技能目的及主要用例的简洁概述。如有用，链接到部分、引用文件或相关技能
2. **概述** - 关于技能目的的上下文（可选但常见），用更多细节和背景扩展摘要
3. **主要内容** - 步骤、使用说明或工作流程指导
4. **最佳实践** - 指南和建议（可选）
5. **示例 / 参考 PR** - 真实示例的链接（可选）

根据技能的需求保持结构灵活。简单的技能可以省略可选部分。

### 验证

可选地，使用 [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) 参考库来验证你的技能：

```bash
skills-ref validate ./my-skill
```

这会检查你的 `SKILL.md` 前置元数据是否有效并遵循所有命名约定。如果未安装，请使用 WebSearch 工具了解此包的上下文。

### 主要内容最佳实践

- 有关什么构成良好主内容的指导，请参阅 [references/best-practices.md](references/best-practices.md) 中的"简洁性原则"
- 有关代码示例格式，请参阅 [references/best-practices.md](references/best-practices.md) 中的"代码示例格式"

### 文件组织

- **简单技能**（<=200 行）：将所有内容保留在 `SKILL.md` 中
- **复杂技能**（>200 行）：将详细内容拆分为 `references/` 子目录
  - 通过清晰的链接从 `SKILL.md` 引用参考文件
  - 示例："有关详细指导，请参阅 [references/best-practices.md](references/best-practices.md)"

## 何时拆分内容

在以下情况下创建 `references/` 子目录：

- `SKILL.md` 接近 200+ 行
- 技能涵盖可以独立加载的多个领域或工作流程
- 详细的参考材料会使主要说明混乱

仅在 `SKILL.md` 中保留基本工作流程和过程说明。将详细的参考材料、模式和扩展示例移至 `references/` 文件。

## 现有技能示例

关于结构和样式的参考：

- `.agents/skills/add-feature-flag/SKILL.md` - 具有清晰顺序步骤的多步骤工作流程
- `.agents/skills/rust-unit-tests/SKILL.md` - 具有代码示例和辅助工具的全面指南
- `.agents/skills/remove-feature-flag/SKILL.md` - 具有搜索命令的清理工作流程

## 同步 README 目录

每次创建或更新技能后，**若存在 [~/.claude/skills/README.md](../README.md) 则同步更新它；若不存在则跳过此步骤**。它是整个技能库的总目录：顶部写有「当前共收录 N 个技能」的计数与若干分组，每个分组是一张表格，每行格式为：

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [skill-name](skill-name/SKILL.md) | 一句话说明做什么 | 一句话说明何时使用 |

需要维护的内容：

- **新增技能**：在合适的分组中追加一行（必要时新建分组，并在顶部目录补上锚点链接），并更新顶部的技能计数。
- **更新技能**：若改动涉及 `description`、主要功能或适用场景，同步修改 README 对应行的「主要功能」与「何时使用」，保持两者语义一致。
- **删除技能**：移除对应行并更新计数；若分组因此变空，一并删除该分组及其顶部目录链接。

> README 中每行的描述应与该技能前置元数据里的中文 `description` 语义一致，但可更精炼。

## 最佳实践

有关详细的编写指导，包括：
- 渐进式披露模式
- 编写简洁有效的说明
- 代码示例格式
- 要避免的常见反模式

请参阅 [references/best-practices.md](references/best-practices.md)
