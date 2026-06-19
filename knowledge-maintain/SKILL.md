---
name: knowledge-maintain
description: 对 ~/.claude/knowledge/ 知识库执行三类校准（一致性/时效性/覆盖度），输出结构化健康报告。当用户想校验知识库质量、检查双索引一致性、清理过期条目，或说「维护知识库/校准知识库/检查知识库健康」时使用。默认只报告不自动改文件，需修复时提示对应操作。
---

# knowledge-maintain — 知识库维护与校准

> 一句话：定期给知识库做体检——检查一致性、时效性、覆盖度，输出 🔴🟡🟢 分级报告。

## 核心定位

- 这是知识库系统的**维护端**：只检查、不新增知识
- 三类校准：一致性 / 时效性 / 覆盖度
- **默认只报告，不自动改文件**——需要修复时给出对应命令，由用户（或 `/knowledge-distill`）执行

读取入口：`~/.claude/knowledge/index.json`（机读）与 `index.md`（人读）。当前日期由用户提供或系统日期，用于时效判断。

## 一、一致性校验

| 检查项 | 方法 |
|---|---|
| 双索引互查 | `index.md` 表格列出的文件 ↔ `index.json` 的 `entries`，双向 diff |
| 文件存在性 | `index.json` 每个 `entry.file` 指向的文件是否真实存在 |
| frontmatter 必填 | 每个 `.md` 是否含 `title`/`type`/`updated_at` |
| 字段一致 | 同一文件在 `index.md` 与 `index.json` 的 title/type/slug 是否一致 |
| 交叉引用 | `.md` 内部链接（如 decisions 引用 specs）是否有效 |

不一致项 → 🔴 严重。

## 二、时效性校验

读每个文件 frontmatter 的 `updated_at`，与今天比：

- 超 **90 天**未更新 → 🟡 警告
- 超 **180 天**未更新 → 🔴 严重
- decisions 中「修正记录」标注了适用条件变更、但正文未同步 → 🟡

对每个过期文件给出建议：重新蒸馏 / 确认仍有效（刷新 updated_at）/ 归档。

## 三、覆盖度校验

- **项目完整性**：`index.json` 的每个 project 是否至少有 `overview.md`
- **文件覆盖度矩阵**：每个项目 × {overview, decisions, gotchas, specs} 的有/无

| 项目 | overview | decisions | gotchas | specs |
|------|----------|-----------|---------|-------|

- **反模式覆盖**：gotchas 条目数过少（< 3）且项目非简单项目 → 🟡 提示可能积累不足
- **跨项目模式**：`patterns/`、`anti-patterns/` 是否有条目，与项目数是否匹配

缺失项 → 🟡（建议运行 `/knowledge-distill` 补充）。

## 📋 报告输出格式

```
🔴 严重（需立即处理）
  - <具体项 + 建议动作>

🟡 警告（建议处理）
  - <具体项 + 建议动作>

🟢 正常
  - <通过的检查>

📊 覆盖度矩阵
  <上面的项目×文件表格>
```

每条问题都附**建议动作**（如「项目 X 缺 gotchas.md → 运行 /knowledge-distill 选『某个踩坑』」）。

## ⚠️ 关键约束

- **只读 + 只报告**：发现问题不擅自改文件；索引不一致等可自动修复项，提示修复命令（如「以 .md 的 frontmatter 为准重建 index.json」）但不执行
- **`knowledge/` 不存在**：告知「知识库未初始化，请运行 /knowledge-distill」
- 报告输出到对话，不写文件（除非用户要求落盘）
