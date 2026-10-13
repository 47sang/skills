---
name: motion-craft
description: 实现「高级、自然、克制」的 Web 动效系统——分层动效架构、时长与缓动常量表、微交互模式、共享元素变形、Canvas 物理动画与性能护栏，并附可直接拷走的框架无关核心实现、可执行的反模式扫描脚本，以及症状→根因诊断表。当需要新增或审查页面切换、浮层开合、悬停与按压反馈、图表生长、Canvas 常驻动画，或排查动效卡顿、抖动、不自然、违反 prefers-reduced-motion、后台标签页补间停在中途时使用。范本来自一个 Vue 3 + GSAP 后台管理脚手架的实测实现，技术要点可移植到任意前端栈。
---

# 动效工艺

把「炫酷」拆成可复用的手艺：每一段动效都要能说出口它属于哪种能量语态，说不出语态的就是装饰，不做。

**三条使用路径**：

| 你要做什么 | 看哪里 |
| --- | --- |
| 从零搭一套动效系统 | **`assets/motion-core.ts` 直接拷走**（框架无关、已过类型检查与冒烟测试）→ 按需读 `references/` 专题 |
| 给已有项目加/改动效 | 本文第二~五节按模式取用 → `references/` 对应专题 |
| 审查或排查动效问题 | 先跑 `scripts/motion-audit.sh` → `references/motion-audit.md` 的症状→根因诊断表 |

## 一、先过哲学关

| 语态 | 含义 | 典型载体 |
| --- | --- | --- |
| 🔋 蓄（Charge） | 输入、等待、可交互的暗示 | 悬停抬起、指针光、焦点环 |
| ⚡ 放（Discharge） | 开始工作、交付 | 按压反馈、涟漪、弹窗展开、浮条升起 |
| 🌊 导（Conduct） | 进行中、数据在流动 | 折线描绘、脉冲沿线、秒针推进、倒计时环 |
| 💎 结（Crystallize） | 落定、确认 | 群组按阅读序进场、开关注满、登录成功对勾 |
| 🛑 停摆（Halt） | 停止、恢复默认 | 退场、收回原行、骨架屏 |

> 📌 源码只在部分函数注释里标了语态（按压=放、退场=停摆、群组进场=结、折线与脉冲=导）。表中「典型载体」一列是把语态体系推广到全部动效的归类建议，用于新动效自查——不是源码里逐条写明的映射。

**三条铁律**

1. **动效必须有语义**。装饰性动效一律砍掉；宁少勿多。
2. **CSS 与 JS 分工明确，按元素划分而不是按属性一刀切**：`transform` / `opacity` 一旦交给 GSAP，就撤掉该元素的 CSS `transition`；**没被 GSAP 接管的元素**（读数条、开关旋钮、图谱连线与节点、Toast 牌堆槽位）仍可用 CSS 过渡 `transform` / `translate` / `opacity` / `stroke`。同一元素上两条通道绝不写同一个属性——这才是「hover 写 `y`、press 写 `scale` 能同时生效」的由来。CSS 侧凡有位移/旋转需求，优先用独立的 `translate` / `rotate` 属性，把 `transform` 整条通道让给 GSAP。
3. **常驻动画只动 `transform` / `opacity`**，不触发重排；需要连续补间的自定义属性必须用 `@property` 注册。颜色、背景、描边（`stroke` / `stroke-width`）允许 `.15`–`.3s` 的短补间，但不进常驻动画。

**「唯一入口」要靠依赖锁定，不靠约定**：`motion.ts` 末尾 `export { gsap }`，页面连裸 `gsap.set` 都从它导入。这样「不引第二个动效库」从代码规范变成模块依赖——换个项目照抄这行就行。

**两个减动效入口，别混用**：`prefersReducedMotion()` 只回答「用户要不要减少」；`motionSkipped()` 是「要减少 **或** 页面在后台」。需要「跳过就给终态」的地方用后者，只做主题/能力判断的地方用前者。本项目两个入口并存，新增代码优先 `motionSkipped()`。

