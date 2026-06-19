# knowledge-distill — 知识文件模板

本文件是 [SKILL.md](../SKILL.md) 的配套参考，提供 6 类知识文件的 frontmatter 字段定义、正文骨架与示例。

---

## 目录

1. overview.md（项目概览）
2. decisions.md（技术决策记录）
3. gotchas.md（踩坑记录）
4. specs/`<module>`.md（模块深度规范）
5. patterns/`<name>`.md（跨项目通用模式）
6. anti-patterns/`<name>`.md（反模式）

---

## 一、overview.md（项目概览）

**路径**：`projects/<slug>/overview.md`　**type**：`overview`

### frontmatter

```yaml
---
title: "<项目名> 项目概览"
type: overview
project: "<slug>"
repo: "owner/repo"
language: "<主要语言>"
framework: "<主要框架>"
status: active | archived | deprecated
created_at: YYYY-MM-DD
updated_at: YYYY-MM-DD
tags: [技术栈关键词]
---
```

### 正文骨架

```markdown
> 一句话定位：这个项目做什么、给谁用。

## 技术栈
- 语言 / 运行时 / 框架 / 数据库 / 消息队列 / 部署方式

## 核心模块
| 模块 | 职责 | 入口文件 | 关键类/函数（行号） |
|------|------|----------|---------------------|

## 核心数据模型
- 核心实体及其关系（必要时用 Mermaid 画 ER 图）
- 关键表/集合的字段说明（只列关键的，不贴全量 DDL）

## 关键外部依赖
| 服务 | 用途 | 调用方式 | 可靠性评级 |
|------|------|----------|------------|

## ⚠️ 项目特有约束
- 本项目特有的、换一个项目就不适用的约束（如「必须兼容 Java 8 因为客户 X 的生产环境」）
```

---

## 二、decisions.md（技术决策记录）

**路径**：`projects/<slug>/decisions.md`（**单文件含多条**，每条用 `## 决策 N：标题` 分隔）　**type**：`decisions`

### 文件级 frontmatter

```yaml
---
title: "<项目名> 技术决策记录"
type: decisions
project: "<slug>"
updated_at: YYYY-MM-DD
decisions_count: 0
---
```

### 每条决策正文骨架

```markdown
## 决策 N：<决策标题>

- **日期**：YYYY-MM-DD
- **状态**：proposed | accepted | deprecated | superseded

### 背景
为什么要做这个决策？当时面临什么问题？

### 决策
最终选择了什么方案？

### 备选方案
- 方案 A：……（优缺点）
- 方案 B：……（优缺点）

### 理由
为什么选这个而不是别的？

### ⚠️ 适用条件（必须具体）
【硬约束】必须写「因本项目 X 约束，所以选 Y」，禁写「通用最佳实践」。
例：本项目回调要求 5 秒内响应，故选异步消息而非同步轮询。

### 代价
这个决策带来了什么副作用 / 限制？

### 修正记录
<!-- 没有则留空；被推翻时按时间倒序追加 -->
- YYYY-MM-DD：因 XX，适用条件变更为 YY / 已被决策 M 替代
```

---

## 三、gotchas.md（踩坑记录）

**路径**：`projects/<slug>/gotchas.md`（**单文件含多条**，每条用 `## 坑 N：标题` 分隔）　**type**：`gotchas`

### 文件级 frontmatter

```yaml
---
title: "<项目名> 踩坑记录"
type: gotchas
project: "<slug>"
updated_at: YYYY-MM-DD
gotchas_count: 0
---
```

### 每条踩坑正文骨架

