---
name: translate-source-comments
description: 将 Java（及 YAML）源代码中的英文 Javadoc 注释和行内注释翻译为中文，保留 License 头、URL、正则、代码标识符与字符串字面量不变。当用户要求把整个项目或部分源文件的英文注释翻译成中文、或提到"翻译注释 / 翻译 javadoc / 注释汉化"时使用。
---

# 翻译源代码注释

把 Java 源文件里的英文注释（Javadoc 块注释、`//` 行内注释）翻译成中文，YAML 配置文件里的 `#` 注释同理。核心原则：**只动注释文字，绝不碰代码**。

## ⚠️ 为什么用脚本 + Claude 分工（重要）

不要让 Claude（或子代理）用 Read/Edit 逐个文件翻译——2000+ 文件会让工具调用数爆炸、耗尽 API 配额（这是踩过的坑）。也不要调第三方翻译 API（Google Translate 等），既慢又会限流，而且翻译质量不如 Claude 本身。

**正确分工**：
- **机械的提取与应用** → 交给本地 Python 脚本（零配额消耗、几秒完成）
- **只有"翻译"这一步** → 用 Claude 自己的语言能力（这是 Claude 的强项，无需外部 API）

## 🔑 铁律（绝对不能违反）

详见 [references/translation-rules.md](references/translation-rules.md)，最关键的是：

1. **License 头部绝对不动** — 文件开头 Apache-2.0 声明（`Copyright`/`Licensed under`/`http://www.apache.org/...`），原样保留。
2. **已有中文的注释/文件整体跳过** — 检测到中文字符（`一-鿿`）就视为已翻译，不要重译。
3. **URL、正则、格式字符串绝对不动** — `http://`、`https://`、正则模式、`%s`/`%d` 占位符原样保留，不要加空格、不要改格式。
4. **代码标识符绝对不动** — 类名、方法名、变量名、import、注解名、字符串字面量（`"..."`、`'''...'''`）。
5. **Javadoc 标签关键字保留英文** — `@param`、`@return`、`@throws`、`@see`、`@deprecated`、`{@code}`、`{@link}`、`<p>` 等，只翻译标签后面的说明文字。
6. **技术术语用「中文(英文)」格式** — 如 `检索增强生成(RAG)`、`大语言模型(LLM)`、`响应式(Reactive)`、`单值流(Mono)`/`多值流(Flux)`、`智能体(Agent)`；`API`/`JSON`/`HTTP` 等通用缩写保留英文。

## 📋 完整工作流

### 第 1 步：准备文件列表

生成一个 `filelist.txt`，每行一个待翻译文件的**绝对路径**。例如全量扫描某个模块：

```bash
cd /path/to/project
find agentscope-core/src -name "*.java" > /tmp/filelist.txt
# 若要同时翻译 YAML 配置注释，可追加：
find . -name "*.yml" -not -path "*/target/*" >> /tmp/filelist.txt
```

### 第 2 步：提取注释 → JSON（脚本，零配额）

```bash
python3 scripts/extract_comments.py /tmp/filelist.txt /tmp/comments.json --root "$(pwd)"
```

输出 `comments.json`，每条注释含 `id` / `file` / `type` / `start` / `end` / `indent` / `source`。已含中文的文件会自动跳过。

### 第 3 步：切小批次（脚本，零配额）

```bash
python3 scripts/split_comments.py /tmp/comments.json /tmp/batches --size 100
```

把注释切成每批 ≤100 条的 `batch_001.json`、`batch_002.json`…（每条已带空的 `target` 字段）。

### 第 4 步：Claude 分批翻译（核心，消耗配额但可控）

对每个 `batch_NNN.json`：
1. **Read** 该批次文件。
2. 把每个元素的 `source`（英文）翻译成中文，填到对应 `target` 字段，**保持 `id`/`file`/`type`/`start`/`end`/`indent` 完全不变**。
3. **Write** 回同一文件（覆盖）。

⚠️ 翻译时遵守铁律：保留 `@param`/`@return`/`{@code}`/`{@link}`/`<p>`/`<pre>`/`<ul>`/`<li>` 等 Javadoc 标签与 HTML 标记原样，只翻译说明文字；保留代码示例块（`<pre>{@code ...}`）里的代码原样，只翻其中的英文注释（若有）。

⚠️ 控制节奏：每批 100 条、一次处理一批。不要并发开多个子代理翻译（会触发并发/配额限制）。串行处理最稳。

### 第 5 步：写回源文件（脚本，零配额）

```bash
python3 scripts/apply_translations.py --dir /tmp/batches --root "$(pwd)"
```

读取所有批次里的 `target`，按 `start`/`end` 行号写回各源文件。`target` 为空的条目跳过（保留原文）。

### 第 6 步：验证

```bash
# 1. 确认没破坏代码：编译或跑测试
mvn -q compile

# 2. 翻译后 Javadoc 被标准化为统一格式，跑 spotless 统一风格
mvn spotless:apply

# 3. 抽查几个文件，确认 License 头、URL、字符串字面量都没被动过
git diff --stat
```

## 🧪 提交前自检清单

对任意一个被改的文件，逐项确认：
- [ ] License 头部（前 ~15 行）原样未动
- [ ] 所有 `http://`/`https://` 链接原样未动
- [ ] 字符串字面量（双引号内）未被翻译
- [ ] `import` 语句、类名、方法名未被翻译
- [ ] `@param`/`@return`/`@throws` 等标签关键字是英文
- [ ] 正则、`%s`/`%d` 占位符原样未动
- [ ] 编译通过（`mvn compile`）

## 📐 工作流原理（理解脚本行为）

- **提取**：对每个 Javadoc 块，记录起始/结束行号与缩进，把 `*` 之后的内容抽成纯文本。已含中文的文件整体跳过。
- **重建**：`apply` 把译文按标准格式重建（`/**` 单独一行 → 内容每行加 ` * ` 前缀 → ` */` 结尾），缩进从提取时记录的 `indent` 恢复。**单行 `/** x */` 会被标准化为多行**——这是预期行为，符合 google-java-format，跑 `spotless:apply` 即可统一。
- **行号安全**：同一文件按起始行号从后往前应用，避免行号位移错乱。

## 📁 文件说明

- `scripts/extract_comments.py` — 提取注释为 JSON（支持 `--yaml` 同时处理 YAML）
- `scripts/split_comments.py` — 切小批次，便于分批翻译
- `scripts/apply_translations.py` — 把译文写回源文件
- `references/translation-rules.md` — 详细翻译规则、技术术语对照表、常见陷阱

## ⚠️ 常见陷阱

- **不要并发开多个翻译子代理**：会触发 API 并发上限（`429 concurrency reached`）或 5 小时配额耗尽。串行、小批次最稳。
- **不要用第三方翻译 API**：Claude 自己翻译质量更好，且不依赖网络/不受外部限流。
- **批次别太大**：单批超过 ~150 条，Claude 一次 Write 容易截断或遗漏。100 条/批是甜点。
- **翻译完一定跑 `mvn compile`**：脚本只动注释，但万一误伤，编译能立刻发现。
