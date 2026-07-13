---
name: annual-report
description: A股年报/定期报告PDF下载。数据源：巨潮资讯。支持年报、半年报、一季报、三季报。支持按年份、报告类型筛选查询。不指定年份时默认使用当前年份。保存位置：年报PDF/<股票名称>/。命名规范：{股票名称}_{股票代码}_{年份}{报告类型}.pdf
---

# annual-report — A股年报/定期报告PDF下载

## 数据源
- 巨潮资讯（cninfo.com.cn）
- PDF 存储：static.cninfo.com.cn

## 功能范围
下载 A 股上市公司定期报告 PDF：年报、半年报、一季报、三季报。

## 工作流程（4步）

### 第一步：查询报告列表
先让用户选择要下载哪份报告，不要直接下载。

```bash
python3 /Users/zhou/.hermes/skills/annual-report/scripts/list_reports.py <股票代码> [关键词] [年份]
```

示例：
```bash
python3 list_reports.py 300750                  # 查全部（不限年份，最新公布在前）
python3 list_reports.py 300750 年度报告 2025   # 查2025年年报
python3 list_reports.py 300750 一季报           # 查最新公布的一季报
```

### 第二步：下载 PDF
下载到临时位置，再移动到目标目录。

```bash
python3 /Users/zhou/.hermes/skills/annual-report/scripts/download_report.py <股票代码> <报告类型> [年份] [保存目录]
```

示例：
```bash
# 不指定年份，下载最新公布的一季报（不限年份，按公告时间倒序取最新）
python3 download_report.py 300750 一季报

# 指定年份下载年报
python3 download_report.py 300750 年报 2025 "/Users/zhou/Desktop/投研分析/年报PDF/宁德时代/"
```

报告类型支持：年报、半年报、一季报、三季报（或完整名称：年度报告、半年度报告等）。

### 第三步：重命名文件
**归档前必须统一重命名**为标准格式：

```
{股票名称}_{股票代码}_{年份}{报告类型}.pdf
```

| 报告类型 | 命名示例 |
|----------|----------|
| 年度报告 | 宁德时代_300750_2025年年度报告.pdf |
| 半年度报告 | 宁德时代_300750_2025年半年度报告.pdf |
| 一季度报告 | 宁德时代_300750_2025年一季度报告.pdf |
| 三季度报告 | 宁德时代_300750_2025年三季度报告.pdf |

### 第四步：归档到公司子文件夹
**严禁将文件直接放在 `年报PDF/` 根目录下**，必须按公司名称建子文件夹：

```bash
mkdir -p "/Users/zhou/Desktop/投研分析/年报PDF/<股票名称>/"
mv "/tmp/<标准文件名>.pdf" "/Users/zhou/Desktop/投研分析/年报PDF/<股票名称>/"
```

## 批量下载规则
- 不指定年份时：按公告时间倒序取最新公布的一份（不限年份）
- 下载任何季报/半年报时：自动连带下载最新的一份年报（本地已有且大小一致则跳过）
- 年报：业务分析底本（最近一个完整财年）
- 一季报：最新财务数据（4月发布）
- 半年报/三季报：按需补充
- 目标已存在时先比较大小（阈值1KB），大小一致则跳过

## 文件命名规范（必须严格执行）

标准格式：`{股票名称}_{股票代码}_{年份}{报告类型}.pdf`

| 报告类型 | 命名示例 |
|----------|----------|
| 年度报告 | `宁德时代_300750_2025年年度报告.pdf` |
| 半年度报告 | `..._2025年半年度报告.pdf` |
| 一季度报告 | `..._2025年一季度报告.pdf` |
| 三季度报告 | `..._2025年三季度报告.pdf` |

规则：
- 年份从报告标题中提取（标题格式通常为"xxx公司2025年年度报告"）
- 报告类型使用完整中文名称（年度报告/半年度报告/一季度报告/三季度报告）
- 文件扩展名统一为小写 `.pdf`
- 原始下载文件名（如 `格林美_002340_1225142250.PDF`）无意义，**必须在归档前统一重命名**

## 文件归档流程（必须严格执行）

1. **先下载到临时位置**：使用 `download_report.py` 时不指定保存目录或指定为 `/tmp/`
2. **创建公司文件夹**：
   ```bash
   mkdir -p "/Users/zhou/Desktop/投研分析/年报PDF/<股票名称>"
   ```
3. **重命名文件**：按命名规范，在临时位置将文件重命名为标准格式
   ```bash
   mv "/tmp/<原始文件名>" "/tmp/<股票名称>_<股票代码>_<年份><报告类型>.pdf"
   ```
4. **移动文件到公司文件夹**：
   ```bash
   mv "/tmp/<标准文件名>" "/Users/zhou/桌面/投研分析/年报PDF/<股票名称>/"
   ```

## 交互规范
- 先展示列表让用户选择，不要直接下载
- 支持按年份、报告类型筛选
- 下载后告知文件路径和页数
- 默认保存路径：`/Users/zhou/Desktop/投研分析/年报PDF/<股票名称>/`

## 已知踩坑（必读）

### 1. 高亮标签破坏关键词匹配
巨潮资讯返回的公告标题带 `<em>` 高亮标签（如 `2026年<em>一季度</em><em>报告</em>`），直接 `str.contains("一季度报告")` 会匹配失败。**脚本已自动去标签**，但如手动拼接查询需注意。

