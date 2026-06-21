# Python 源代码注释翻译

把 Python 源文件里的英文注释（文档字符串、`#` 行内注释）翻译成中文。核心原则：**只动注释文字，绝不碰代码**。

## ⚠️ 为什么用脚本 + Claude 分工（重要）

不要让 Claude（或子代理）用 Read/Edit 逐个文件翻译——14000+ 条注释会让工具调用数爆炸、耗尽 API 配额（这是踩过的坑）。也不要调第三方翻译 API（Google Translate 等），既慢又会限流，而且翻译质量不如 Claude 本身。

**正确分工**：
- **机械的提取与应用** → 交给本地 Python 脚本（零配额消耗、几秒完成）
- **只有"翻译"这一步** → 用 Claude 自己的语言能力（这是 Claude 的强项，无需外部 API）

## 🔑 铁律（绝对不能违反）

详见 [references/translation-rules.md](references/translation-rules.md)，最关键的是：

1. **`_()` gettext_lazy 字符串绝对不动** — Django 的国际化系统会处理这些，不在本工具范围内。
2. **已有中文的注释/文件整体跳过** — 检测到中文字符（`一-鿿`）就视为已翻译，不要重译。
3. **URL、正则、格式字符串绝对不动** — `http://`、`https://`、正则模式、`%s`/`%d`/`{name}` 占位符原样保留。
4. **代码标识符绝对不动** — 类名、方法名、变量名、import、装饰器名、类型注解、字符串字面量（`"..."`）。
5. **文档字符串标签关键字保留英文** — `Args:`、`Returns:`、`Raises:`、`Example:`、`Note:` 等，只翻译标签后面的说明文字。
6. **技术术语用「中文(英文)」格式** — 如 `查询集(QuerySet)`、`序列化器(Serializer)`、`装饰器(Decorator)`；`Django`/`DRF`/`API` 等保留英文。
7. **`r"""` 原始字符串前缀保留** — 正则相关的文档字符串使用 `r"""` 前缀，不能去掉。

## 📋 完整工作流

### 第 1 步：准备文件列表

生成一个 `filelist.txt`，每行一个待翻译文件的**绝对路径**：

```bash
cd /path/to/project
# 扫描 backend Python 文件（排除 migrations/fixtures 等）
find src/backend -name "*.py" \
  -not -path "*/migrations/*" \
  -not -path "*/fixtures/*" \
  -not -path "*/test_data/*" \
  -not -path "*/static/*" \
  -not -path "*/templates/*" \
  -not -path "*/locale/*" \
  > /tmp/python_filelist.txt
```

### 第 2 步：提取注释 → JSON（脚本，零配额）

```bash
python3 scripts/extract_comments.py /tmp/python_filelist.txt /tmp/comments.json --root "$(pwd)"
```

输出 `comments.json`，每条注释含 `id` / `file` / `type` / `start` / `end` / `indent` / `source` / `prefix` / `docstring_style`。

注释类型：
- `module_docstring` — 模块级文档字符串（文件顶部）
- `class_docstring` — 类文档字符串
- `function_docstring` — 函数/方法文档字符串
- `inline` — `#` 行内注释

已含中文的文件会自动跳过。

### 第 3 步：切小批次（脚本，零配额）

```bash
python3 scripts/split_comments.py /tmp/comments.json /tmp/batches --size 100
```

把注释切成每批 ≤100 条的 `batch_001.json`、`batch_002.json`…（每条已带空的 `target` 字段）。

### 第 4 步：Claude 分批翻译（核心，消耗配额但可控）

对每个 `batch_NNN.json`：
1. **Read** 该批次文件。
2. 把每个元素的 `source`（英文）翻译成中文，填到对应 `target` 字段，**保持 `id`/`file`/`type`/`start`/`end`/`indent` 完全不变**。**关键：`target` 的行数必须与 `source` 完全一致**（多行文档字符串的每一行一一对应），因为写回脚本按行索引映射到原始物理行；行数不符会导致内容错位或丢失。
3. **Write** 回同一文件（覆盖）。

⚠️ 翻译时遵守铁律：保留 `Args:`/`Returns:`/`Raises:`/`Example:`/` ```py ` 等标签和标记原样，只翻译说明文字；保留代码示例块中的代码原样。

⚠️ `target` 译文尽量避免出现 `"""`（三引号）：普通 docstring 写回时会自动转义，但 `r"""` 原始字符串无法转义——若译文含三引号，`r` 前缀的 docstring 会损坏。

⚠️ 控制节奏：每批 100 条、一次处理一批。不要并发开多个子代理翻译（会触发并发/配额限制）。串行处理最稳。

### 第 5 步：写回源文件（脚本，零配额）

```bash
python3 scripts/apply_translations.py --dir /tmp/batches --root "$(pwd)"
```

读取所有批次里的 `target`，按 `start`/`end` 行号写回各源文件。`target` 为空的条目跳过（保留原文）。

### 第 6 步：验证

```bash
# 1. 确认没破坏代码：语法检查
python3 -c "
import ast, os
for root, dirs, files in os.walk('src/backend'):
    dirs[:] = [d for d in dirs if d not in ('migrations','fixtures','test_data','static','templates','locale')]
    for f in files:
        if not f.endswith('.py'): continue
        p = os.path.join(root, f)
        try: ast.parse(open(p).read())
        except SyntaxError as e: print(f'ERROR: {p}: {e}')
