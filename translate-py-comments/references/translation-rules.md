# Python 项目翻译规则与术语对照

本文档是 [SKILL.md](../SKILL.md) 的详细参考，定义了「翻译什么、不翻译什么、术语怎么处理」的完整规则。

## 1. 要翻译的内容

| 类型 | 形式 | 翻译范围 |
|------|------|----------|
| 模块文档字符串 | 文件顶部的 `"""..."""` | 块内说明文字 |
| 类文档字符串 | `class X:` 下方的 `"""..."""` | 块内说明文字 |
| 函数/方法文档字符串 | `def func():` 下方的 `"""..."""` | 块内说明文字 |
| 文档字符串标签说明 | `Args: name 说明` / `Returns: 说明` / `Raises: 说明` | 标签后面的说明文字 |
| 行内注释 | `# 说明` | `#` 后面的文字 |
| `class Meta:` 内文档字符串 | Django 模型内部 `class Meta:` 的 `"""..."""` | 块内说明文字 |

## 2. 绝对不能翻译的内容

### 2.1 License 头部
每个文件开头的版权声明（通常前 15 行），识别特征：
```python
"""
InvenTree - An open-source inventory management system
...
"""
```
或
```python
# InvenTree - An open-source inventory management system
# Copyright ...
```
**整块原样保留，一个字都不改。**

### 2.2 代码标识符
- 类名、函数名、方法名：`DiffMixin`, `validate_physical_units`, `get_db_instance`
- 变量名、字段名：`maxIters`, `reference_int`, `fmt_string`
- 模块名、import 语句：`import django.db.models`, `from InvenTree.helpers import ...`
- 装饰器名：`@receiver`, `@dataclass`, `@property`, `@admin.register`
- 类型注解：`-> str`, `Optional[dict]`, `QuerySet`, `Callable`
- 泛型参数：`Serializer[SomeType]`, `dict[str, Any]`
- 字符串格式化占位符：`{ref:04d}`, `{name}`, `%(name)s`, `%s`, `%d`

### 2.3 字符串字面量（非文档字符串）
- 代码中的普通字符串：`'http://example.com'`, `"PO-???-{ref:04d}"`, `f'Value {x}'`
- `_()` gettext_lazy 调用内的字符串：`_('Invalid physical unit')`
  - 这些由 Django i18n 系统处理，不在此工具翻译范围内
- Django 模型字段的 `verbose_name` 和 `help_text`：
  ```python
  name = models.CharField(
      verbose_name=_('Name'),
      help_text=_('Description of the part name'),
  )
  ```
- JSON 数据、日志消息模板、API 响应字符串

### 2.4 URL、正则、格式串
- `http://...`、`https://...` 链接
- 正则表达式模式（尤其 docstring 中的示例正则）
- 格式占位符：`%s`、`%d`、`{ref}`、`{0}`、`{name:04d}`
- **这些绝不能加空格、改大小写、动格式**

### 2.5 Python 文档字符串标签
保留原样（不翻译标签本身）：
- Google-style：`Args:`、`Arguments:`、`Returns:`、`Return:`、`Raises:`、`Raise:`、`Example:`、`Note:`、`See Also:`
- reStructuredText：`:param name:`、`:type name:`、`:returns:`、`:raises:`
- 代码块标记：` ```py `、` ```python `
- 内联代码：`` `code` ``

### 2.6 Django 特有配置
- 模型字段参数：`blank=True`、`null=True`、`max_length=100`、`unique=True`
- Django 选项：`abstract = True`、`db_table = '...'`、`app_label = '...'`
- DRF 字段参数：`read_only=True`、`required=False`

### 2.7 特殊注释
以下注释在提取阶段已被过滤，不进入翻译流程：
- `# pragma: no cover` — 覆盖率排除标记
- `# type: ignore[xxx]` — 类型检查忽略
- `# TODO:` / `# FIXME:` / `# HACK:` / `# noqa` — 开发标记
- `# noinspection ...` — IDE 检查抑制

### 2.8 注释掉的代码行
提取脚本会自动过滤以下特征的 `#` 行内注释（视为代码而非说明文字）：
- 包含 `{}` `[]` 等 Python 字面量符号（字典、列表）
- 以 Python 赋值语句开头（`identifier = value` 或 `self.attr = value`）
- 包含点号调用模式（`obj.method(` 或 `self.attr(`）

例如以下行会被过滤，不进入翻译：
```python
# limit_choices_to={'salable': True},
# order = self.context['order']
# sales_order = SalesOrder.objects.create(
# customer=supplier,
```

**原因**：这类注释行的文本本身就是可执行的 Python 代码，翻译其中的关键字或语法会导致代码被破坏。如需翻译此类注释，应手动处理。