### 2. 年报搜索范围必须跨年度
年报在次年3-4月发布，标题是"2025年年度报告"但发布时间在2026年。如果搜索范围只限定 `2025-01-01~2025-12-31` 会漏掉。**脚本已将搜索范围自动扩展为 `{year}-01-01~{year+1}-12-31`**。

### 3. "年度报告"关键词会混入"半年度报告"
`年度报告` 是 `半年度报告` 的子串，搜索时必须排除包含"半年度"的结果。**脚本已做精确过滤**。

### 4. 英文版公告时间更晚、会排在中文版前面
巨潮资讯对同一份报告可能同时发布中文版和英文版，英文版公告时间更晚，会排在列表前面。
**修复**：`_query_reports` 已过滤含"英文版"的标题，优先取中文正文。

### 5. orgId 获取已改为 topSearch 接口
`akshare.stock_fundamental.stock_notice.__get_stock_json` 是私有函数，版本升级可能失效。
**修复**：两个脚本均已改为直接调用巨潮 `topSearch/query` 接口获取 orgId，不再依赖 akshare 私有函数。

### 6. 标题中公司名提取不稳定
公告标题可能是"宁德时代2025年年度报告"，也可能是"2025年年度报告"（无公司名前缀）。脚本优先从 orgId 反向映射获取，失败时 fallback 到 `stock_profile_cninfo`，最后兜底用股票代码。

### 6. 同一简称可能对应多个股票代码（股票代码校验）
**现象**：用户已有报告目录中存在 `源杰科技_688147_2025年年度报告.pdf`，但巨潮 topSearch 按"源杰科技"查到的是 688498。  
**原因**：同一简称可能被重名使用、或用户记错代码、或上市公司更名/迁址导致代码变化。  
**修复**：下载前先用 topSearch 按股票代码查 orgId，再与用户本地已有文件名中的代码做比对。如果发现不一致，**暂停下载并向用户确认正确代码**，避免研报数据错配。  
示例代码：
```python
import requests, os
# 查 orgId
r = requests.post("http://www.cninfo.com.cn/new/information/topSearch/query",
    data={"keyWord": "<股票代码>", "maxNum": 5}, headers=HEADERS, timeout=20)
result = r.json()
cninfo_code = result[0]["code"]
cninfo_name = result[0]["zwjc"]
# 与用户本地已有文件交叉验证
existing_files = os.listdir(f"/Users/zhou/Desktop/投研分析/年报PDF/{cninfo_name}/")
for f in existing_files:
    if f.startswith(f"{cninfo_name}_") and not f.startswith(f"{cninfo_name}_{cninfo_code}_"):
        print(f"⚠️ 代码不一致！本地文件: {f}，巨潮查到: {cninfo_code}")
```

### 7. 下载大小校验过于严格
**现象**：所有报告都提示"大小异常"，差 1-2KB。  
**原因**：HTTP chunk 边界或重定向导致实际字节数与 header 中 `adjunctSize` 有微小差异。  
**修复**：将 `existing_size == size_kb * 1024` 改为 `abs(existing_size - size_kb * 1024) < 1024`。

## orgId 获取的可靠方法
akshare 私有函数 `__get_stock_json` 可能随版本升级失效。更稳定的方式是直接调用巨潮 `topSearch/query` 接口：
```python
url = "http://www.cninfo.com.cn/new/information/topSearch/query"
payload = {"keyWord": "<股票代码>", "maxNum": 5}
r = requests.post(url, data=payload, headers=HEADERS, timeout=20)
# 返回值是 list，每个元素含 code / orgId / zwjc(简称)
result = r.json()
org_id = result[0]["orgId"]
stock_name = result[0]["zwjc"]
```
接口返回值是 `list`，不要用 `.get()`。topSearch 覆盖沪深京 A 股主要标的。

## 批量下载流程
用户明确要求批量时，可直接批量查询 + 下载，不必每只股票先展示列表再询问。
流程：
1. 用 topSearch 批量解析所有股票的 `orgId` + 简称
2. 按报告类型/年份查询，取最新一份正文（排除摘要）
3. 创建 `<股票名称>/` 子文件夹，统一命名归档
4. 大小校验阈值建议 **1KB**（字节级差异属于正常网络抖动，不应误判为失败）
5. **股票代码校验**：下载前检查巨潮返回的代码与用户本地已有文件中的代码是否一致，不一致则暂停并请用户确认

## 注意事项
- `download_report.py` 的 `[保存目录]` 参数是最终存放位置，如果传入根目录 `年报PDF/`，文件会直接落在那里。因此**必须按上述流程操作**，确保文件重命名后再进入 `<股票名称>/` 子文件夹
- 报告中可能同时存在"年报正文"和"年报摘要"，下载时自动过滤摘要，只保留正文
- 巨潮资讯接口未找到报告时可能因为股票代码对应的 orgId 未收录，见脚本注释中的 fallback 映射
- **`__get_stock_json` 已废弃**：优先改用 topSearch 接口，或维护本地 fallback 映射
- 批量场景应加 `time.sleep(0.3)` 避免对巨潮接口造成压力
- 批量场景应加 `time.sleep(0.3)` 避免对巨潮接口造成压力
