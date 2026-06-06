---
name: implement-specs
description: Implement an approved feature from PRODUCT.md and TECH.md, keeping specs and code aligned in the same PR as implementation evolves. Use after the product and tech specs are approved and the next step is building the feature.
---

# implement-specs

根据 `PRODUCT.md` 和 `TECH.md` 实现已批准的功能。

## 概述

在产品和技术规格获得批准后使用此技能。目标是根据规格构建功能，同时保持签入的规格与实现一致，因为工作会演变。

已批准的规格应直接位于 `specs/01-门诊混发/` 中工单命名的目录下，例如 `specs/01-门诊混发/PRODUCT.md` 和 `specs/01-门诊混发/TECH.md`。

在许多情况下，实现应与产品和技术规格一起推送到同一个 PR 中。随着工程师的迭代，`PRODUCT.md`、`TECH.md` 和代码的更改都应推送到同一个 PR 中，以便评审锚定于实际将发布的功能。

## 先决条件

使用此技能之前：
- 确认 `PRODUCT.md` 存在
- 当功能需要一个时，确认 `TECH.md` 存在
- 确认相关规格已被评审和批准到足以开始实现的程度

## 工作流程

### 1. 先阅读已批准的规格

将以下内容视为事实来源：
- `PRODUCT.md` 作为用户可见行为的来源
- `TECH.md` 作为架构、顺序和实现形状的来源

在编写代码之前，确保你理解期望的行为、约束、风险和验证计划。

### 2. 为大型功能提供可选的实现辅助工具

对于大型或长期运行的功能，在实现开始前可选择向用户提供以下辅助工具之一：
- `PROJECT_LOG.md` 以跟踪检查点、探索的路径、部分发现和当前实现状态
- `DECISIONS.md` 以捕获 PRD 和技术设计过程中做出的具体产品和技术决策

这些是可选的辅助工具，而非必需的交付物。在它们能减少混乱或帮助未来代理避免重新探索相同路径时提供它们。

### 3. 根据规格计划和实现

将工作分解为具体的实现步骤，然后根据已批准的规格实现功能。

在实现过程中：
- 保持行为与 `PRODUCT.md` 一致
- 保持架构和顺序与 `TECH.md` 一致
- 随着工作落地添加或更新测试和验证工件

实际可行时，将规格和实现推送到同一个 PR 中，以便完整的功能演变在一个地方可评审。

### 4. 随着实现演变更新规格

如果实现揭示预期行为或设计应该改变，更新签入的规格，而不是让它们过时。

特别是：
- 当用户可见行为、UX、边缘情况或成功标准发生变化时更新 `PRODUCT.md`
- 当架构、顺序、模块边界或验证策略发生变化时更新 `TECH.md`
- 将这些更新保持在与其对应代码更改相同的 PR 中

PR 应描述实际发布的功能，而不仅仅是规格的初始草稿。

### 5. 根据规格验证

在认为工作完成之前，验证代码与当前规格匹配。

优先使用：
- `rust-unit-tests` 进行单元测试和回归覆盖
- 重要用户流程的集成或端到端测试

## 最佳实践

- 在实现过程中保持规格和代码同步。
- 优先在决策更改时立即更新规格，而不是将规格清理批量留到最后。
- 仅当复杂功能真正增加价值时才使用可选的跟踪文档。
- 保持同一个 PR 的一致性：规格更新、代码更改、测试和可选的跟踪文档都应支持相同的功能叙述。

## 相关技能

- `spec-driven-implementation`
- `write-product-spec`
- `write-tech-spec`
- `rust-unit-tests`
