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
python3 /Users/zhou/.claude/skills/annual-report/scripts/list_reports.py <股票代码> [关键词] [年份]
```

示例：
```bash
python3 list_reports.py 300750                  # 查全部（不限年份，最新公布在前）
python3 list_reports.py 300750 年度报告 2025   # 查2025年年报
python3 list_reports.py 300750 一季报           # 查最新公布的一季报
```

### 第二步：下载 PDF
脚本已内置标准命名，直接下到目标公司目录即可，无需手动重命名。

```bash
python3 /Users/zhou/.claude/skills/annual-report/scripts/download_report.py <股票代码> <报告类型> [年份] [保存目录]
```

示例：
```bash
# 不指定年份，下载最新公布的一季报（不限年份，按公告时间倒序取最新）
python3 download_report.py 300750 一季报

# 指定年份下载年报
python3 download_report.py 300750 年报 2025 "/Users/zhou/Desktop/投研分析/年报PDF/宁德时代/"

# 公司已更名时，用 --name 指定本地沿用的旧名（巨潮简称不同时会提示）
python3 download_report.py 300223 半年报 2026 "/path/君正股份/" --name 君正股份
```

报告类型支持：年报、半年报、一季报、三季报（或完整名称：年度报告、半年度报告等）。

常用可选参数：
- `--name 简称`：公司改名后，沿用本地既有目录名归档
- `--force`：文件已存在时强制重新下载（默认跳过已存在文件）
- `--no-verify`：跳过 PDF 首页标题校验（不推荐）

### 批量下载（一份清单覆盖多家公司）

```bash
python3 download_report.py --batch <清单.json> --base-dir <父目录> [选项]
```

清单为 JSON 数组，支持两种写法（`name` 可省略，脚本会自动用巨潮官方简称补齐）：

```json
[{"name": "宁德时代", "symbol": "300750"},
 {"name": "中芯国际", "symbol": "688981"}]
```

或纯代码数组：`["300750", "688981"]`

常用选项：

| 选项 | 说明 |
|------|------|
| `--base-dir` | **必填**。每家公司在该目录下自动建子文件夹，如 `/Users/zhou/Desktop/投研分析/年报PDF` |
| `--types` | 报告类型，逗号分隔，默认 `年报,一季报`；支持 `年报,半年报,一季报,三季报` |
| `--year` | 目标报告年份；不填则查「当年 + 去年」两轮，适配跨年补数据 |
| `--check-only` | **只检查不下载**，用于盘点哪些公司缺哪些报告 |
| `--force` | 已存在也重新下载 |
| `--report <文件>` | 把逐条结果写成 JSON，便于二次处理 |
| `--interval` | 每份之间的间隔秒数，默认 0.35 |

典型用法：
```bash
# 1) 先盘点：全库缺哪些报告，一眼看清
python3 download_report.py --batch 清单.json --base-dir "/Users/zhou/Desktop/投研分析/年报PDF" \
  --types 年报,一季报,半年报 --check-only

# 2) 再补齐：只下载缺失的（已存在的自动跳过，可反复安全执行）
python3 download_report.py --batch 清单.json --base-dir "/Users/zhou/Desktop/投研分析/年报PDF" \
  --types 年报,一季报 --year 2025 --report /tmp/下载明细.json
