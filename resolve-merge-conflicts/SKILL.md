---
name: resolve-merge-conflicts
description: 通过只提取未解决的路径、冲突片段与精简差异来解决 Git 合并冲突，而不是把整个文件载入上下文。当合并（merge）、变基（rebase）、拣选（cherry-pick）或储藏恢复（stash pop）因冲突中断、`git status` 显示未合并路径，或文件中存在冲突标记时使用。
---

# 解决合并冲突

## 概述

在不需要打开完整文件的情况下解决冲突，除非压缩视图不足以判断。从摘要开始，然后逐个检查冲突文件。

## 工作流程

1. 从摘要开始。

```bash
python3 scripts/extract_conflict_context.py
```

使用摘要识别哪些文件未解决、存在哪些索引阶段，以及每个文件包含多少个文本块。

2. 深入查看单个文件。

```bash
python3 scripts/extract_conflict_context.py --file path/to/file
```

优先使用此命令而非读取整个文件。该脚本仅打印附近的上下文、每个块的 `ours` / `base` / `theirs` 部分，以及 `ours` 和 `theirs` 之间的压缩统一差异。

3. 解决文件。

- 当合适时，使用 `git checkout --ours -- path/to/file` 或 `git checkout --theirs -- path/to/file` 整块采用某一侧。
- 否则直接编辑文件并删除冲突标记。
- 仅当压缩输出不足以判断正确合并方式时，才读取更多文件内容。

4. 重新检查未解决的文件。

```bash
python3 scripts/extract_conflict_context.py
git diff --name-only --diff-filter=U
```

5. 验证解决方案。

- 确保没有未合并的路径剩余。
- 确保已解决的文件中不再包含 `<<<<<<<`、`=======` 或 `>>>>>>>` 标记。
- 运行受影响区域的目标测试、构建或代码检查。
- 暂存已解决的文件。

## 命令

### 仅摘要

```bash
python3 scripts/extract_conflict_context.py
```

### 单个文件的详细视图

```bash
python3 scripts/extract_conflict_context.py --file path/to/file
```

### 所有冲突文件的详细视图

```bash
python3 scripts/extract_conflict_context.py --all
```

### JSON 输出

```bash
python3 scripts/extract_conflict_context.py --file path/to/file --json
```

### 调整输出大小

```bash
python3 scripts/extract_conflict_context.py \
  --file path/to/file \
  --context 3 \
  --max-lines 60
```

## 注意事项

- 直接打开冲突文件前先使用本脚本。
- 一次解决一个文件以保持上下文简洁。
- 预期会出现基于标记的文本冲突以及仅索引级别的冲突，例如 add/add 或 modify/delete。该脚本会汇总这两种冲突；当工作区文件没有冲突标记时，会回退到索引阶段预览。