## 二、分层架构

样式按固定顺序引入，每层只解决自己的问题，通用变化写进所属层，不用页面选择器覆盖整个控件库：

| 层 | 职责 | 动效相关内容 |
| --- | --- | --- |
| `tokens.css` | 颜色、圆角、阴影、字体、密度 | 缓动令牌 `--ease-premium`、`@property --fill`、`font-synthesis: none` |
| `base.css` | 重置、焦点环、颗粒层 | 全局 reduced-motion 降级 |
| `materials.css` | 玻璃配方、槽、阅读面 | 容器级指针光 `m-glow`、透明度降级 |
| `components.css` | 按钮、输入、表格、浮层 | 控件级过渡、牌堆、倒计时环、遮罩 3px 模糊 |
| `instruments.css` | 读数、图表、画布、矩阵 | 数字滚动、呼吸光环、Canvas 与 DOM 分工 |
| `layout.css` | 外壳、导航、页面 | 入场兜底隐藏、侧栏抽屉 |
| `pages.css` | 单页独有排布 | 页面级开场 |

**入场兜底隐藏**：GSAP 就位前，用 `:not(.is-entrance-ready)` 把待动元素设为 `opacity: 0`，避免以终态闪现；时间轴第一步再把类加上。

## 三、时长与缓动

缓动只保留五种，各自对应一种运动性格：

```ts
export const EASE = Object.freeze({
  reveal: 'expo.out',      // 显现：快出慢收，落点清晰
  glide:  'power4.out',    // 位移滑行：长距离、有重量
  exit:   'power2.in',     // 退场：加速离开，不拖泥带水
  swap:   'power2.inOut',  // 双向交接：来回对称
  settle: 'back.out(1.6)', // 落定确认：唯一允许的过冲
})
```

时长按交互类型分档，**进场约是退场的三倍**（用户需要看清来了什么，不需要看清它怎么走）：

```ts
export const DUR = Object.freeze({
  press: 0.14,      // 按压：最快，跟随手指
  release: 0.46,    // 回弹
  hoverIn: 0.34, hoverOut: 0.42,
  slide: 0.52,      // 玻璃滑块位移
  pageOut: 0.18, pageIn: 0.62,          // 页面切换
  overlayIn: 0.42, overlayOut: 0.2,     // 浮层开合
})
```

**规律**：`back.out` 只用于「状态确认」那一下，绝不用 `opacity` 脉冲代替；`stagger` 每级 0.025–0.08s，超过 0.1s 会让人觉得卡。

CSS 侧的过渡另有一条**按控件尺寸分档**的阶梯：`.15s`（下拉选项、树行、表格行）→ `.18s`（17px 勾选框）→ `.2s`（按钮、图标按钮、分页）→ `.25s` / `.3s`（看板列、面板、组织节点）。判据是控件尺寸而不是控件类型——小控件要立刻有反应，大面积变色太快会闪。

## 四、为什么这些动效「自然」

炫酷不来自参数，来自四条感知规律：

1. **快出慢收**。所有缓动都是 `*.out` 家族——起步快、收尾慢。真实世界里没有物体瞬间启动又匀速运动。唯一的例外是 `power2.in` 的退场（离开时可以加速）。
2. **过冲只出现一次**。全程只有「落定确认」用 `back.out(1.6)`——括号里的 1.6 是 GSAP 的回弹量参数（不是百分比），调到 3 以上就开始像果冻。其他地方一律不用带回弹的缓动。
3. **位移小、幅度克制**。按压缩 4.5%、悬停抬 3px、页面缩 0.6%、弹窗从 86% 展开。**动效的质感来自「几乎看不见但感觉到了」**，不是来自大幅运动。
4. **方向承载信息**。阶段切换按前进/后退选入射方向；列表按阅读序；并列卡片从中心展开；拖拽幽灵倾斜 2.5°。每一个方向选择都在回答「我刚才在往哪走」。

