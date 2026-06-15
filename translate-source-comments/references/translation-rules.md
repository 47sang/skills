# 翻译规则与术语对照

本文档是 [SKILL.md](../SKILL.md) 的详细参考，定义了「翻译什么、不翻译什么、术语怎么处理」的完整规则。

## 1. 要翻译的内容

| 类型 | 形式 | 翻译范围 |
|------|------|----------|
| Javadoc 块注释 | `/** ... */` | 块内的说明文字 |
| Javadoc 标签说明 | `@param name 说明` / `@return 说明` / `@throws X 说明` | 标签**后面**的说明文字（标签本身不动） |
| 行内注释 | `// 说明` | `//` 后面的文字 |
| YAML 注释 | `# 说明` | `#` 后面的文字 |

## 2. 绝对不能翻译的内容

### 2.1 License 头部
每个文件开头的 Apache-2.0 声明（通常前 15 行），识别特征：
```
/*
 * Copyright 2024-2026 ...
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * ...
 *      http://www.apache.org/licenses/LICENSE-2.0
 * ...
 * limitations under the License.
 */
```
**整块原样保留，一个字都不改。**

### 2.2 代码标识符
- 类名、接口名、枚举名：`ReActAgent`、`Msg`、`MsgRole`
- 方法名、变量名、字段名：`doCall()`、`maxIters`
- 包名、import 语句：`io.agentscope.core`
- 注解名：`@Tool`、`@JsonProperty`、`@SuppressWarnings`
- 泛型参数：`<T extends ContentBlock>`

### 2.3 字符串字面量
双引号 `"..."` 或三引号 `'''...'''`（text block）内的所有内容：
- LLM prompt 模板、system message
- API 协议标识符：`"system-reminder"`、`"task_list"`、`"USER"`
- 错误信息字符串、日志文本
- JSON 字符串、正则字符串

### 2.4 URL、正则、格式串
- `http://...`、`https://...` 链接
- 正则表达式模式
- 格式占位符：`%s`、`%d`、`%n`、`{}`、`{0}`
- **这些绝不能加空格、改大小写、动格式**

### 2.5 Javadoc 标签与 HTML
保留原样（不翻译标签本身）：
- 标签：`@param`、`@return`、`@throws`、`@exception`、`@see`、`@since`、`@deprecated`、`@serial`、`@author`
- 内联标签：`{@code ...}`、`{@link ...}`、`{@linkplain ...}`、`{@inheritDoc}`、`{@value ...}`
  - 注意：`{@code}`/`{@link}` 标签**内部**的代码引用也不翻译
- HTML：`<p>`、`<pre>`、`<code>`、`<ul>`、`<ol>`、`<li>`、`<b>`、`<i>`、`<em>`、`<strong>`

### 2.6 配置 key
YAML/properties 里的配置键名不翻译，只翻注释：
```yaml
agentscope:           # ← key 不翻
  model:
    provider: dashscope  # ← value 看情况，协议值不翻
    # 注释可以翻译
```

### 2.7 已含中文的注释
检测到中文字符（Unicode `一-鿿` 范围）的注释，视为已翻译，**整体跳过**，不要重译、不要"优化"。

## 3. 技术术语处理规则

### 3.1 用「中文(英文)」格式
专业术语首次出现或作为核心概念时，用 `中文(英文)` 格式，兼顾可读性与可检索性：

| 英文 | 推荐译法 |
|------|----------|
| Reactive Programming | 响应式编程(Reactive Programming) |
| Reactor / Project Reactor | 响应式(Reactor) |
| Mono | 单值流(Mono) |
| Flux | 多值流(Flux) |
| Large Language Model (LLM) | 大语言模型(LLM) |
| Retrieval-Augmented Generation (RAG) | 检索增强生成(RAG) |
| Human-in-the-Loop (HITL) | 人机协同(HITL) |
| Chain-of-Thought (CoT) | 思维链(CoT) |
| ReAct (Reasoning+Acting) | 推理与行动(ReAct) |
| Agent | 智能体(Agent) |
| Multi-Agent | 多智能体(Multi-Agent) |
| Tool Use / Function Calling | 工具调用(Tool Use) |
| Structured Output | 结构化输出 |
| Embedding | 向量嵌入(Embedding) |
| Streaming | 流式(Streaming) |
| Middleware | 中间件(Middleware) |
| Hook | 钩子(Hook) |
| Toolkit | 工具箱(Toolkit) |

### 3.2 保留英文原样（业界通用缩写）
这些缩写在中文技术语境下已约定俗成，直接保留英文，不强行中译：