```markdown
## 坑 N：<症状简述>

- **发现日期**：YYYY-MM-DD
- **严重程度**：🔴 致命 | 🟡 注意 | 🟢 小坑

### 症状
出了什么问题？错误信息 / 异常行为 / 性能表现。

### 根因
为什么会这样？底层原因。

### 触发条件
什么情况下会踩到？（具体场景 / 输入 / 环境）

### 解法
怎么修？给具体步骤或代码示例。

### 🔑 预防（不可省略）
以后怎么避免再踩？——代码规范 / lint 规则 / 测试用例 / CI 检查（至少一条可落地的）。

### 关联决策
与 decisions.md 中哪条决策相关？（如某决策选了某方案导致此坑）
```

---

## 四、specs/`<module>`.md（模块深度规范）

**路径**：`projects/<slug>/specs/<module>.md`　**type**：`spec`

### frontmatter

```yaml
---
title: "<模块名> 模块规范"
type: spec
project: "<slug>"
module: "<module-name>"
updated_at: YYYY-MM-DD
tags: [模块关键词]
---
```

### 正文骨架

```markdown
> 一句话：这个模块的职责和边界。

## 职责
- 负责什么？不负责什么？（明确边界）

## 核心流程
1. 主流程步骤（必要时用 Mermaid 画时序图/流程图）
2. 关键调用链：Entry → A → B → C（附源码 `文件:行号`）

## 关键接口
| 接口 | 方法/签名 | 职责 | 注意事项（行号） |
|------|-----------|------|------------------|

## 已知边界与限制
- 这个模块处理不了什么？（能力边界）

## 配置
- 本模块特有的配置项（环境变量 / 配置文件 / 默认值）

## 测试
- 测试文件路径 + 关键测试用例覆盖的场景
```

---

## 五、patterns/`<name>`.md（跨项目通用模式）

**路径**：`patterns/<name>.md`（kebab-case，描述问题而非方案）　**type**：`pattern`

> 放这里的模式必须是**跨项目通用**的工程做法；只在单一项目用过的做法，放该项目的 `specs/`。

### frontmatter

```yaml
---
title: "<模式名>"
type: pattern
tags: [模式关键词]
projects: [slug-1, slug-2]   # 在哪些项目观察到
source: "<最初来源>"
updated_at: YYYY-MM-DD
---
```

### 正文骨架

```markdown
> 一句话：这个模式是什么，解决什么问题。

## 场景
什么情况下用？

## 做法
具体怎么做？给代码骨架或设计图。

## 适用条件
什么条件下成立？

## 不适用的情况
什么情况别用，该用什么替代？

## ❌ 反模式示例 / ✅ 正确示例
至少各一个对比。

## 来源
- <项目名> - <简述>
```

---

## 六、anti-patterns/`<name>`.md（反模式）

**路径**：`anti-patterns/<name>.md`　**type**：`anti-pattern`

### frontmatter

```yaml
---
title: "<反模式名>"
type: anti-pattern
tags: [关键词]
projects: [slug-1]
severity: critical | warning | info
updated_at: YYYY-MM-DD
---
```

### 正文骨架

```markdown
> 一句话：这个反模式是什么，为什么是陷阱。

## 错误做法
不要这样做（看起来合理实则有问题）。

## 为什么会犯这个错
它看起来合理的原因。

## 实际后果
这样做之后会发生什么。

## ✅ 正确做法
应该怎么做？最好引用对应 pattern。

## 检测方法
lint 规则 / 代码审查 checklist，怎么提前发现。

## 来源
- <项目名> - <简述>
```

---

## frontmatter 通用字段说明

| 字段 | 含义 | 必填 |
|------|------|------|
| `title` | 文件标题 | ✅ |
| `type` | overview / decisions / gotchas / spec / pattern / anti-pattern | ✅ |
| `project`（或 `slug`） | 所属项目 slug；patterns/anti-patterns 用 `projects` 数组 | ✅ |
| `tags` | 关键词，便于检索 | 推荐 |
| `status` | active / archived / deprecated | 推荐 |
| `updated_at` | 最后更新日期（YYYY-MM-DD），maintain 据此判时效 | ✅ |
| `created_at` | 创建日期 | overview 推荐 |
