# Skills 技能库

本仓库是一组可被 Claude Code 自动加载与调用的技能集合。每个技能是一个独立目录，内含一份 `SKILL.md`（YAML 前置元数据 + Markdown 正文），说明「做什么、何时用、怎么做」。

当前共收录 **14** 个技能，按功能归为以下 7 组。进入项目时可直接对照下表定位；点击技能名可跳转到对应的 `SKILL.md`。使用时无需手动指定——在对话中说出对应意图（如「帮我评审这个 PR」「分析一下这个开源项目」），相关技能会被自动触发。

## 目录

- [📚 学习与知识沉淀](#-学习与知识沉淀)
- [📐 规格驱动开发](#-规格驱动开发)
- [🤝 PR 评审与协作](#-pr-评审与协作)
- [🛠️ 代码质量与修复](#-代码质量与修复)
- [🔀 Git 操作](#-git-操作)
- [🌐 注释翻译](#-注释翻译)
- [⚙️ 技能维护](#-技能维护)

---

## 📚 学习与知识沉淀

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [deep-learn-codebase](deep-learn-codebase/SKILL.md) | 深度学习任意代码库，产出「一篇一主题」教学文档 + 嵌入式刻意练习（缺陷预演 / 决策复盘） | 想系统学习或分析一个开源项目 / 框架、提炼优秀架构 |
| [distill-essence](distill-essence/SKILL.md) | 从新事物中萃取可复用的精华，沉淀为可被人工智能（AI）检索的「第二大脑」条目，并做元认知自检 | 想快速搞懂一个新东西、提炼可复用抓手，但没时间逐行读源码 |

## 📐 规格驱动开发

一条「先写规格、再写代码」的工作流：用 `write-product-spec` / `write-tech-spec` 产出 `PRODUCT.md` / `TECH.md`，用 `implement-specs` 落地实现，`spec-driven-implementation` 负责整体编排与保持规格同步。

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [spec-driven-implementation](spec-driven-implementation/SKILL.md) | 驱动规格优先工作流，让 `PRODUCT.md` / `TECH.md` 随实现演进并签入源码 | 启动重要功能、规划智能体（agent）驱动的开发 |
| [write-product-spec](write-product-spec/SKILL.md) | 编写 `PRODUCT.md`，从用户视角描述功能行为与验证条件 | 定义功能行为、编写产品需求文档（PRD） |
| [write-tech-spec](write-tech-spec/SKILL.md) | 编写 `TECH.md`，把产品意图转化为贴合现有代码库的实现计划 | 做技术实现计划、架构设计文档 |
| [implement-specs](implement-specs/SKILL.md) | 按已批准的规格实现功能，保持规格与代码在同一次提交中同步 | 产品 / 技术规格批准后，开始构建功能 |

## 🤝 PR 评审与协作

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [review-pr](review-pr/SKILL.md) | 评审拉取请求（PR）的差异，输出结构化 `review.json` 供工作流发布 | 评审已签出的本地 PR（基于 `pr_diff.txt` 等产物） |
| [create-pr](create-pr/SKILL.md) | 为当前分支创建拉取请求，含合并主干、运行预提交检查、关联工单 | 提交代码评审、准备合并 |
| [diagnose-ci-failures](diagnose-ci-failures/SKILL.md) | 用 GitHub CLI 诊断 PR 的持续集成（CI）失败，提取日志并生成修复计划 | 检查 CI 状态、排查构建或测试失败 |

## 🛠️ 代码质量与修复

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [fix-errors](fix-errors/SKILL.md) | 修复编译错误、代码检查（lint）告警、格式违规与测试失败（覆盖 rustc / clippy / fmt） | 遇到构建、代码检查或测试失败，或提交前需通过预检查 |
| [rust-unit-tests](rust-unit-tests/SKILL.md) | 编写、改进并运行 Rust 单元测试（crate 级、异步、特性开关场景） | 补充或完善 Rust 测试、设定测试规范 |

## 🔀 Git 操作

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [resolve-merge-conflicts](resolve-merge-conflicts/SKILL.md) | 只提取未解决路径与冲突摘要，在尽量不展开完整文件的前提下解决冲突 | 合并、变基、拣选（cherry-pick）、储藏恢复等操作卡在冲突时 |

## 🌐 注释翻译

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [translate-source-comments](translate-source-comments/SKILL.md) | 将 Java（及 YAML）源码中的英文 Javadoc 与行内注释翻译为中文，保留代码、正则与字面量不动 | 整个项目或部分源文件的注释汉化 |

## ⚙️ 技能维护

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [update-skill](update-skill/SKILL.md) | 创建或更新本仓库的 `SKILL.md`（目录结构、前置元数据、正文规范） | 新增技能，或修订现有技能的结构与说明 |

---

> 💡 想新增或修改技能？参考 [update-skill](update-skill/SKILL.md) 中的结构与最佳实践。