配套的减法：**每个页面只有一个视觉主角**，其余缩为小块。动效也是——同一时刻只有一处正在「表演」，其他都是状态切换。

## 五、十条核心模式

每条只说「关键洞察」；完整实现与踩坑在 `assets/motion-core.ts`（可直接拷走）和对应的 `references/`。

| # | 模式 | 关键洞察 | 详情 |
| --- | --- | --- | --- |
| 1 | 双闸门 | `motionSkipped()` = 要减少动态 **或** 页面在后台。切到后台的**那一刻**就把补间 `progress(1)` 推到终态，回前台看到的永远是完成态。三种「不画」要分清：减动效是画终态，隐藏与离屏是停帧 | `references/css-motion-layer.md` 十三 |
| 2 | 通道分离 | 同一元素上两条补间绝不写同一个属性：hover 写 `y`、press 写 `scale`，才能同时发生不打架。CSS 侧位移用独立 `translate` / `rotate`，把 `transform` 整条让给 GSAP | 本文铁律 2 |
| 3 | 事件委托 | `document` 级监听 + `closest(选择器)`，新控件命中选择器即获得同一手感。`pressed` 用 `Set` 追踪，`pointerup` / `pointercancel` 挂 `window` 统一释放 | `references/micro-interactions.md` 一 |
| 4 | 页面切换 | `:css="false"` + JS 钩子；**`out-in` 下 `done` 必须 `setTimeout(done, 0)`**，同步调用会让框架在补丁过程中重渲染。隐藏态写在时间轴开头的 `set` 里，内部只用 `to` 推进，收尾 `clearProps` | `references/page-and-overlay.md` 一 |
| 5 | 浮层从触发点展开 | 全局记指针坐标，600ms 窗口内算 `transformOrigin`；键盘触发把 `at` 置 0 回落中心。原点 clamp 在面板外扩 25%~125%，避免从屏幕角落飞入 | `references/page-and-overlay.md` 二 |
| 6 | 共享元素 morph | 中介层 `position: fixed` + `pointer-events: none`，用 `x`/`y`/`width`/`height` 补间。⚠️ `x`/`y` 走合成层，`width`/`height` 仍触发重排——所以它必须是**廉价实色盒**（无 `backdrop-filter`、固定圆角） | `references/page-and-overlay.md` 三 |
| 7 | 玻璃滑块 | 折算祖先缩放：`kx = pr.width / parent.offsetWidth`。不折算则首帧量偏小、滑块错位到下次切换才纠正。**`ResizeObserver` 必须同时观察容器和每个选项**——字体加载只改选项宽度 | `references/micro-interactions.md` 五 |
| 8 | `@property` 补间 | 渐变进度这类值不在可过渡列表里，注册后才能过渡；`inherits: false` 避免打脏后代。开关注满、环形进度、占比条都用它 | `references/css-motion-layer.md` 一 |
| 9 | 常驻帧循环 | 挂 `gsap.ticker` 而非自起 rAF；`dt` 夹在 `1/30` 内；每 20 帧量一次几何判离屏（比 `IntersectionObserver` 不受过渡与隐藏祖先影响）；`try/catch` 只报一次不让循环停摆；**帧内零 `querySelector`**，用 ref 回调建索引 | `references/canvas-stage.md` 六 |
| 10 | 临界阻尼弹簧 | `c = 2√k` 是关键：不过冲、不振荡，比 `ease` 更适合追随指针和布局变形。k 越大越硬（62 ≈ 0.5s 落定） | `references/canvas-stage.md` 七 |

#### clearProps 四类表：按节点命运决定写不写

| 补间类型 | 要不要 | 原因 |
| --- | --- | --- |
| 进入类（演完仍留在 DOM） | ✅ 必须 | 残留 `transform` 会让后续测量与布局全错 |
| 按压 / 悬停这类可逆微交互 | ❌ 不写 | 靠补间回默认值（`scale: 1` / `y: 0`）收尾 |
| 退场类（节点随即被卸载） | ❌ 不写 | 框架马上移除元素 |
| `slideThumb` 的定位 | ❌ 故意不清 | inline 定位就是它的常驻状态 |

