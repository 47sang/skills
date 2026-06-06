---
name: create-pr
description: Create a pull request in the current repository for the current branch. Use when the user mentions opening a PR, creating a pull request, submitting changes for review, or preparing code for merge.
---

# create-pr

## 概述

本指南涵盖了在当前仓库中创建拉取请求的最佳实践，包括合并 master、运行预提交检查、关联 Linear 任务、确保适当的测试覆盖率，以及构建适合有效评审的 PR 结构。

## 相关技能

- `fix-errors` - 在打开 PR 前修复预提交失败（格式化、代码检查、测试）
- `rust-unit-tests` - 为你的更改编写单元测试（如适用，见下方的"测试要求"）
- `add-feature-flag` - 在特性标志后面进行更改

## PR 前检查清单

### 1. 将 master 合并到你的特性分支

**在开始评审流程之前，务必将 master 合并到你的特性分支。**

```bash
git fetch origin
git merge origin/master
```

在打开 PR 之前，在本地解决所有合并冲突。

### 2. 运行代码更改的预提交检查

如果 PR 包含代码更改，请在打开或更新 PR 之前运行项目的预提交检查。常见的预提交脚本是 `./script/presubmit`、`./scripts/check.sh`，或等效的 CI 代码检查/测试命令。如果项目没有预提交脚本，请手动运行相关检查：
- 代码格式化（例如 `cargo fmt`、`gofmt`、`prettier --check`）
- 以警告为错误的代码检查（例如 `cargo clippy`、`golangci-lint run`）
- 全部测试（单元、文档和集成）

如果 PR 仅包含文档更改（例如技能、Markdown 或其他非代码内容），则无需为了打开或更新 PR 而运行 `cargo fmt` 或 `cargo clippy`。

如果代码变更的 PR 的预提交失败，请使用 `fix-errors` 技能解决问题。

**在以下情况之前必须运行 `cargo fmt` 和 `cargo clippy`：**
- 打开包含代码更改的新 PR
- 向现有 PR 分支推送包含代码更改的新提交
- 任何更改代码的已评审分支更新

### 3. 评审你的更改

在创建 PR 之前，先检查你要提交的更改：

```bash
# 查看分支中的提交（与基础分支比较）
git --no-pager log <base-branch>..HEAD --oneline

# 查看更改的文件统计信息
git --no-pager diff <base-branch>...HEAD --stat

# 查看完整差异
git --no-pager diff <base-branch>...HEAD
```

这有助于你：
- 验证所有预期更改都已包含
- 在评审前发现意外更改
- 编写准确的 PR 描述
- 确保与正确的基础分支比较
- **测试：** 在需要时包含测试——bug 修复（回归测试）、算法代码（单元测试）、UI 组件（布局测试）、P0 用例（集成测试）。见下方的测试要求。

### 4. 关联到 Linear 任务

如有可能，PR 应关联到 Linear 任务。如果可用，使用 Linear MCP 工具查找对应问题。

**分支命名规范：**
远程分支应以你的名字为前缀（例如 `zheng/feature`、`alice/fix-bug`）。

**如何将 PR 关联到 Linear：**
在 PR 标题中包含问题 ID（例如 `[WARP-1234] 添加新功能`）。请在创建 PR **之前**执行此操作以实现自动关联。

### 5. 打开 PR

打开 PR 时使用 `.github/pull_request_template.md` 中的 PR 模板。

在适当时使用 PR 模板底部的格式添加变更日志条目。一些示例：
- 功能："在当前目录中跨文件进行全局搜索。使用 CMD-F/CTRL-SHIFT-F 打开。"
- 改进："跳转到行/列时添加水平自动滚动。"
- Bug 修复："修复代理运行命令时会话查看器输入被清除的问题。"

**CLI 工作流程：**

- **检查当前分支是否已有 PR：**
  ```bash
  gh pr view --json number,url
  ```
  退出码 0 表示 PR 存在，1 表示不存在。

- **创建新 PR：**
  ```bash
  # 带标题和正文
  gh pr create --title "标题" --body "描述" --draft

  # 从提交自动填充
  gh pr create --fill --draft

  # 使用 PR 模板文件
  gh pr create --body-file .github/pull_request_template.md --title "标题" --draft
  ```
  关键标志：`--draft` / `-d`、`--fill` / `-f`、`--body-file` / `-F`、`--web` / `-w`