### 2.9 已含中文的文档/注释
检测到中文字符（Unicode `一-鿿` 范围）的文件整体跳过，不要重译。

## 3. 技术术语处理规则

### 3.1 用「中文(英文)」格式
专业术语首次出现或作为核心概念时，用 `中文(英文)` 格式：

| 英文 | 推荐译法 |
|------|----------|
| Django | Django |
| Django REST Framework | Django REST 框架(DRF) |
| Django Q | Django Q |
| MPTT (Modified Preorder Tree Traversal) | 改进前序树遍历(MPTT) |
| Model | 模型(Model) |
| Serializer | 序列化器(Serializer) |
| ViewSet | 视图集(ViewSet) |
| QuerySet | 查询集(QuerySet) |
| Migration | 数据库迁移(Migration) |
| Signal | 信号(Signal) |
| Receiver | 接收器(Receiver) |
| Middleware | 中间件(Middleware) |
| Mixin | 混入类(Mixin) |
| Decorator | 装饰器(Decorator) |
| Context Manager | 上下文管理器(Context Manager) |
| Dataclass | 数据类(Dataclass) |
| Type Hint | 类型提示(Type Hint) |
| Abstract Base Class (ABC) | 抽象基类(ABC) |
| F-string | f-string |
| Generator | 生成器(Generator) |
| Iterator | 迭代器(Iterator) |
| Docstring | 文档字符串(Docstring) |
| REPL | REPL |
| API | API |
| URL | URL |
| UUID | UUID |
| JSON | JSON |
| HTTP | HTTP |
| HTTPS | HTTPS |
| REST | REST |
| ORM | ORM |
| CRUD | CRUD |
| CI | CI |
| CD | CD |
| DRF Spectacular | DRF Spectacular |
| django-allauth | django-allauth |
| structlog | structlog |
| Pint | Pint |
| django-taggit | django-taggit |
| python-akismet | python-akismet |
| django-q | django-q |

### 3.2 保留英文原样（业界通用缩写）
`API` `JSON` `HTTP` `HTTPS` `URL` `UUID` `REST` `ORM` `CRUD` `CI` `CD` `CSRF` `CORS` `JWT` `OAuth` `LDAP` `SQL` `NoSQL`

### 3.3 框架/库名保留英文
`Django` `Django REST Framework` `Django Q` `MPTT` `django-allauth` `django-taggit` `structlog` `Pint` `django-money` `django-stdimage` `drf-spectacular` `django-filter`

### 3.4 译文风格
- **意译优先于直译**：确保译文对 Python/Django 开发者来说自然通顺
- **符合 Django 开发者阅读习惯**：术语准确、语句简练
- **保持文档字符串结构**：列表还是列表，段落还是段落，代码块还是代码块
- **保留 Google-style 格式**：`Args:` / `Returns:` / `Raises:` 等标签后换行，内容缩进
- **保留 `r"""` 前缀**：原始字符串文档字符串的前缀不改变

## 4. 本项目特有模式

### 4.1 gettext_lazy 字符串（不翻译）

项目中广泛使用 Django 的 `gettext_lazy` 进行运行时翻译：
```python
from django.utils.translation import gettext_lazy as _

name = models.CharField(
    verbose_name=_('Name'),
    help_text=_('Description of the part'),
)
error = ValidationError(_('Invalid physical unit'))
```

`_()` 包裹的字符串由 Django i18n 系统在运行时翻译，**此工具不动这些字符串**。

### 4.2 Django 模型 Mixin 的 class Meta: 文档字符串

大量抽象 Mixin 类包含以下重复出现的文档字符串：
```python
class Meta:
    """Metaclass options for this mixin.

    Note: abstract must be true, as this is only a mixin, not a separate table
    """
    abstract = True
```

翻译时需翻译内容，保留 `class Meta:` 结构和 `abstract = True` 不动。

### 4.3 原始字符串文档字符串（r"""）

项目中 2 处使用 `r"""` 前缀，因为文档字符串包含正则反斜杠：
```python
def construct_format_regex(fmt_string: str) -> str:
    r"""Construct a regular expression based on a provided format string.
    ...
    Returns:
        str: A regular expression pattern e.g. ^PO\-...\-(?P<ref>.*)$
    """
```

**必须保留 `r` 前缀**，且不修改正则内容。

### 4.4 Google-style 文档字符串格式

项目使用 Google-style 文档字符串（通过 `ruff` 的 `pydocstyle` 规则 `convention = "google"` 强制），常见结构：
```python
def function_name(param: str) -> bool:
    """Short summary line.

    Longer description that can span multiple paragraphs.

    Args:
        param: Description of the parameter.

    Returns:
        bool: Description of the return value.

    Raises:
        ValueError: When the input is invalid.

    Example:
        >>> function_name("test")
        True
    """
```

