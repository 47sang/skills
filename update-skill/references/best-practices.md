# 技能最佳实践

在 `.agents/skills/` 中创建有效技能的详细编写指导。

## 渐进式披露

技能使用加载系统来高效管理上下文：

1. **元数据（name + description）** - 启动时始终加载
2. **SKILL.md 正文** - 技能触发时加载
3. **参考文件** - 仅在需要时加载

### 何时使用参考

将 `SKILL.md` 保持在 150-200 行以内。当内容超过此限制时：

**模式 1：带参考的高层指南**

`SKILL.md` 包含核心工作流程并指向详细参考：

```markdown
## 高级功能

- **详细配置**：参阅 [references/config.md](references/config.md)
- **API 参考**：参阅 [references/api.md](references/api.md)
- **示例**：参阅 [references/examples.md](references/examples.md)
```

**模式 2：特定领域组织**

对于具有多个独立领域的技能，按领域组织：

```
skill-name/
├── SKILL.md（概述和导航）
└── references/
    ├── domain-a.md
    ├── domain-b.md
    └── domain-c.md
```

当用户使用 domain-a 时，代理仅加载 domain-a.md，而不加载其他文件。

**模式 3：条件详情**

内联显示基本内容，链接到高级内容：

```markdown
## 基本用法

[核心说明在此处]

**高级配置**：参阅 [references/advanced.md](references/advanced.md)
```

### 重要指南

- **保持参考仅一层深度** - 所有参考文件都应直接从 `SKILL.md` 链接
- **避免嵌套参考** - 不要创建引用其他文件的参考
- **添加目录** - 对于超过 100 行的参考文件，在顶部包含目录

## 编写有效的描述

描述字段启用技能发现。代理使用它来决定何时加载技能。

### 描述最佳实践

1. **具体并包含关键词**
   - 好："在代码库中添加一个特性标志来控制代码更改。"
   - 避免："帮助处理功能。"

2. **同时包含内容和时机**
   - 技能做什么："编写、改进和运行 Rust 单元测试"
   - 何时使用："在 Rust 代码库中"

3. **使用第三人称**
   - 好："添加特性标志来控制代码更改"
   - 避免："我可以帮你添加特性标志"
   - 避免："你可以用这个来添加特性标志"

4. **包含触发词**
   - 提及特定的文件、命令或概念
   - 示例："在处理 PDF 文件、表单或文档提取时使用"

## 简洁性原则

上下文窗口在所有技能、对话历史和系统提示之间共享。每个标记都很重要。

### 默认假设：代理已经足够聪明

仅添加代理还没有的上下文。质疑每一个部分：
- "代理真的需要这个解释吗？"
- "我能假设代理已经知道这个吗？"
- "这个段落值得它的标记成本吗？"

**好（简洁）：**

```markdown
## 提取 PDF 文本

使用 pdfplumber 进行文本提取：

```python
import pdfplumber

with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```
```

**坏（冗长）：**

```markdown
## 提取 PDF 文本

PDF（便携式文档格式）文件是一种包含文本、图像和其他内容的常见文件格式。要提取 PDF 的文本，你需要使用一个库。有许多可用于 PDF 处理的库，但我们推荐 pdfplumber，因为它易于使用，能处理大多数情况。首先，你需要使用 pip 安装它。然后你可以使用下面的代码...
```

简洁版本假设代理知道 PDF 是什么以及库如何工作。

## 代码示例格式

### 语法高亮

始终为代码块指定语言：

```rust
pub fn example() {
    println!("始终指定语言");
}
```

```bash
cargo nextest run --workspace
```

### 示例结构

对于基于工作流程的技能，展示前后对比或逐步说明：

```markdown
### 之前：
```rust
if FeatureFlag::YourFeature.is_enabled() {
    // 新行为
} else {
    // 旧行为（死代码）
}
```

### 之后：
```rust
// 新行为（无条件启用）
```
```