- **更新现有 PR：**
  ```bash
  gh pr edit --title "新标题" --body "新正文"
  gh pr edit --add-reviewer username --add-label bug
  ```

- **将 PR 标记为就绪评审：**
  ```bash
  gh pr ready
  ```

### 6. 包含共同作者署名

提交更改或创建 PR 时，在每个提交消息或 PR 描述的末尾包含署名：

```
Co-Authored-By: Agent <agent@example.dev>
```

## 测试要求

### Bug 修复需要回归测试

**所有 bug 修复都应附带回归测试。** 这有助于防止已经损坏过的功能再次被破坏。

测试应满足：
- 重现原始 bug（修复前会失败）
- 修复后通过
- 名称清晰，表明它防止哪个 bug

### 算法代码需要单元测试

具有非平凡逻辑的代码应具有单元测试以验证功能：

**需要单元测试的示例：**
- 自定义数据结构（例如 `SumTree`）
- 应对给定查询返回预期结果的搜索相关 API
- UI 框架中的核心布局代码
- 任何算法或计算逻辑

**不需要的：**
- 足够简单的函数
- 平凡的 getter/setter

有关编写单元测试的指导，请参阅 `rust-unit-tests` 技能。

### UI 组件需要布局验证测试

**所有 UI 组件（`View` 的实现）都应具有简单的单元测试**，以验证它们可以布局而不出现 panic。

这提供了对渲染"安全性"（虽然不是"正确性"）的高级覆盖：

```rust
#[test]
fn test_component_can_layout() {
    use mycrate::App;
    use mycrate::test_util::{terminal::initialize_app_for_terminal_view, add_window_with_terminal};
    
    App::test((), |mut app| async move {
        initialize_app_for_terminal_view(&mut app);
        let term = add_window_with_terminal(&mut app, None);
        
        // 渲染组件 - 不应 panic
        term.update(&mut app, |view, ctx| {
            // 创建并布局你的组件
        });
    })
}
```

### 在跳过集成测试覆盖前先询问用户

如果 PR 更改了用户可见流程、修复了端到端回归，或者看起来会从集成测试覆盖中受益，请在创建或更新 PR 之前使用 `ask_user_question` 工具询问用户是否希望将集成测试作为工作的一部分添加。

优先使用直接选项，例如：
- `Yes, add an integration test before creating the PR`（是，在创建 PR 前添加集成测试）
- `No, continue without an integration test`（否，继续而不添加集成测试）


### P0 用例需要集成测试

**所有"P0 用例"都需要一个集成测试**，以覆盖所讨论的行为/流程。

**"P0 用例"定义为：** 任何应用程序行为，如果其损坏将导致带外发布。

集成测试应：
- 执行完整的面向用户流程
- 验证端到端功能
- 放置在 `integration/` 目录中

## PR 描述指南

PR 描述中"说明"部分下的摘要应包含：

1. **什么** - 进行了哪些更改
2. **为什么** - 为什么需要这些更改（如适用，链接到工单/issue）
3. **如何** - 所采用方法的简要说明

## 打开 PR 之后

1. **监控 CI 检查** - 确保所有自动化检查通过
2. **回复评审意见** - 及时处理反馈
3. **保持 PR 最新** - 如果出现冲突，合并 master
4. **重新运行相关验证** - 根据评审反馈进行更改后。对于代码更改，重新运行 `cargo fmt`/`cargo clippy`（以及其他相关检查）；对于仅文档更改，则无需此操作。

## 最佳实践

- **保持 PR 聚焦** - 如有可能，每个 PR 只做一个逻辑更改
- **编写清晰的提交消息** - 解释做了什么和为什么，而不仅仅是做了什么
- **先自我评审** - 在请求评审之前先审查自己的差异
- **更新测试** - 确保测试覆盖反映你的更改
- **记录破坏性更改** - 指明任何 API 更改或破坏性修改
- **使用特性标志** - 在适当时将高风险更改隐藏在特性标志后面（参阅 `add-feature-flag` 技能）