```

**批量模式的两个保障**：① 每份 PDF 下载后都用 `pdftotext` 校验首页标题，校验不通过会自动删除错文件并换下一个候选，最多试 3 个；② 公司简称与巨潮不一致时按清单里的本地名归档，并在进度行提示现用简称，不会改写你的目录结构。

### 第四步：归档到公司子文件夹
**严禁将文件直接放在 `年报PDF/` 根目录下**，必须按公司名称建子文件夹：

```bash
mkdir -p "/Users/zhou/Desktop/投研分析/年报PDF/<股票名称>/"
mv "/tmp/<标准文件名>.pdf" "/Users/zhou/Desktop/投研分析/年报PDF/<股票名称>/"
```

## 批量下载规则
- `--year` 不指定时批量查「当年 + 去年」两轮；单只模式不指定年份时，年报取最新一期的实际年份，季报取当前年份
- 目标文件已存在时默认跳过（不再按文件大小比较——同名同源文件大小本就一致，跨期报告会因年份不同而不同名）
- 每份 PDF 下载后强制用 `pdftotext` 校验首页标题；校验不通过自动删除并换下一个候选，最多试 3 个
- `--check-only` 只盘点不下载，是补数据前的第一步

## 文件命名规范（脚本已自动处理）

标准格式：`{公司名称}_{股票代码}_{年份}{报告类型}.pdf`

| 报告类型 | 命名示例 |
|----------|----------|
| 年度报告 | `宁德时代_300750_2025年年度报告.pdf` |
| 半年度报告 | `..._2025年半年度报告.pdf` |
| 一季度报告 | `..._2025年一季度报告.pdf` |
| 三季度报告 | `..._2025年三季度报告.pdf` |

规则：
- 公司名称取自巨潮 topSearch 的官方简称；本地沿用旧名（如公司改名后）用 `--name` 覆盖
- 年份从公告标题中提取，不从文件下载时间推断
- 报告类型使用完整中文名称
- 文件扩展名统一为小写 `.pdf`
- **不需要**「先下到 /tmp 再手动 mv」——直接传目标公司目录即可，脚本内部已处理

## 交互规范
- 单只下载：先展示列表让用户选择，不要直接下载
- 批量下载：用户明确要求批量时直接执行，不必逐只询问
- 下载后告知文件路径和页数
- 默认保存路径：`/Users/zhou/Desktop/投研分析/年报PDF/<公司名称>/`

## 已知踩坑（必读）

### 1. 高亮标签破坏关键词匹配
巨潮资讯返回的公告标题带 `<em>` 高亮标签（如 `2026年<em>一季度</em><em>报告</em>`），直接 `str.contains("一季度报告")` 会匹配失败。**脚本已自动去标签**（`cninfo_common.clean_title`）。

### 2. 年报搜索范围必须跨年度
年报在次年 3-4 月发布，标题是「2025 年年度报告」但发布时间在 2026 年。**脚本已把检索区间设为 `{year}-12-01 ~ {year+1}-12-31`**。

### 3.「年度报告」关键词会混入「半年度报告」
`年度报告` 是 `半年度报告` 的子串，且 `<em>` 标签会把「半年度」与「报告」打断导致子串匹配失效。**脚本已先去标签再做双向排除**。

### 4. 英文版公告时间更晚、会排在中文版前面
**脚本已过滤含「英文版」「英文」的标题**，优先取中文正文。

### 5. 港股与 A 股双重上市公司会挂出「港股公告：XXXX年报」
中芯国际（688981）等 A+H 公司在巨潮同时挂港股年报，且港股版**常是无文字层的扫描版、体积大 25 倍**。旧脚本按「最新一份」选取会直接下到扫描版。
**修复**：`EXCLUDE_TOKENS` 已排除含「港股公告」「H股公告」「香港联合交易所」等字样的公告。

### 6. orgId 获取已改为 topSearch 接口
`akshare.stock_fundamental.stock_notice.__get_stock_json` 是私有函数，版本升级即失效。**两个脚本均已改为直接调用巨潮 `topSearch/query`**，同时取得官方简称（`zwjc`），不再依赖 akshare 反查。

### 7. column 参数写死 szse 会漏沪市/科创板
**已按代码前缀自动选择** `column`（688/689/600/601/603/605 → sse，4/8/92 开头 → bjse，其余 szse），并在首选板块返回 0 条时自动回落到另一板块重查。

### 8. 季报有「一季度报告」与「第一季度报告」两种官方写法
**两种写法都匹配**，只认前者会漏掉部分公司。

### 9. PDF 首页常在数字与「年」之间插空格
巨潮 PDF 首页常见「2026 年第一季度报告」，直接 `in` 匹配会误判。**校验前已用正则去除全部空白字符**。

### 10. 个别公司封面是中英双语设计版式
如中信证券（600030），「2026 年半年度报告」字样出现在第 5 页而非第 1 页。**校验读取前 3 页**以避免误杀。

### 11. 同一简称可能对应多个股票代码
下载前应先确认代码。以源杰科技为例，实际代码是 **688498**（688147 是科创板申报阶段用过的代码，未正式使用）。
**修复**：批量清单用 `symbol` 字段指定代码，`name` 仅作本地目录名；脚本会打印「巨潮现用简称」提示差异。
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

### 12. 首页文字层校验是最后一道防线，不可关闭
巨潮的摘要、提示性公告、港股扫描版都会通过标题过滤的绝大多数情况。**`fetch_report` 强制在落地前校验首页**，这是本 skill 与旧版最大的区别——旧版只看公告标题就写盘，错文件进了库没人发现，下游趋势分析报告直接引用了半年报数字。
系统若未安装 `pdftotext`（`brew install poppler`），脚本会降级为不校验并明确告警。

## orgId 获取的可靠方法
akshare 私有函数 `__get_stock_json` 可能随版本升级失效。**已统一改为直接调用巨潮 `topSearch/query` 接口**（`cninfo_common.get_org_info`）：
```python
url = "http://www.cninfo.com.cn/new/information/topSearch/query"
payload = {"keyWord": "<股票代码>", "maxNum": 5}
r = requests.post(url, data=payload, headers=HEADERS, timeout=20)
# 返回值是 list，不要用 .get()；含 code / orgId / zwjc(简称)
result = r.json()
org_id = result[0]["orgId"]
stock_name = result[0]["zwjc"]
```
接口返回值是 `list`。topSearch 覆盖沪深京 A 股主要标的。

## 脚本结构

| 文件 | 职责 |
|------|------|
| `cninfo_common.py` | 公共层：去标签、报告类型归一、板块判断、orgId 查询、候选过滤、下载、首页校验、批量任务编排 |
| `download_report.py` | 命令行入口：单只下载 + `--batch` 批量模式 |
| `list_reports.py` | 命令行入口：报告列表查询，与下载共用同一套过滤标准 |
| `read_pdf.py` | PDF 文本提取小工具 |

修改过滤规则时**只改 `cninfo_common.py` 一处**，两个脚本自动同步，不会再出现「列表显示年报、下载拿到半年报」的分裂。

## 批量下载流程
用户明确要求批量时，可直接执行，不必每只股票先展示列表再询问。推荐两步走：

1. **盘点**：`--check-only` 输出每家公司缺哪些报告，不下载、不报错
2. **补齐**：去掉 `--check-only` 实际下载，已存在的自动跳过，可反复安全执行

流程细节：
- 清单用 `symbol` 指定代码（唯一事实来源），`name` 仅作本地目录名，可省略
- 报告类型、年份由 `--types` / `--year` 控制；不填年份时查当年+去年两轮
- 进度行实时打印每家每份的状态标记：✅下载 ⏭已存在 ➖巨潮无 ⚠️校验失败 ❌异常
- 结果摘要中的异常明细会逐条列出公司名、代码、报告类型与失败原因
- 间隔 `--interval` 默认 0.35 秒，避免对巨潮接口造成压力

## 注意事项
- 单只模式的 `[保存目录]` 是最终存放位置。**传公司目录**（`年报PDF/宁德时代/`）即可，脚本自动建目录并按标准命名落盘
- 传父目录（`年报PDF/`）不会自动分文件夹，文件会散落在根目录——批量模式请用 `--base-dir`，它会为每家公司建子目录
- 报告中可能同时存在「年报正文」和「年报摘要」，已自动过滤摘要
- 巨潮未收录的代码（如尚未上市的公司）会报「无法获取 orgId」，批量模式下计入异常并继续，不中断整批
- 批量场景保留 `time.sleep(0.35)` 间隔

