# 动效审查手册

`scripts/motion-audit.sh` 抓「高度可疑」，本手册抓「必须人看」的部分：时序、语义、观感、边界。

三种使用场景：

| 场景 | 怎么做 |
| --- | --- |
| 新项目要接入动效系统 | 先跑脚本看能力缺口 → 按 `porting-checklist.md` 落地 → 过本手册第三节清单 |
| 上线前验收 | 跑脚本 → 按第二节诊断表逐条点一遍 → 过第三节清单 |
| 用户反馈「卡 / 抖 / 不自然」 | 直接查第三节诊断表，症状 → 根因 |

## 一、先跑脚本

```bash
./scripts/motion-audit.sh <项目目录>     # 退出码 = 高危类数，可直接卡 CI
```

覆盖 10 类高危 + 3 类提醒 + 7 项能力探测。脚本做了防误报处理（属性名加边界、配对类按文件比对、否定类按行排除），**宁可漏报不要误报**——误报会训练人忽略整个脚本。

已知的漏报（脚本结构上抓不到，必须人看）：

- 时序错误（`getBoundingClientRect` 早于 DOM 更新）
- 缓存未失效（主题/数据变化后仍用旧值）
- 语义错误（该用 `back.out` 的地方用了 `power2.out`）
- `clearProps` 该清没清 / 不该清乱清
- 观感问题（幅度过大、stagger 过慢、动效语态说不出口）

脚本报「高危」时先分清是**组件级**还是**应用级单例**：装在 `install` 函数里、有幂等锁、只装一次的监听，不移除是正确的。

## 二、诊断表：症状 → 根因

按用户或开发者看到的**现象**查，不按技术分类查。

### 卡顿与掉帧

| 症状 | 根因 | 确认方法 | 修法 |
| --- | --- | --- | --- |
| 动画整体发顿 | `transition` 里过渡了 `width`/`height`/`top`/`left`/`margin` | DevTools Performance，看紫色 Layout 条 | 改 `transform` / `translate` / `rotate` |
| 开弹窗时明显卡一下 | 补间了 `backdrop-filter` | 同上，看 Rendering 占比 | 预置静态玻璃层，只切 `opacity` |
| 拖拽时跟手发糊 | 拖拽路径上做了补间 | 看是否有 `gsap.to` 而非 `gsap.set` | 跟手一律 `gsap.set` 直写 |
| 画布常驻动画烧 CPU | 每帧新建对象/补间/闭包；每帧读布局或查 DOM | Performance 看 JS 自执行时间 | 预建对象；`gsap.quickTo()`；ref 回调建索引，帧内只读缓存 |
| 页面滚动时图表卡 | 帧循环没做离屏停帧 | 让画布滚出视口看 CPU | `getBoundingClientRect` 每 20 帧量一次，离屏 `return` |

### 状态停留在半路

| 症状 | 根因 | 确认方法 | 修法 |
| --- | --- | --- | --- |
| 切标签页回来，弹窗停在半透明 | 缺 `document.hidden` 闸门 | 手动切走再切回 | 双闸门直接给终态 + `visibilitychange` 时 `progress(1, false)` |
| 切标签页回来，弹簧炸开 | 帧循环 `dt` 没夹紧 | 同上 | `Math.min(1/30, ...)` |
| 打开「减弱动态效果」后元素不显示 | 闸门分支没给终态，元素停在 `opacity: 0` | 系统设置里开减弱动态效果 | 跳过时 `return done()` 并让元素回到 CSS 默认可见态 |
| 减弱动态效果下数字停在 0 | `requestAnimationFrame` 在后台不触发 | 后台打开页面 | `setTimeout` 兜底 |

### 位置与测量错误

| 症状 | 根因 | 确认方法 | 修法 |
| --- | --- | --- | --- |
| 弹窗从屏幕角落飞入 | `transformOrigin` 没算或没 clamp | 点屏幕角落的按钮 | 算触发点相对面板的位置，clamp 在面板外扩一圈内 |
| 滑块位置偏，下次切换才纠正 | 祖先缩放没折算回布局像素 | 在弹窗里开分段控件 | `kx = pr.width / parent.offsetWidth` |
| 网页字体加载后滑块错位 | `ResizeObserver` 只观察了容器 | 慢网络 + 自定义字体 | 容器**和每个选项**都 observe |
| 尺寸变化时整图闪烁 | 尺寸回传没留死区 | 滚动让滚动条出现/消失 | `> 0.5px` 才写入 |
| 画布主题切换后还是旧配色 | 调色板缓存没失效 | 设置里切外观 | `MutationObserver` 监听 `data-theme` 置空缓存 |
| 下拉框浮在错误位置 | `scroll` 监听没开捕获阶段 | 在滚动容器里开下拉 | `addEventListener('scroll', place, true)` |

