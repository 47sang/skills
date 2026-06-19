---
name: diagnose-ci-failures
description: 使用 GitHub CLI 诊断 PR 的持续集成（CI）失败，提取错误日志并生成修复计划。当用户要求检查 CI 状态、拉取 CI 问题、分诊测试失败，或排查 PR 构建失败时使用。
---

# diagnose-ci-failures

使用 GitHub CLI 对 PR 的 CI 失败进行编程诊断，提取错误日志，并生成修复计划。

## 概述

本技能提供了一种确定性工作流程，用于检查 PR 的 CI 状态、提取失败日志、分析错误，并生成计划（而非代码更改）来解决问题。输出始终是一个计划文档，在执行前可以进行审查。

## 工作流程

### 1. 验证当前分支的 PR 是否存在

获取当前分支并检查是否存在 PR：

```bash
# 获取当前分支
git branch --show-current

# 检查 PR
gh --no-pager pr view <branch-name> --json number,title,url,state
```

如果不存在 PR，请告知用户，并提议使用 `create-pr` 技能创建一个。

### 2. 检查 CI 状态

获取所有 CI 检查的状态：

```bash
gh pr view <branch-name> --json statusCheckRollup
```

解析输出以识别：
- 已完成的检查与进行中的检查
- 成功的检查
- 失败的检查及其名称和详情 URL

如果 CI 仍在运行，请告知用户哪些检查已失败或通过，高亮仍正在运行的检查，并建议在诊断前等待完成。

### 3. 提取失败日志

对于每个失败的检查，使用状态检查中的运行 ID 拉取日志：

```bash
gh run view <run-id> --log-failed
```

重点提取：
- 错误消息及其位置（文件路径、行号）
- 编译错误（未使用的导入、类型不匹配等）
- 带有特定 lint 名称的代码检查/clippy 错误
- 测试失败消息和堆栈跟踪
- 构建失败及其根本原因

### 4. 对错误进行分类

按类型分组错误：
- **格式化问题**：`cargo fmt` 失败
- **代码检查问题**：`cargo clippy` 警告/错误
- **编译错误**：类型错误、缺少导入、签名不匹配
- **测试失败**：带有名称和失败原因的失败测试
- **平台特定问题**：WASM、Linux、macOS、Windows 特定的失败

### 5. 生成修复计划

使用 `create_plan` 工具创建计划文档，包含：
- **问题陈述**：失败检查的摘要
- **当前状态**：发现了哪些错误以及在哪里
- **建议的更改**：每个错误类别所需的具体修复
- **验证步骤**：验证修复的命令（fmt、clippy、测试、预提交）

该计划应引用 `fix-errors` 技能以获取特定错误类型的详细指导。

## 重要注意事项

- **始终先创建计划**：不要直接进行代码更改。生成计划供用户审查
- **检查 CI 中的测试状态**：即使测试在本地失败，也请在标记为问题之前在 CI 中验证它们是否已通过
- **无关的测试失败**：如果测试在 CI 中通过但在本地失败，它们可能是特定于环境的或存在不稳定性
- **多种错误类型**：一次修复一个类别（例如，先修复所有 clippy 错误再修复测试）
- **交叉引用 fix-errors 技能**：有关特定错误类型的详细解决策略，请使用 `fix-errors` 技能

## 常见 CI 检查名称

- `Formatting + Clippy (MacOS)`
- `Formatting + Clippy (Linux)`
- `Run MacOS tests`
- `Run Linux tests`
- `Run Windows tests`
- `Check CI results`（汇总检查）
- `WASM build`

## 示例命令

**获取带详细信息的 PR 状态：**
```bash
gh --no-pager pr view --json number,title,state,statusCheckRollup
```

**从特定失败运行中获取日志：**
```bash
gh run view 12345678 --log-failed
```

**在日志中检查特定错误：**
```bash
gh run view 12345678 --log-failed 2>&1 | grep -A 5 "error:"
```
