---
name: git-worktree-parallel
description: 使用 Git worktree 隔离工作目录进行多分支并行开发，覆盖创建/合并/清理全流程与常见陷阱。当需要同时推进多个功能、并行子代理互不踩踏工作区、或紧急修复不打断当前开发时使用。
---

# Git Worktree 并行开发

## 🔎 何时使用 / 何时不用

**✅ 适合**：

- 同时开发多个功能分支（前端 / 后端 / 文档各一路）
- 当前开发进行中，插入紧急修复（不想 `stash` → 切分支 → `pop` 来回折腾）
- 多个子代理并行改代码，需要目录级隔离防止互相卷入未提交改动
- 对照不同分支的代码做审查

**❌ 不适合**：

- 同一分支需要检出多个目录（Git 分支互斥限制，做不到）
- 需要完全独立的仓库（不同远程配置）——直接 `clone` 多份
- 单线程串行开发——普通切分支就够了，别为了用而用

## 🧠 心智模型（一句话）

一个仓库可以同时检出多个工作目录，每个目录独立的工作区 + 独立的 `HEAD` + 独立的暂存区，但**共享同一套对象库与分支引用**——所以磁盘占用极小（仅差异文件），提交即时互通。

```
主工作区 (main) ──┐
worktree-A (feat/a) ──┼── 共享 .git/objects，各自独立 HEAD
worktree-B (feat/b) ──┘
```

## 🛠️ 命令速查（高频五条）

```bash
git worktree add -b <分支> <目录>   # 创建新分支 + 新目录（最常用）
git worktree list                  # 列出所有 worktree
git worktree remove <目录>         # 安全删除（有未提交改动会拒绝）
git worktree remove -f <目录>      # 强制删除
git worktree prune                 # 清理已手动 rm -rf 的残留记录
```

低频命令（`lock` / `unlock` / `move` / `repair` / `--detach`）用到时查 `git worktree --help` 即可。

## 🔄 标准工作流（五步）

```bash
# 1. 创建：从主仓库目录为每个并行任务开一个 worktree
#    统一放在 .claude/worktrees/（与 Claude Code 内建工具 EnterWorktree 的落点一致）
git worktree add -b feature/auth .claude/worktrees/feature-auth
git worktree add -b feature/api  .claude/worktrees/feature-api

# 2. 并行开发：各目录独立编辑、提交，互不干扰
cd .claude/worktrees/feature-auth && git add -A && git commit -m "feat(auth): ..."
cd ../feature-api  && git add -A && git commit -m "feat(api): ..."

# 3. 回主工作区依次合并（改动不同文件通常自动合并）
cd <主仓库目录>
git merge feature/auth --no-edit
git merge feature/api  --no-edit

# 4. 清理 worktree
git worktree remove .claude/worktrees/feature-auth
git worktree remove .claude/worktrees/feature-api

# 5. 删除已合并分支
git branch -d feature/auth feature/api
```

**🔑 减少冲突的关键**：给每个并行任务划分**互不重叠的文件范围**（和本项目 CLAUDE.md 铁律三「按文件挑提交」是同一思想）；分支生命周期尽量短，勤从主干合并更新。

## 🤖 Claude Code 集成

除了手动敲命令，Claude Code 有内建的 worktree 支持：

| 方式 | 用法 | 适合场景 |
|------|------|---------|
| `EnterWorktree` 工具 | 说「开一个 worktree」，会话切入 `.claude/worktrees/` 下的隔离目录 | 当前会话要在隔离副本里改代码 |
| 子代理隔离 | 派发子代理（Agent）时指定 `isolation: "worktree"` | 多个子代理并行改文件，防互相踩踏 |
| 手动命令 | 上面的标准工作流 | 多终端人工并行开发 |

## ⚠️ 常见陷阱

1. **分支互斥**：同一分支不能同时被两个 worktree 检出，报错 `fatal: 'main' is already checked out`——用 `-b` 开新分支解决。
2. **删除要用 `git worktree remove`**：直接 `rm -rf` 会残留元数据记录，之后需 `git worktree prune` 清理。
3. **`.git` 是文件不是目录**：关联工作区的 `.git` 只是一个指向主仓库的指针文件——不能在 worktree 内部再嵌套创建 worktree。
4. **子模块需单独初始化**：在 worktree 里执行 `git submodule update --init --recursive`。
5. **先 prune 再 gc**：worktree 目录被外部删除后，先 `git worktree prune` 再跑 `git gc`，避免误清对象。

## 📚 延伸阅读

原理详解、全量命令、裸仓库部署等完整内容见：
`/Users/zhou/Desktop/演示项目/worktree/docs/git-worktree-tutorial.md`
