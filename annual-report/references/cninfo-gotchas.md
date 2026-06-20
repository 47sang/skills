# 巨潮资讯接口踩坑记录

## 坑1：年报关键词搜索会混入半年报
- **现象**：搜索"年度报告"时，结果里同时出现"2025年半年度报告"
- **原因**：`年度报告` 是 `半年度报告` 的子串
- **修复**：过滤时用 `年度报告` AND NOT `半年度`

## 坑2：高亮标签破坏关键词匹配
- **现象**：搜索"一季度报告"返回 0 条，但接口明明有数据
- **原因**：巨潮资讯返回的标题带 `<em>` 高亮标签，如 `2026年<em>一季度</em><em>报告</em>`，导致 `str.contains("一季度报告")` 匹配失败
- **修复**：先 `str.replace("<em>", "").replace("</em>", "")` 去掉标签，再过滤

## 坑3：年报年份搜索范围必须跨年度
- **现象**：`list_reports.py 300750 年报 2025` 找不到 2025 年报
- **原因**：年报在次年3-4月发布，标题是"2025年年度报告"但发布时间是2026年。如果搜索范围只限定 `2025-01-01~2025-12-31` 就会漏掉
- **修复**：年份参数对应的搜索范围改为 `{year}-01-01~{year+1}-12-31`

## 坑4：orgId 获取 — 已弃用 akshare，改用 topSearch
- **旧方案**：`akshare.stock_fundamental.stock_notice.__get_stock_json` 是私有函数，版本升级可能失效
- **当前方案**：直接调用 `http://www.cninfo.com.cn/new/information/topSearch/query`，传股票代码，取 `result[0]["orgId"]`
- **注意**：返回值是 `list`，不要用 `.get()`；按 `code` 字段精确匹配

## 坑5：英文版公告时间更晚、会排在中文版前面
- **现象**：同一份报告同时发布中文版和英文版，英文版公告时间更晚，会排在列表前面导致脚本误选英文版
- **修复**：`_query_reports` 中过滤含"英文版"的标题，优先取中文正文

## 坑6：空日期字符串导致 announcements 列表为空
- **现象**：`seDate=""` 传给接口时，`totalAnnouncement` 有值但 `announcements` 为空列表
- **修复**：不限年份时改用极宽范围 `2000-01-01~2099-12-31` 覆盖全部历史

## 坑7：标题中公司名提取不稳定
- **现象**：公告标题可能是"宁德时代2025年年度报告"，也可能是"2025年年度报告"（无公司名前缀）
- **修复**：优先从 topSearch 返回的 `zwjc` 字段获取简称，失败时从公告标题正则提取，兜底用股票代码

## 已知接口验证（2026-06-16）
- `stock_zh_a_disclosure_relation_cninfo` — 可用，查公告列表
- `stock_profile_cninfo` — 可用，公司基本信息
- `stock_zh_a_spot_em` — 可用，实时行情
- `stock_profit_sheet_by_report_em` / `stock_balance_sheet_by_report_em` / `stock_cash_flow_sheet_by_report_em` — 当前版本报错 `NoneType object is not subscriptable`，待排查