判据是「节点会不会复生」，不是「这条补间重不重要」。

## 六、性能与无障碍护栏

| 项 | 做法 |
| --- | --- |
| 重排 | 常驻动画只写 `transform` / `opacity`；DOM 节点位置用 `translate3d` 直写，不经响应式 |
| `backdrop-filter` | **绝不补间**。顶栏凝结只切换一层静态玻璃的 `opacity` |
| 高分屏 | `Math.min(devicePixelRatio, 2)` 设上限，避免过度绘制 |
| 帧循环 | 隐藏停帧、离屏停帧、异常不停摆、提供 `flush()` 画终态 |
| 减弱动态效果 | 全局 `animation-duration: .01ms !important; transition-duration: .01ms !important`；JS 侧 `snap` 分支直写终态 |
| 降低透明度 | `prefers-reduced-transparency: reduce` 时关掉 `backdrop-filter`，改用实色面 |
| 键盘等价 | 涟漪与弹窗原点在键盘触发时回落中心；方向键在图谱节点间空间导航；`Esc` 逐层返回 |
| 焦点环 | 全局只删 `:focus`（鼠标点击不显环），`:focus-visible` 补回键盘环，全站一种颜色；浮层焦点陷阱，关闭后还给触发者；栈顶才 `aria-modal` |
| 不靠颜色 | 状态必须同时有文字或图标；`prefers-contrast: more` 时去掉颗粒层 |
| 装饰层 | Canvas / SVG 连线 / 点阵等纯装饰加 `pointer-events: none` + `aria-hidden="true"`；提示浮层只加 `pointer-events: none`，**文案保持可读**，要播报另用 `aria-live` 区域 |

## 七、快速决策

| 问题 | 答案 |
| --- | --- |
| 该用 CSS 过渡还是 GSAP？ | 单元素、状态切换、无时序 → CSS；跨元素编排、`stagger`、SVG 描边、共享元素 → GSAP |
| 什么时候不能给元素挂 `transform` 过渡？ | 该元素的 `transform` 已交给 GSAP 时——两次补间互相覆盖。没被 GSAP 接管的元素照常可以过渡 `transform` |
| 常驻动画怎么才能不烧 CPU？ | 挂 `gsap.ticker` + 隐藏停帧 + 离屏停帧 + 只动 `transform`/`opacity` |
| 后台标签页回来看到动画停在中途？ | 补间走 `motionSkipped()` 闸门直接给终态，`visibilitychange` 时 `progress(1)` 收尾；帧循环则是停帧（不调 `step`），别混为一谈 |
| 渐变进度怎么动画？ | `@property` 注册后过渡自定义属性 |
| 弹窗为什么从按钮位置炸开？ | 全局记指针坐标，600ms 内算 `transformOrigin`，键盘触发回落中心 |
| 列表进场为什么从中间展开？ | 并列卡片用 `stagger: { from: 'center' }`，比从左到右更有交付感；工作台网格则用「径向迸发」（各自算到中心的位移矢量） |
| 数字怎么滚动？ | 每条一位一条 `odo-strip`，`transition: transform` 到目标偏移，位次 key 从右往左编号 |
| 提示堆叠怎么做？ | 一个 `--depth` 变量同时驱动 `translateY` / `scale` / `opacity` / `z-index` |
| 倒计时怎么暂停？ | 记 `endsAt` 绝对时刻，暂停时反推剩余，恢复时按剩余重启；CSS 环用 `animation-play-state`，两处都要停 |
| 滑块的 `ResizeObserver` 该观察谁？ | 容器**和每个选项**——字体加载只改选项宽度，只观察容器会一直错位 |
| SVG 高亮怎么加粗？ | 只推 `stroke-width`，不碰 `d` 属性；降亮用 `stroke-opacity` |

