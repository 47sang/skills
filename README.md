# Skills 技能库

本仓库是一组可被 Claude Code 自动加载与调用的技能集合。每个技能是一个独立目录，内含一份 `SKILL.md`（YAML 前置元数据 + Markdown 正文），说明「做什么、何时用、怎么做」。

当前共收录 **40** 个技能，按功能归为以下 11 组。进入项目时可直接对照下表定位；点击技能名可跳转到对应的 `SKILL.md`。使用时无需手动指定——在对话中说出对应意图（如「帮我评审这个 PR」「分析一下这个开源项目」），相关技能会被自动触发。

**最近更新**：2026-10-27

## 目录

- [📚 学习与知识沉淀](#-学习与知识沉淀)
- [📐 规格驱动开发](#-规格驱动开发)
- [🤝 PR 评审与协作](#-pr-评审与协作)
- [🛠️ 代码质量与修复](#️-代码质量与修复)
- [🎨 前端与动效](#-前端与动效)
- [🔀 Git 操作](#-git-操作)
- [🌐 注释翻译](#-注释翻译)
- [🖥️ 远程运维](#️-远程运维)
- [☁️ Cloudflare 平台](#️-cloudflare-平台)
- [🎬 豆包多模态生成](#-豆包多模态生成)
- [⚙️ 技能维护](#️-技能维护)

---

## 📚 学习与知识沉淀

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [deep-learn-codebase](deep-learn-codebase/SKILL.md) | 深度学习任意代码库，产出「一篇一主题」教学文档 + 嵌入式刻意练习（缺陷预演 / 决策复盘） | 想系统学习或分析一个开源项目 / 框架，提炼优秀架构 |
| [distill-essence](distill-essence/SKILL.md) | 从新事物中萃取可复用的精华，沉淀为可被人工智能（AI）检索的「第二大脑」条目，并做元认知自检 | 想快速搞懂一个新东西、提炼能复用的抓手，但没时间逐行读源码 |
| [blind-spot-scan](blind-spot-scan/SKILL.md) | 动手实现前主动扫描「未知的未知」与「未知的已知」，防止实施阶段才发现代价高昂的遗漏 | 启动新模块实现、写完规格文档后，或用户提到「盲区」 |
| [knowledge-distill](knowledge-distill/SKILL.md) | 从当前项目蒸馏结构化知识（项目概览 / 技术决策 / 踩坑记录 / 模块规范 / 通用模式 / 反模式），写入本地知识库并同步双索引 | 想沉淀项目知识、记录踩坑、归档技术决策 |
| [knowledge-maintain](knowledge-maintain/SKILL.md) | 对本地知识库执行三类校准（一致性 / 时效性 / 覆盖度），输出结构化健康报告 | 校验知识库质量、检查双索引一致性、清理过期条目 |
| [knowledge-router](knowledge-router/SKILL.md) | 根据当前工作目录自动识别项目，从知识库按任务类型加载对应的项目知识文件 | 会话启动时由钩子自动触发，或开发新功能、排查故障、代码评审前手动运行 |

## 📐 规格驱动开发

一条「先捕获意图、再写规格、最后写代码」的产物链工作流：用 `capture-intent` 快速记录原始想法，用 `write-product-spec` / `write-tech-spec` 产出 `PRODUCT.md` / `TECH.md`，用 `implement-specs` 落地实现，`spec-driven-implementation` 负责整体编排与保持规格同步。

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [capture-intent](capture-intent/SKILL.md) | 快速捕获功能意图，在 `specs/NN-xxx/` 下创建 `intent.md` | 用户描述新功能或改进想法时，产物链的起点 |
| [spec-driven-implementation](spec-driven-implementation/SKILL.md) | 驱动规格优先工作流，让 `PRODUCT.md` / `TECH.md` 随实现演进并签入源码 | 启动重要功能、规划智能体（agent）驱动的开发 |
| [write-product-spec](write-product-spec/SKILL.md) | 编写 `PRODUCT.md`，从用户视角描述功能行为与验证条件 | 定义产品功能、编写产品需求文档（PRD） |
| [write-tech-spec](write-tech-spec/SKILL.md) | 编写 `TECH.md`，把产品意图转化为贴合现有代码库的实现计划 | 做技术实现计划、架构设计 |
| [implement-specs](implement-specs/SKILL.md) | 按已批准的规格实现功能，并保持规格与代码在同一次提交中同步 | 产品 / 技术规格批准后，开始构建功能 |

## 🤝 PR 评审与协作

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [review-pr](review-pr/SKILL.md) | 评审拉取请求（PR）的差异，输出结构化 `review.json` 供工作流发布 | 评审已签出的本地 PR（基于 `pr_diff.txt` 等产物） |
| [create-pr](create-pr/SKILL.md) | 为当前分支创建拉取请求，含合并主干、运行预提交检查、关联工单 | 提交代码评审、准备合并 |
| [diagnose-ci-failures](diagnose-ci-failures/SKILL.md) | 用 GitHub CLI 诊断 PR 的持续集成（CI）失败，提取日志并生成修复计划 | 检查 CI 状态、排查构建或测试失败 |
| [requesting-code-review](requesting-code-review/SKILL.md) | 完成开发后请求代码评审，评审当前分支相对基线的改动 | 完成重要功能、合入前确认工作质量 |
| [receiving-code-review](receiving-code-review/SKILL.md) | 以技术严谨性对待评审意见——先验证再实现，拒绝表演性认同与盲目照搬 | 收到代码评审反馈、准备落实修改建议时 |
| [review-and-iterate](review-and-iterate/SKILL.md) | 对当前分支变更做三路并发审查（规范合规 / 人工智能编码陷阱 / 工程规范），自动修复问题并多轮迭代 | 按规格实现完成后、合并前 |

## 🛠️ 代码质量与修复

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [fix-errors](fix-errors/SKILL.md) | 修复编译错误、代码检查（lint）告警、格式违规与测试失败（覆盖 rustc / clippy / fmt） | 遇到构建、代码检查或测试失败，或提交前需通过预检查 |
| [rust-unit-tests](rust-unit-tests/SKILL.md) | 编写、改进并运行 Rust 单元测试（crate 级、异步、特性开关场景） | 补充或完善 Rust 测试、设定测试规范 |

## 🎨 前端与动效

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [motion-craft](motion-craft/SKILL.md) | 实现「高级、自然、克制」的 Web 动效系统：分层架构、时长缓动常量表、微交互、共享元素变形、Canvas 物理动画，附可直接拷走的框架无关核心实现与可执行反模式扫描脚本 | 新增或审查页面切换、浮层开合、悬停按压、图表生长、Canvas 常驻动画，或排查卡顿抖动与减弱动态效果问题 |
| [answer-me-with-html](answer-me-with-html/SKILL.md) | 把回答变成一页可视化 HTML 讲解页：模型写简短 Markdown 草稿，命令行工具构建单页 | 原理讲解、架构说明、方案对比、问题诊断——图形比纯文字更清楚时主动使用 |
| [web-perf](web-perf/SKILL.md) | 用 Chrome DevTools 测量 Web 性能：核心网页指标（LCP / INP / CLS）与辅助指标（FCP / TBT / 速度指数），定位渲染阻塞链与布局抖动源 | 审计性能、解读 Lighthouse 结果、优化页面加载速度 |

## 🔀 Git 操作

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [git-worktree-parallel](git-worktree-parallel/SKILL.md) | 用 Git worktree 隔离工作目录进行多分支并行开发，覆盖创建 / 合并 / 清理全流程与常见陷阱 | 多分支并行推进、子代理互不踩踏工作区、紧急修复不打断当前开发 |
| [resolve-merge-conflicts](resolve-merge-conflicts/SKILL.md) | 只提取未解决路径与冲突摘要，在尽量不展开完整文件的前提下解决冲突 | 合并、变基、拣选（cherry-pick）、储藏恢复等操作卡在冲突时 |

## 🌐 注释翻译

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [translate-source-comments](translate-source-comments/SKILL.md) | 将 Java（及 YAML）源码中的英文 Javadoc 与行内注释翻译为中文，保留代码、正则与字面量不动 | 整个项目或部分源文件的注释汉化 |
| [translate-py-comments](translate-py-comments/SKILL.md) | 将 Python 源码中的英文文档字符串与行内注释翻译为中文，只动注释文字、绝不碰代码 | 整个项目或部分 Python 源文件的注释汉化 |

## 🖥️ 远程运维

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [remote-ops](remote-ops/SKILL.md) | 连接 4 台远程服务器（医院内网 / 家用网关 / 测试服务器 / 公网入口），支持日志排查、Nginx 配置管理与验证、Docker 容器管理、项目部署 | 查看远程服务器日志、修改 Nginx 端口转发配置、重启服务或排查部署问题 |

## ☁️ Cloudflare 平台

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [cloudflare](cloudflare/SKILL.md) | Cloudflare 平台全景：Workers、Pages、存储（KV / D1 / R2）、人工智能（Workers AI / Vectorize / Agents SDK）、功能开关、网络（Tunnel / Spectrum）、WAF 与基础设施即代码（Terraform） | 任何 Cloudflare 产品选型、架构与开发问题 |
| [cloudflare-email-service](cloudflare-email-service/SKILL.md) | 用 Cloudflare Email Service 收发交易邮件（Email Sending + Email Routing），含 SPF / DKIM / DMARC 配置与代码示例 | 搭建邮件发送与路由、验证发件人域名、排查送达率 |
| [cloudflare-one](cloudflare-one/SKILL.md) | Cloudflare One 零信任与 SASE：Access、Gateway、WARP、Tunnel、Spectrum、WAN、DLP、CASB、设备姿态与基础设施即代码，优先检索最新文档 | 部署零信任接入、配置安全网关与数据防泄漏 |
| [cloudflare-one-migrations](cloudflare-one-migrations/SKILL.md) | 规划从 Zscaler ZIA / ZPA、Palo Alto、旧版 VPN / SWG 栈迁移到 Cloudflare One | 评估与执行安全栈迁移 |
| [workers-best-practices](workers-best-practices/SKILL.md) | 按生产最佳实践编写与评审 Cloudflare Workers 代码，含必须遵守的硬性规则 | 编写或评审 Workers 代码、部署前、性能调优 |
| [wrangler](wrangler/SKILL.md) | Cloudflare Workers 命令行工具：部署、开发、测试 Workers、Pages Functions、R2、D1、KV、Queues、Workflows、Containers、Hyperdrive、Vectorize | 执行 wrangler 命令、调试部署、配置 wrangler 配置文件 |
| [durable-objects](durable-objects/SKILL.md) | 创建与评审 Cloudflare Durable Objects：强一致性的有状态协调（聊天室、游戏状态、限流），含休眠、告警、SQLite 存储与 RPC | 构建有状态实时协调、使用 DO / 休眠 / 告警 / RPC 接口时 |
| [sandbox-sdk](sandbox-sdk/SKILL.md) | 用 Sandbox SDK 构建安全代码执行应用：容器生命周期、命令执行、代码解释器、隔离的智能体运行时与预览链接 | 执行不可信代码、构建代码解释器或沙箱预览 |
| [agents-sdk](agents-sdk/SKILL.md) | 在 Cloudflare Workers 上用 Agents SDK 构建人工智能智能体：有状态智能体、持久工作流、实时 WebSocket 应用、定时任务、MCP 服务器、聊天与语音应用 | 开发上述任一场景，优先检索 Cloudflare 文档而非依赖预训练记忆 |
| [turnstile-spin](turnstile-spin/SKILL.md) | 端到端落地 Cloudflare Turnstile：扫描代码库、经 API 创建小部件、部署受管校验 Worker、写前端片段并验证 | 给表单或页面加人机验证、防机器人刷量 |

## 🎬 豆包多模态生成

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [byted-ark-seedance-skill](byted-ark-seedance-skill/SKILL.md) | 豆包 Seedance 人工智能视频生成（火山方舟 Agent Plan 专属版）：智能模型路由、图生视频、首尾帧控制 | 用户意图为生成视频时优先评估 |
| [byted-ark-seedream-skill](byted-ark-seedream-skill/SKILL.md) | 豆包 Seedream 人工智能图片生成（火山方舟 Agent Plan 专属版）：连贯组图、流式输出、提示词优化、联网搜索 | 用户说「生图 / 画图」或发参考图时；视频生成请用 Seedance |

## ⚙️ 技能维护

| 技能 | 主要功能 | 何时使用 |
|---|---|---|
| [update-skill](update-skill/SKILL.md) | 创建或更新本仓库的 `SKILL.md`（目录结构、前置元数据、正文规范） | 新增技能，或修订现有技能的结构与说明 |

---

> 📦 **已迁出的技能**：`tushare-news`（财经快讯晨报）与 `buy-checklist`（买入前检查清单）原属本仓库的「投研数据采集」分组，现已迁移至投研分析项目的 `.claude/skills/` 目录，由该项目自动加载，不再随本仓库版本控制。

> 💡 想新增或修改技能？参考 [update-skill](update-skill/SKILL.md) 中的结构与最佳实践。

## 更新记录

| 版本 | 更新日期 | 本次变更 | 触发原因 |
|---|---|---|---|
| v1.0 | — | 初版收录 18 个技能 | — |
| v1.1 | 2026-10-27 | 技能总数 18 → 40（实测 `ls` 目录数）；补录 23 个此前未收录的技能，新增「Cloudflare 平台」「豆包多模态生成」两组；`annual-report` 已迁至投研分析项目，从本仓库移除条目；「投研数据采集」分组整体改为「已迁出的技能」说明，消除指向仓库外的死链 | 索引与磁盘脱节（README 记 18 个、实际 40 个目录），按索引一致性纪律修正 |