`API` `DTO` `SSRF` `JSON` `XML` `HTTP` `HTTPS` `URL` `URI` `UUID` `JVM` `JDK` `JRE` `MCP` `SDK` `CLI` `CI` `CD` `IoC` `AOP` `ORM` `CRUD` `DAO` `PoC` `TDD`

### 3.3 框架/产品名保留英文
`Spring Boot` `Spring AI` `Maven` `Jackson` `Project Reactor` `AgentScope` `DashScope` `Anthropic` `OpenAI` `Gemini` `Ollama` `JUnit` `Mockito` `OkHttp` `Netty` `SLF4J` `OpenTelemetry`

框架特有的类名（如 `ReActAgent`、`HarnessAgent`、`JsonSession`）更不能翻译。

### 3.4 译文风格
- **意译优先于直译**：`Returns the message ID` → `返回消息的唯一标识`（而非"返回消息ID"，因 ID 是保留缩写可保留，但整体要通顺）
- **符合 Java 开发者阅读习惯**：术语准确、语句简练
- **保持注释长度大致一致**：不要把一行英文膨胀成五行中文
- **保留原注释的结构**：列表还是列表，段落还是段落，代码块还是代码块

## 4. Javadoc 翻译示例

### 示例 1：类级 Javadoc
原文：
```java
/**
 * Represents a message in the AgentScope framework.
 *
 * <p>Messages are the primary communication unit between agents.
 *
 * <p>Content blocks can include text, images, audio, and tool use blocks.
 */
```
译文：
```java
/**
 * 表示 AgentScope 框架中的一条消息。
 *
 * <p>消息是智能体之间通信的基本单元。
 *
 * <p>内容块可以包含文本、图片、音频和工具调用块。
 */
```

### 示例 2：方法 Javadoc 带标签
原文：
```java
/**
 * Gets the role of the message sender.
 *
 * @param name the user name (can be null)
 * @return The message role (user, assistant, system, or tool)
 * @throws IllegalArgumentException if role is invalid
 * @see MsgRole
 */
```
译文：
```java
/**
 * 获取消息发送者的角色。
 *
 * @param name 用户名（可为 null）
 * @return 消息角色（user、assistant、system 或 tool）
 * @throws IllegalArgumentException 当角色非法时抛出
 * @see MsgRole
 */
```
注意：`@param`/`@return`/`@throws`/`@see` 标签本身和 `MsgRole`（类名）保留原样，`null`/`user`/`assistant` 等枚举值字符串保留。

### 示例 3：含代码块的 Javadoc
原文：
```java
/**
 * Example usage:
 * <pre>{@code
 * // Create a model
 * DashScopeChatModel model = DashScopeChatModel.builder()
 *     .modelName("qwen-plus")
 *     .build();
 * }</pre>
 */
```
译文（只翻注释行，代码原样）：
```java
/**
 * 使用示例：
 * <pre>{@code
 * // 创建模型
 * DashScopeChatModel model = DashScopeChatModel.builder()
 *     .modelName("qwen-plus")
 *     .build();
 * }</pre>
 */
```
注意：`DashScopeChatModel`、`modelName`、`"qwen-plus"` 全部原样。

## 5. 常见陷阱

| 陷阱 | 错误做法 | 正确做法 |
|------|----------|----------|
| 翻译字符串里的提示词 | `"You are a helpful assistant."` → `"你是一个有用的助手。"` | **不翻译**，字符串字面量保持原样 |
| 翻译枚举值 | `MsgRole.USER` → `MsgRole.用户` | **不翻译**，保留 `USER` |
| 给 URL 加空格 | `http://x.y` → `http:// x.y` | **不动**，原样保留 |
| 翻译 `@link` 内的类名 | `{@link Toolkit}` → `{@link 工具箱}` | **不翻译**，保留 `Toolkit` |
| 重复翻译已汉化的注释 | 重新翻译已有中文 | **跳过**，保留原样 |
| 混淆 `Mono` 的代码类型与注释概念 | `Mono<String>` → "单声道"；或注释里 "a Mono" 照抄不译 | 代码里的 `Mono<String>` 类型**不翻译**；注释说明文字里作为概念提及的 Mono 译为「单值流(Mono)」 |
| 并发开多个翻译代理 | 10 个子代理同时翻译 | 串行、小批次，避免配额耗尽 |

## 6. 译后处理

1. **格式统一**：`mvn spotless:apply`（脚本的 Javadoc 重建已标准化，但跑一遍确保 AOSP 风格一致）
2. **编译验证**：`mvn compile`，确认没误伤代码
3. **License 检查**：CI（apache/skywalking-eyes）会校验 License 头未丢失，确认头部原样
4. **抽查 diff**：`git diff` 逐文件看一眼，重点确认 URL、字符串、import 没被动