### 交互误判

| 症状 | 根因 | 确认方法 | 修法 |
| --- | --- | --- | --- |
| 点卡片却触发了拖拽 | 缺位移阈值 | 在卡片上单击 | `Math.hypot(dx, dy) < 5` 不算拖拽 |
| 点当前导航项，页面重播进场 | 同路径也 `router.push` | 点已选中项 | `if (route.path !== path)` 才推 |
| 嵌套弹窗一按 Esc 全关 | 缺 `stopImmediatePropagation()` | 打开两层弹窗 | 只在 `trap.isTop()` 时关，并阻止事件继续传 |
| 悬停预览卡闪退 | 缺离开宽限 | 指针从触发区移向卡片 | `hide()` 留 120ms 宽限 |
| 按压时拖出文字选区 | 缺 `user-select: none` | 在按钮上按下并拖动 | 控件统一 `user-select: none` |

### 视觉不自然

| 症状 | 根因 | 确认方法 | 修法 |
| --- | --- | --- | --- |
| 动效「廉价」「玩具感」 | 过冲用多了 | 数一下有几处 `back.out` | 只留「落定确认」一处 |
| 觉得「糊」「不精致」 | 细字重被伪粗体合成 | 看 `font-synthesis` | `:root { font-synthesis: none }` |
| 大号数字发散 | 缺负字距 | 看 `letter-spacing` | 大号数字 `-.035em` ~ `-.045em`，正文不调 |
| 列表进场末尾突然跳出一片 | 静默截断 | 长列表 | 截断点落在感知阈值内，或明确告知「还有 N 项」 |
| 数字滚动时个位十位错位 | `key` 从左往右编号 | 让数字从 99 变 100 | `key: text.length - i` |
| 选中态时布局抖一下 | 用 `border: 0` 切换 | 逐帧看 | 用 `border-color: transparent`，边框宽度不变 |
| 弹窗内容变化时高度跳 | 缺高度预留 | 切换弹窗内的状态 | 容器 `min-height` 取两者较高值 |
| 移动端工具栏收起时页面跳 | 用 `vh` 而非 `dvh` | 真机 | 全链路换 `dvh` |

### 无障碍

| 症状 | 根因 | 确认方法 | 修法 |
| --- | --- | --- | --- |
| 弹窗内 Tab 不到某个按钮 | `offsetParent !== null` 对 `fixed` 恒为 `null` | 浮层内放一个 fixed 控件 | 改 `el.getClientRects().length > 0` |
| 键盘用户找不到焦点 | `outline: none` 没配 `:focus-visible` | 只用键盘走一圈 | 全局只删 `:focus`，`:focus-visible` 补环 |
| 焦点环被切掉一角 | 外扩 offset 超出 `overflow: clip` 的祖先 | 看导航项 | 容器内的可聚焦元素用负 `outline-offset` |
| 屏幕阅读器念出装饰内容 | 装饰层漏加 `aria-hidden` | 开读屏 | Canvas / SVG 连线 / 点阵加 `aria-hidden="true"` |
| 读屏念不出提示文案 | 提示浮层误加 `aria-hidden` | 开读屏 | 提示层只加 `pointer-events: none`，要播报另用 `aria-live` |
| 读屏把回答当选项念 | `role` 没随模式切换 | 命令面板进问答模式 | `:role="askMode ? 'region' : 'listbox'"` |

## 三、人工审查清单

脚本查不出的，用这些问题过一遍。每条都能用是/否回答。

### 语义与取舍

- [ ] 每段动效说得出口属于哪种能量语态（蓄/放/导/结/停摆）？
- [ ] 有没有「说不出语态」的装饰性动效？（有就删）
- [ ] 同一时刻是否只有一处在「表演」，其余都是状态切换？
- [ ] 时长与缓动是否只从常量表取，没有散落的魔法数字？
- [ ] 每页是否只有一个视觉主角？
- [ ] 位移幅度是否克制（按压缩 4.5% / 悬停抬 3px / 页面缩 0.6% 这个量级）？