print('Done')
"

# 2. 抽查几个文件，确认 _() 字符串、URL、import 没被动
git diff --stat
git diff src/backend/InvenTree/InvenTree/models.py | head -30
```

## 📐 工作流原理（理解脚本行为）

### 提取
- 使用 Python `ast` 模块解析源文件，精确定位文档字符串位置
- 通过 `ast.walk` 遍历 AST 所有层级节点（Module/ClassDef/FunctionDef/AsyncFunctionDef），因此 `if`/`try`/`for`/`with` 等条件块或语句块内嵌套定义的函数/类的 docstring 也会被正确提取
- 绝不误伤赋值语句中的字符串字面量（`msg = "..."`）
- 提取时去除文档字符串内容的公共缩进，统一保留原始缩进信息用于写回
- 已含中文的文件整体跳过
- 行内注释提取时，若 `#` 的前一个字符是 URL 字符（字母数字或 `./_-~`）、`#` 后紧跟非空字符、且该 `#` 所在行前半段包含 `http://` 或 `https://`，则判定为 URL 锚点（fragment）并跳过，不当作注释提取
- `# pragma: no cover`、`# type: ignore[...]`、`# TODO:` 等特殊注释在提取阶段过滤

### 重建
- 单行文档字符串保持单行格式：`"""content"""`
- 多行文档字符串采用物理行就地替换，保留原始布局（引号 `"""` 的位置、缩进、空行、Google-style 中 Args/Returns 等标签下参数说明的相对缩进）
- docstring 内的空行输出为真空行（不加 indent），避免引入尾随空格
- 原始字符串前缀 `r` 保留
- 行内注释替换为 `# 译文`
- 同一文件按起始行号从后往前应用，避免行号位移

### JSON 格式

```json
[
  {
    "id": "C00000",
    "file": "src/backend/InvenTree/InvenTree/__init__.py",
    "type": "module_docstring",
    "start": 1,
    "end": 4,
    "indent": "",
    "source": "The InvenTree module provides...",
    "prefix": "",
    "docstring_style": "multi"
  },
  {
    "id": "C00001",
    "file": "src/backend/InvenTree/InvenTree/validators.py",
    "type": "function_docstring",
    "start": 15,
    "end": 15,
    "indent": "    ",
    "source": "Ensure that a given unit is a valid physical unit.",
    "prefix": "",
    "docstring_style": "single"
  },
  {
    "id": "C00002",
    "file": "src/backend/InvenTree/InvenTree/api.py",
    "type": "inline",
    "start": 54,
    "end": 54,
    "indent": "    ",
    "source": "Check if the file exists"
  }
]
```

字段说明：
- `id`: 全局唯一编号
- `file`: 相对项目根的路径
- `type`: 注释类型
- `start`/`end`: 行号（1 基），文档字符串的起止行
- `indent`: 文档字符串所在行的缩进字符串（如 `""` 或 `"    "`）
- `source`: 提取的原文内容
- `prefix`: 文档字符串前缀（`r`/`R`/`u`/`U` 或空）
- `docstring_style`: `single`（单行）或 `multi`（多行）

## 📁 文件说明

- `scripts/extract_comments.py` — 提取 Python 注释为 JSON（使用 AST 精确定位 docstring）
- `scripts/split_comments.py` — 切小批次，便于分批翻译
- `scripts/apply_translations.py` — 把译文写回源文件
- `references/translation-rules.md` — 详细翻译规则、术语对照表、常见陷阱

## ⚠️ 常见陷阱

- **不要并发开多个翻译代理**：会触发 API 并发上限（`429 concurrency reached`）或配额耗尽。串行、小批次最稳。
- **`_()` gettext 字符串不要翻译**：这些是 Django 国际化系统的标记，翻译后会破坏运行时的语言切换功能。
- **`r"""` 前缀不能丢**：丢失后正则中的反斜杠会被 Python 解释为转义字符。
- **批次别太大**：单批超过 ~100 条，Claude 一次 Write 容易截断或遗漏。100 条/批是甜点。
- **翻译完一定跑语法检查**：`python3 -c "import ast; ast.parse(open(...).read())"` 能立刻发现脚本是否误伤了代码结构。
