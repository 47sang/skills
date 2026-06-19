---
name: review-pr
description: 评审拉取请求（PR）的差异，并将结构化反馈写入 `review.json` 供工作流发布。当基于 `pr_diff.txt`、`pr_description.txt` 等本地产物评审一个已签出的 PR，并需要产出机器可读的评审结果（而非直接发布到 GitHub）时使用。
---

# PR 评审技能

评审当前的拉取请求，并将输出写入 `review.json`。

## 上下文

- 工作目录是已签出的 PR 分支。
- 工作流在 `pr_diff.txt` 中提供了带注释的差异。
- 工作流在 `pr_description.txt` 中提供了 PR 描述。
- 重点关注本 PR 更改的文件和行。
- 不要直接将评论或评审发布到 GitHub。

## 评审范围

- 优先关注正确性、安全性、错误处理和重要的性能问题。
- 仅当你能提供具体建议块时，才包含样式或细节评论。
- 如果某个关注点涉及未更改的代码，请在摘要中提及，而不是放在内联评论中。
- 当现有测试已覆盖有意义的特性时，不要建议添加仅变化构造函数参数或结构体字段的测试用例。仅当新测试能覆盖不同的代码路径或边缘情况时才建议添加。
- 当 PR 明显是 V0 或初始实现时，将关于鲁棒性的建议（超时、重试、生命周期管理）框定为可选未来工作，而非阻断性问题，除非它们存在正确性、安全性或数据丢失风险。

## 差异行注释

差异文件使用以下前缀：

- `[OLD:n]` 表示旧侧被删除的行。使用 `"LEFT"`。
- `[NEW:n]` 表示新侧添加的行。使用 `"RIGHT"`。
- `[OLD:n,NEW:m]` 表示未更改的上下文。使用 `"RIGHT"` 和行 `m`。

## 评论要求

每个评论正文必须以以下标签之一开头：

- `🚨 [CRITICAL]` 用于 bug、安全问题、崩溃或数据丢失。
- `⚠️ [IMPORTANT]` 用于逻辑问题、边缘情况或缺失的错误处理。
- `💡 [SUGGESTION]` 用于有价值的改进或更好的模式。
- `🧹 [NIT]` 仅当评论包含建议块时用于清理。

撰写评论时需遵守以下约束：

- 简洁、直接、可操作。
- 不要添加恭维或含糊其辞。
- 优先使用单行评论。
- 范围最多保留 10 行。
- 内联评论仅限于本 PR 中有效更改的行。

## 建议块

提议代码更改时使用：

```suggestion
<replacement code here>
```

规则：
- 匹配原文件的精确缩进。
- 仅包含替换代码。
- 对于多行建议，将 `start_line` 设置为第一行，`line` 设置为最后一行。

## 输出格式

创建具有以下结构的 `review.json`：

```json
{
  "summary": "## 概述\n...\n\n## 关注点\n- ...\n\n## 结论\n发现：1 个严重，2 个重要，3 个建议\n\n**Request changes**",
  "comments": [
    {
      "path": "path/to/file",
      "line": 42,
      "side": "RIGHT",
      "start_line": 40,
      "body": "⚠️ [IMPORTANT] 简短说明\n\n```suggestion\nreplacement\n```"
    }
  ]
}
```

字段规则：
- `path` 必须相对于仓库根目录。
- `line` 是必需的，且必须定位到正确的一侧。
- `start_line` 是可选的，仅用于多行范围。
- `side` 必须是 `"LEFT"` 或 `"RIGHT"`。

## 摘要要求

`summary` 必须包含：
- PR 的高级概述。
- 重要关注点以及无法内联评论的未触及代码关注点。
- 格式为 `Found: X critical, Y important, Z suggestions` 的问题数量。
- 最终建议为 `Approve`、`Approve with nits` 或 `Request changes`。

## 最终检查

完成之前：

- 使用 `jq` 验证 `review.json`。
- 如果验证失败，修复无效的 JSON。
- 确认行号与带注释的差异匹配。
- 不要运行 `gh pr review`、`gh pr comment`、`gh api` 或任何其他发布到 GitHub 的命令。

你的唯一输出是最终的 `review.json`。