### 时序与状态

- [ ] `getBoundingClientRect` 之前是否等了 DOM 更新（`nextTick`）？
- [ ] 缓存（调色板、测量值、路径长度）在数据或主题变化后是否失效？
- [ ] 异步请求是否有竞态丢弃（序号自增 + 不匹配就扔）？
- [ ] 序号是实例级还是模块级？（模块级在同屏多实例时会互相顶掉）
- [ ] 异步失败是否有回滚（接口失败时幽灵弹回原处、恢复按钮）？
- [ ] measure → mutate → measure 是否被压缩到一次？（避免强制同步布局）

### 可访问性

- [ ] 开启「减弱动态效果」后，所有动效到终态且功能不缺失？
- [ ] 键盘能完成所有交互？拖拽是否有菜单等价路径？
- [ ] 键盘触发的动效有合理回落（涟漪从中心、弹窗居中淡入）？
- [ ] 装饰层与内容层的 `aria-hidden` 是否分清？
- [ ] 焦点环是否被祖先的 `overflow: clip` 裁掉？
- [ ] 常驻动画是否有关闭开关（暂停/重播）？
- [ ] `prefers-reduced-transparency: reduce` 下有实色回退？

### 性能

- [ ] 常驻动画只写 `transform` / `opacity`？
- [ ] 帧循环里有没有读布局（`getBoundingClientRect` / `offsetWidth`）或查 DOM？
- [ ] `dt` 是否夹在 `1/30` 内？
- [ ] 隐藏停帧 + 离屏停帧都有？
- [ ] DPR 是否夹在 2 以内？
- [ ] 卸载是否四件事都做：`loop.stop()` + `killTweensOf` + `disconnect` + `removeEventListener`？
- [ ] `will-change` 是否只加在真的会动的元素上，且 reduced-motion 下释放？
- [ ] `clearProps` 是否按节点命运分四类处理（见 `SKILL.md` 第五节「clearProps 四类表」）？

### 边界与降级

- [ ] 空数据 / 加载中 / 错误三态都有？
- [ ] 浮层定位是否做了视口夹紧与上下翻转？
- [ ] 窄屏是否降级？断点降级是否显式排除用户主动状态（`:not(.is-collapsed)`）？
- [ ] 上限是否告知用户，而不是静默截断？
- [ ] `localStorage` / `sessionStorage` 读写是否包了 `try/catch`？
- [ ] 有没有除零、空数组、`NaN` 的兜底？

### CSS 架构

- [ ] 有没有绕过令牌的手写字面量（而对应令牌已存在）？
- [ ] 同一条 `transform` 通道是否被 CSS 与 JS 同时写？
- [ ] `@property` 注册的自定义属性才被过渡？
- [ ] 深色态是否只改令牌，组件规则零改动？
- [ ] z-index 是否走令牌 + 焦点栈，没有硬编码大数？
- [ ] `!important` 是否只在全局降级块里？

## 四、CI 接入

```yaml
# GitHub Actions 片段
- name: 动效反模式扫描
  run: |
    chmod +x .claude/skills/motion-craft/scripts/motion-audit.sh
    .claude/skills/motion-craft/scripts/motion-audit.sh ./src || echo "::warning::发现高危动效反模式，见日志"
```

建议**先用 `warning` 而不是 `error`**：脚本的高危是「高度可疑」而非「确定有错」，直接卡 CI 会被人加 `|| true` 绕过。跑一段时间、把误报规则收紧后再升级成 error。

如果想更严，可以只卡其中几类（把不关心的检查注释掉），或者反过来——**先用能力探测当门槛**：新项目如果连 `prefers-reduced-motion` 都没有，那比任何单条反模式都严重。

## 五、缺陷模式目录

下面是「在本项目源码里真实抓到过」的可复用缺陷模式。用到新项目时，按这张表逐条问「我们这儿有没有」。

> 说明：每条都标注了在本项目的实例（`文件:行号`）。迁移到其他项目时行号无效，**模式和检测方法有效**。

### A. 共享状态被多实例共用