## 八、参考文件

| 文件 | 内容 |
| --- | --- |
| `references/css-motion-layer.md` | CSS 层动效全景：`@property`、`@keyframes`、`:has()` 联动、牌堆、倒计时环、数字滚动、令牌工程、控件层细节配方、reduced-motion 降级 |
| `references/micro-interactions.md` | 微交互全集：按压、悬停、涟漪、指针光、玻璃滑块、骨架、spinner、径向迸发、登录卡轻倾与成功三拍 |
| `references/page-and-overlay.md` | 页面切换、浮层三类（弹窗/抽屉/浮出）、共享元素变形、底部浮条、Toast 牌堆、悬停意图与浮层定位 |
| `references/canvas-stage.md` | Canvas 舞台：调色板读取、纯绘制函数、DPR、帧循环、弹簧布局、触须与幽灵退场、命中区、SVG 描边技巧 |
| `references/chart-motion.md` | 图表动效：折线描绘与形变、柱体生长、grid stagger 热力级联、泳道现在线、刻度环、看板拖拽与 Flip |
| `references/motion-audit.md` | 审查手册：症状→根因诊断表、人工审查清单、可复用缺陷模式目录 |
| `references/porting-checklist.md` | 移植到其他前端栈的对照清单与最小可用实现 |
| `assets/motion-core.ts` | **可直接拷贝的框架无关核心实现**（零框架依赖，只用 GSAP；已过严格类型检查与 12 项冒烟测试） |
| `assets/motion-core.smoke.test.ts` | 上面那个文件的冒烟测试；拷走后先跑它验证落地成功 |
| `scripts/motion-audit.sh` | 可执行扫描：10 类高危反模式 + 3 类提醒 + 7 项能力探测，退出码可卡 CI |

## 九、反模式（看到就改）

- ❌ 用 `opacity` 脉冲表示「成功」→ 用一次 `back.out` 的 `scale` 弹入
- ❌ 补间 `backdrop-filter` → 它每帧重新栅格化背后全部内容。改补间 `opacity`，把带模糊的玻璃层预置好只切透明度
- ❌ 每帧创建新 tween → `gsap.quickTo()` 预建或直写 `style.transform`
- ❌ 动 `left` / `top` / `width` / `height` → 动 `transform`。例外只有「目标尺寸由外部布局决定、而非自身比例」时才动 `width`（`morphGhost` 的矩形变形、登录成功时按钮收拢成固定 46px 的圆）
- ❌ 开场动画每次刷新都重播 → `sessionStorage` 标记，同会话只播一次，且允许点击快进
- ❌ 进入类补间忘了 `clearProps` → 元素上留着 `transform`，后续布局与测量全错（按压复位、退场卸载、常驻定位三类不写，见上文「clearProps 四类表」）
- ❌ `stagger` 超过 0.1s → 用户以为卡了
- ❌ 装饰性动效 → 说不出能量语态就删掉
- ❌ 选中态用 `border: 0` 切换 → 用 `border-color: transparent`，否则 1px 布局抖动
- ❌ flex 子项忘写 `min-height: 0` → 弹窗被内容撑爆、溢出视口
- ❌ 每帧用 `Math.random()` → 节点抖动、级联错乱；用 id 哈希拿稳定伪随机
- ❌ 帧循环里改响应式状态 → 触发框架渲染，60fps 必卡；用 `ref` 直写 `style`
- ❌ 静默截断列表 → 让截断点落在感知阈值内，或像「还有 N 项」那样明确告知
- ❌ 拖拽不设位移阈值 → 手部 2–3px 抖动就触发拖拽；5px 以内算点击
- ❌ 卸载只 `loop.stop()` → 还要 `killTweensOf`、断开 Observer、移除监听，四件事都做
- ❌ `Math.max(0, ...)` 漏在时间轴位置参数上 → GSAP 不收负值，触须顺序会乱