翻译时保留 `Args:`、`Returns:`、`Raises:`、`Example:` 等标签，只翻译标签后的说明文字。

**注意**：项目中存在不一致的标签写法（`Args:` vs `Arguments:`），翻译时保留原文标签。

### 4.5 代码示例块

文档字符串中可能包含代码示例：
```python
Example:
class MySerializer(FilterableSerializerMixin, serializers.ModelSerializer):
    my_optional_field = OptionalField(
        serializer_class=serializers.CharField,
        default_include=False,
    )
```

**只翻译注释行**，代码行（类名、方法名、关键字参数）原样保留。

### 4.6 `__init__.py` 模块文档字符串

每个子模块的 `__init__.py` 通常包含简短说明：
```python
"""The Part module is responsible for Part management."""
```

翻译时保持单行格式。

## 5. 翻译示例

### 示例 1：模块级文档字符串
原文：
```python
"""The InvenTree module provides high-level management and functionality.

It provides a number of helper functions and generic classes which are used by InvenTree apps.
"""
```
译文：
```python
"""InvenTree 模块提供高级管理和功能。

它提供了一系列辅助函数和通用类，供 InvenTree 应用使用。
"""
```

### 示例 2：带 Google-style 标签的函数文档字符串
原文：
```python
def validate_physical_units(unit):
    """Ensure that a given unit is a valid physical unit."""
```
译文：
```python
def validate_physical_units(unit):
    """确保给定的单位是有效的物理单位。"""
```

### 示例 3：多行文档字符串带 Args/Returns
原文：
```python
def construct_format_regex(fmt_string: str) -> str:
    r"""Construct a regular expression based on a provided format string.

    Args:
        fmt_string: A typical format string e.g. "PO-???-{ref:04d}"

    Returns:
        str: A regular expression pattern e.g. ^PO\-...\-(?P<ref>.*)$

    Raises:
        ValueError: Format string is invalid
    """
```
译文：
```python
def construct_format_regex(fmt_string: str) -> str:
    r"""根据提供的格式字符串构造正则表达式。

    Args:
        fmt_string: 典型格式字符串，例如 "PO-???-{ref:04d}"

    Returns:
        str: 正则表达式模式，例如 ^PO\-...\-(?P<ref>.*)$

    Raises:
        ValueError: 格式字符串无效
    """
```
注意：`r` 前缀保留，正则内容 `^PO\-...\-(?P<ref>.*)$` 和格式字符串 `"PO-???-{ref:04d}"` 不动。

### 示例 4：Django Model Meta 文档字符串
原文：
```python
class Meta:
    """Metaclass options for this mixin.

    Note: abstract must be true, as this is only a mixin, not a separate table
    """
    abstract = True
```
译文：
```python
class Meta:
    """此混入类的元类选项。

    注意：abstract 必须为 True，因为这只是混入类，而非独立表
    """
    abstract = True
```
注意：`class Meta:` 和 `abstract = True` 不动。

### 示例 5：行内注释
原文：
```python
# Ignore blank units
if not unit:
    return
```
译文：
```python
# 忽略空单位
if not unit:
    return
```

## 6. 常见陷阱

| 陷阱 | 错误做法 | 正确做法 |
|------|----------|----------|
| 翻译 gettext_lazy 字符串 | `_('Invalid physical unit')` → `_('无效物理单位')` | **不翻译**，`_()` 内字符串由 Django i18n 处理 |
| 翻译 verbose_name/help_text | `verbose_name=_('Name')` → `verbose_name=_('名称')` | **不翻译**，同上 |
| 破坏 r""" 前缀 | `r"""pattern"""` → `"""pattern"""` | **保留 `r` 前缀** |
| 翻译正则示例 | `^PO\-...\-(?P<ref>.*)$` → 翻译其中的 `?P` | **不翻译**，正则原样保留 |
| 翻译 @param 标签 | `@param name` → `@参数 name` | **保留 `@param`**，只翻译后面的说明 |
| 翻译代码行中的类名 | `class FilterableSerializerMixin` → `class 可过滤序列化器混入` | **不翻译**，代码标识符不动 |
| 翻译导入语句 | `from django.db import models` → `从 django.db 导入 模型` | **不翻译** |
| 修改 `# pragma: no cover` | 当作普通注释翻译 | **提取阶段已过滤** |
| 把 `"""` 放到代码同一行 | 重建时改变 inline docstring 的原始格式 | 多行 docstring 统一用 `"""` 独占一行的格式 |