| 模式 | 症状 | 检测 |
| --- | --- | --- |
| 模块级请求序号 | 同屏两个列表，后发的响应被序号顶掉，列表闪回旧数据 | grep `^let requestId` / `^let seq`，确认在不在组合函数体内 |
| 模块级缓存 Promise | 两个实例共用一次加载，其中一个取消后另一个也空 | grep `^let pending` / `^let loaded` |
| 模块级定时器句柄 | 两个实例互相清掉对方的定时器 | grep `^let timer` |
| 实例级签名被误当模块级 | 多表格同屏互相顶掉进场动画 | 确认 `let lastSignature` 在 `<script setup>` 里（实例级）而非 `.ts` 模块里 |

**判据**：`.vue` 的 `<script setup>` 顶层 `let` 是**实例级**（编译进 `setup()`），普通 `.ts` / `.js` 模块的顶层 `let` 是**模块级**。要单例就加注释说明，否则收进函数体。

### B. 缓存未失效

| 模式 | 症状 | 检测 |
| --- | --- | --- |
| 画布调色板只读一次 | 切换主题后画布停在旧配色，且不刷新永不对 | grep `readStagePalette` / `resolveColors`，确认有没有配 `MutationObserver` |
| 路径长度未缓存 | 每帧 `getTotalLength()`，帧预算直接吃光 | 确认长度在数据变化时算一次并缓存 |
| 测量值跨帧复用 | 容器尺寸变了还在用旧值 | 确认有 `ResizeObserver` 且带死区 |

### C. 生命周期漏配

| 模式 | 症状 | 检测 |
| --- | --- | --- |
| 补间未杀 | 组件销毁后补间继续写已移除节点，控制台报错且内存不回收 | 确认 `onBeforeUnmount` 里有 `gsap.killTweensOf(...)` |
| 只 `loop.stop()` 不够 | 帧循环停了，GSAP 补间还在跑 | 四件事都做：stop / killTweensOf / disconnect / removeListener |
| `watch` 缺 `immediate` | 首帧不播，要等第一次数据变化 | 确认首屏要播的 watch 有 `immediate: true` |
| 卸载后回调写 ref | 定时器/回调在组件销毁后写已销毁的 ref | 确认清理函数里清了定时器与监听 |

### D. 唯一入口被绕过

| 模式 | 症状 | 检测 |
| --- | --- | --- |
| 组件自己写补间 | 改一处手感要改十个地方；两处 `EASE` 取值还可能不一致 | grep `from 'gsap'`，正常只应出现在 `motion.ts` |
| 死导出 | 读代码的人以为某个能力已被使用 | grep 导出名，确认有调用方 |
| 死 CSS 变量 | 读者去找不存在的消费方 | grep `--var-name`，确认 CSS 里有地方读它 |

**落地方式**：`motion.ts` 末尾 `export { gsap }`，让页面连裸 `gsap.set` 都从唯一入口导入——把「不引第二个动效库」从代码规范变成模块依赖。

### E. 层级与焦点

| 模式 | 症状 | 检测 |
| --- | --- | --- |
| 硬编码 z-index | 嵌套浮层按 DOM 顺序而非打开顺序叠加 | grep `z-index: [5-9][0-9]{2,}` |
| `offsetParent` 判可见 | `fixed` 控件被静默踢出 Tab 循环 | grep `offsetParent !== null` |
| Esc 一按全关 | 嵌套弹窗同时关闭 | 确认有 `isTop()` + `stopImmediatePropagation()` |
| 焦点环被裁 | 键盘用户看到环缺一角 | 容器内可聚焦元素用负 `outline-offset` |

### F. 降级缺失

| 模式 | 症状 | 检测 |
| --- | --- | --- |
| 无 reduced-motion | 减弱动态效果用户看到全部动画 | grep `prefers-reduced-motion`，CSS 与 JS 两侧都要有 |
| 无 reduced-transparency | 玻璃拟态对低视力用户不友好 | grep `prefers-reduced-transparency` |
| `vh` 而非 `dvh` | 移动端工具栏收起时页面跳 | grep `100vh` |
| flex 子项缺 `min-height: 0` | 弹窗被内容撑爆溢出视口 | 看可滚动子项 |

## 六、升级 skill 的方式

在新的项目里抓到本章节没有的缺陷模式时，按这个格式补进来：

```markdown
| 模式名（中文，可复用的类名） | 用户看到什么 | grep 模式或审查问题 |
```

补的标准：**必须是真实发生过的**，不能是「理论上可能有」。一条没踩过的模式会稀释整张表的可信度。