### 内联命令

对于 shell 命令，显示带有标志的完整命令：

```bash
cargo clippy --workspace --all-targets --all-features --tests -- -D warnings
```

如有必要解释不明显的标志，但优先使用自文档化的命令。

## 工作流程与简单说明

### 何时使用工作流程

对于顺序重要的多步骤流程，使用编号步骤：

```markdown
## 工作流程

1. 分析表单结构
2. 创建字段映射
3. 验证映射
4. 填写表单
5. 验证输出
```

对于复杂工作流程，包含检查清单：

```markdown
复制此检查清单并跟踪进度：

```
任务进度：
- [ ] 步骤 1：分析表单
- [ ] 步骤 2：创建映射
- [ ] 步骤 3：验证
- [ ] 步骤 4：填写表单
- [ ] 步骤 5：验证
```
```

### 何时使用简单说明

对于简单的任务，跳过工作流程结构：

```markdown
## 添加特性标志

将功能添加到 `app/Cargo.toml`：

```toml
[features]
your_feature_name = []
```

然后在运行时检查后面进行代码控制：

```rust
if FeatureFlag::YourFeatureName.is_enabled() {
    // 特性开关控制的代码
}
```
```

## 常见反模式

### ❌ Windows 风格路径

始终使用正斜杠：
- ✓ 好：`scripts/helper.py`、`references/guide.md`
- ✗ 避免：`scripts\helper.py`、`references\guide.md`

### ❌ 模糊描述

要具体：
- ✗ 避免："帮助处理文档"
- ✓ 好："从 PDF 文件中提取文本和表格"

### ❌ 过多选项

除非必要，否则不要展示多种方法：
- ✗ 避免："你可以使用 pypdf，或 pdfplumber，或 PyMuPDF，或..."
- ✓ 好："使用 pdfplumber 进行文本提取。对于需要 OCR 的扫描 PDF，改用 pdf2image 配合 pytesseract。"

### ❌ 时间敏感信息

不要包含日期或版本特定的指导：
- ✗ 避免："如果你在 2025 年 8 月之前做这件事，使用旧 API。"
- ✓ 好：使用带有弃用说明的"当前方法"和"旧模式"部分

### ❌ 不一致的术语

选择一个术语并在整个文档中使用：
- ✗ 避免：混用"API 端点"、"URL"、"API 路由"、"路径"
- ✓ 好：始终使用"API 端点"

### ❌ 解释明显的内容

跳过代理已经知道的概念的解释：
- ✗ 避免："Git 是一个跟踪文件更改的版本控制系统..."
- ✓ 好："使用 `git --no-pager diff` 查看无分页的更改"

### ❌ 过度构建简单技能

并非每个技能都需要概述、最佳实践和示例部分。仅使用增加价值的部分：
- 简单技能：标题 + 说明
- 中等技能：标题 + 概述 + 说明
- 复杂技能：包含多个部分的完整结构

## 命名约定

对技能使用一致的命名模式：

**推荐：动名词形式（动词 + -ing）**
- `processing-pdfs`
- `analyzing-spreadsheets`
- `managing-databases`
- `testing-code`

**可接受的替代方案：**
- 名词短语：`pdf-processing`、`spreadsheet-analysis`
- 面向动作：`process-pdfs`、`analyze-spreadsheets`

**避免：**
- 模糊名称：`helper`、`utils`、`tools`
- 过于通用：`documents`、`data`、`files`

一致的命名使技能更易于参考、一目了然和组织。

## 技能迭代

技能通过使用而改进。更新技能时：

1. **观察使用情况** - 注意代理在哪里挣扎或成功
2. **识别差距** - 缺少或不清楚哪些信息？
3. **更新目标部分** - 修复特定问题而不过度解释
4. **测试更改** - 在类似任务上使用技能以验证改进

保持迭代的聚焦性。不要预先添加内容——仅添加通过实际使用证明必要的内容。
