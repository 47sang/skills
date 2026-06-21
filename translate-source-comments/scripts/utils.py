#!/usr/bin/env python3
"""
共享工具函数，供 extract_comments.py 和 apply_translations.py 共同使用。
"""

import re

# 中文字符检测：基本区 + 扩展 A 区 + 全角标点/符号
HAS_CHINESE = re.compile(r"[㐀-鿿　-〿＀-￯]")


def has_chinese(text: str) -> bool:
    """检测文本中是否包含中文字符。"""
    return bool(HAS_CHINESE.search(text))


def find_inline_comment_pos(line: str) -> int:
    """
    返回 // 在字符串字面量之外的位置，找不到返回 -1。
    正确处理：
    - 普通双引号字符串 "..."（含转义 \"）
    - 单引号字符字面量 'x'
    - Java 17 文本块 (三个双引号起止)
    """
    in_str = False
    str_char = None
    in_text_block = False
    text_block_starter = 0  # 记录 """ 开始位置

    i = 0
    while i < len(line):
        ch = line[i]

        # ---- 文本块检测（必须在引号检测之前）----
        if not in_str and ch == '"' and i + 2 < len(line) and line[i:i + 3] == '"""':
            if in_text_block:
                # 结束文本块，跳到 """ 之后
                in_text_block = False
                i += 3
                continue
            else:
                # 进入文本块
                in_text_block = True
                i += 3
                continue

        if in_text_block:
            i += 1
            continue

        # ---- 普通引号字符串/字符字面量 ----
        if ch in ('"', "'") and (i == 0 or line[i - 1] != "\\"):
            if not in_str:
                in_str = True
                str_char = ch
            elif str_char == ch:
                in_str = False
                str_char = None

        # ---- 行内注释 ----
        elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/" and not in_str:
            return i

        i += 1
    return -1


def is_license_line(line: str, idx: int) -> bool:
    """判断某一行是否属于文件顶部的 License 头部（前 20 行内）。"""
    if idx >= 20:
        return False
    s = line.strip()
    # 匹配 /* 块注释开始行（带或不带前导空格）
    if s.startswith("/*"):
        return True
    # 匹配 * 开头的块注释内容行（带或不带前导空格，如 " *" 或 "*"）
    if s.startswith("*"):
        return True
    # Apache-2.0 标准声明特征
    markers = (
        "Copyright",
        "Licensed under the Apache License",
        "http://www.apache.org/licenses",
        "https://www.apache.org/licenses",
        "limitations under the License",
        "distributed under the License",
    )
    return any(m in s for m in markers)


# Javadoc 标签 / HTML 标记（提取和校验时用）
JAVADOC_TAGS = re.compile(
    r'@(?:param|return|throws|exception|see|since|deprecated|serial|author)\b'
)
INLINE_TAGS = re.compile(
    r'\{@(?:code|link|linkplain|inheritDoc|value)\b'
)
HTML_TAGS = re.compile(r'</?(?:p|pre|code|ul|ol|li|b|i|em|strong)>')
