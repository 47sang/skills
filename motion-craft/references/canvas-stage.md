# Canvas 舞台

Canvas 适合「几十个元素同时动」的场景：图谱节点、背景网络、珍珠球、脉冲。DOM 保留可交互与可读的部分。

## 一、分工原则

| 画在 Canvas | 留在 DOM |
| --- | --- |
| 连线、脉冲、珍珠球、刻度表盘、圆点、光柱、背景网络、涟漪 | 标签、徽标、命中区、工具按钮 |

好处：文字永远清晰（不受 DPR 缩放影响）、可聚焦、可被屏幕阅读器读到、命中测试用原生事件。

**零尺寸锚点模式**：DOM 节点是 `width: 0; height: 0` 的锚点，位置由帧循环写 `transform`；可见主体 `.rg-body` 用 `position: absolute` + `translate` 相对锚点偏移。

```css
.rg-node { position: absolute; left: 0; top: 0; width: 0; height: 0; will-change: transform, opacity; opacity: 0 }
.rg-body { position: absolute; left: 0; top: 0; translate: -50% -50%; }
.rg-node.align-left  .rg-body { translate: -7px -50% }
.rg-node.align-right .rg-body { translate: calc(-100% + 7px) -50%; flex-direction: row-reverse }
```

锚点元素按可交互性切换标签：可交互的渲染成 `button`（有焦点、有 `aria-label`、有键盘事件），`interactive: false` 的静态节点渲染成 `div` 并给 `tabindex="-1"`——**同一套几何，两种语义**。

### `--size` 是 Canvas 与 DOM 的唯一尺寸契约

舞台变体里珍珠球、刻度表盘的直径由一个 CSS 变量给出，Canvas 绘制和 DOM 命中区都从它算：

```css
.rg.is-stage .rg-node.is-core::before,
.rg.is-stage .rg-node.is-hub::before {
  content: ""; position: absolute; border-radius: 50%;
  width: var(--size, 96px); height: var(--size, 96px);
  left: calc(var(--size, 96px) / -2); top: calc(var(--size, 96px) / -2);
}
```

```ts
// Canvas 侧：core 收 size/2 作半径，hub 收 size 作直径
paintOrb(ctx, x, y, (node.size ?? 96) / 2 * st.s.x, t, p, {...})
paintDial(ctx, x, y, (node.size ?? 104) * st.s.x, t, color, p, {...})
```

一处改、两边同步，不会出现「图形比命中区大」或反过来。**注意语义差别**：`core` / `hub` 的 `--size` 是直径；`slab`（台阶）的 `--size` 是宽度，高度由内容决定，Canvas 的光柱再内缩 8px。「严格同尺寸」只对圆形成立。

## 二、调色板：从 CSS 变量读

Canvas 无法用 CSS 变量，但可以读：

```ts
export function readStagePalette(el: Element): StagePalette {
  const css = getComputedStyle(el)
  const get = (name: string, fallback: RGB) => css.getPropertyValue(name).trim() || fallback
  return {
    cat: [ink, get('--graph-1', ...), get('--graph-2', ...), /* ... */],
    ink: get('--graph-ink', '46, 58, 62'),
    accent: get('--graph-accent', '35, 109, 233'),
    lime: get('--graph-lime', '110, 190, 36'),
    danger: get('--graph-danger', '224, 68, 59'),
    paper: get('--graph-paper', '255, 255, 255'),
  }
}
```

令牌存成 `"r, g, b"` 三元组字符串，绘制时拼 `rgba(${c}, ${a})`——比存 hex 再解析快，也比存 `Color` 对象省事。**深色主题只改 CSS 变量，Canvas 代码一行不动**。

⚠️ **但「读一次」和「每次读」是两种设计，别混**：

```ts
// RelationGraph：惰性读 + MutationObserver 失效缓存，主题切换即时生效
let palette: StagePalette | null = null
if (!palette && root.value) palette = readStagePalette(root.value)
themeObserver = new MutationObserver(() => { palette = null })
themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })

// NeuralNet：只在 onMounted 读一次，运行中切主题不会刷新画布颜色
function resolveColors() {
  const cs = getComputedStyle(document.documentElement)
  cAccent = v('--blue', cAccent)
}
```

后者能工作是因为登录页不会在会话中途切主题。**凡是常驻的画布都要按前者的写法做**，否则用户在设置里切换外观后，画布还停在旧配色——而且因为颜色是缓存的，不刷新页面永远不会对。

## 三、纯绘制函数

绘制件不持有状态，参数进、画面出，可单测、可复用：

```ts
export function paintOrb(ctx, x, y, r, t, p, opts = {}) {
  const alpha = opts.alpha ?? 1
  if (alpha <= 0.01 || r <= 1) return          // 早退：不可见就不画
  ctx.save()
  ctx.globalAlpha = alpha
  /* 外圈刻度环：一段蓝色扫描弧缓慢转动 */
  const ringR = r * 1.3, n = 72
  const head = opts.live !== false ? (t * 0.35) % TAU : 0.9
  for (let i = 0; i < n; i += 1) {
    const a = (i / n) * TAU
    const behind = ((head - a) % TAU + TAU) % TAU
    const k = behind < 1.1 ? 1 - behind / 1.1 : 0        // 扫描头后面 1.1 弧度内渐亮
    ctx.strokeStyle = k > 0 ? rgba(p.accent, 0.2 + k * 0.65) : rgba(p.ink, i % 6 === 0 ? 0.22 : 0.12)
    /* ... */
  }
  /* 球体：软阴影 + 珠光径向渐变 */
  ctx.shadowColor = rgba(p.ink, 0.2); ctx.shadowBlur = r * 0.6; ctx.shadowOffsetY = r * 0.2
  const body = ctx.createRadialGradient(x - r * 0.38, y - r * 0.42, r * 0.05, x, y, r)
  body.addColorStop(0, 'rgba(255,255,255,1)')
  body.addColorStop(0.55, 'rgba(246,249,248,1)')
  body.addColorStop(1, 'rgba(214,223,221,1)')
  ctx.fillStyle = body
  ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill()
  ctx.shadowColor = 'transparent'                      // 必须复位，否则后续都带阴影
  ctx.restore()
}
```

**珍珠质感配方**（三层）：

1. 软阴影：`shadowBlur = r * 0.6` + `shadowOffsetY = r * 0.2`，颜色用墨色 20%
2. 珠光：径向渐变，光源偏左上（`x - r*0.38, y - r*0.42`），白 → 近白 → 灰蓝
3. 淡虹彩：右下青柠 22%、左下蓝 14% 两团径向渐变，中心随 `sin(t*0.5)` 缓慢游移

**纪律**：`ctx.save()` / `ctx.restore()` 成对；`shadowColor` 用完立刻置 `transparent`；不可见（`alpha <= 0.01` 或 `r <= 1`）直接早退。

## 四、稳定伪随机

```ts
export const seedOf = (id: string) => {
  let h = 0
  for (let i = 0; i < id.length; i += 1) h = (h * 31 + id.charCodeAt(i)) | 0
  return (Math.abs(h) % 1000) / 1000
}
```

**为什么不用 `Math.random()`**：每帧随机 → 节点抖动、长度跳变、级联顺序错乱。用 id 哈希后，同一个节点每帧拿到同一个随机数，看起来「随机」但稳定。

## 五、DPR 与尺寸

```ts
const dpr = Math.min(window.devicePixelRatio || 1, 2)      // 上限 2
if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
  canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr)
}
const ctx = canvas.getContext('2d')
ctx.setTransform(dpr, 0, 0, dpr, 0, 0)                     // 之后用 CSS 像素坐标画
ctx.clearRect(0, 0, w, h)
```

- **DPR 上限 2**：3x 屏上 9 倍像素，收益极小、成本翻倍。
- **只在尺寸真变时改 `canvas.width`**——赋值会清空画布并重新分配缓冲。
- `setTransform` 之后全部用 CSS 像素思考，不需要在绘制代码里乘 DPR。

## 六、帧循环

完整实现见 `SKILL.md` 第五节第 9 条。接入方式：

```ts
const loop = createFrameLoop((dt, t) => { /* 每帧绘制 */ })
onMounted(() => {
  resizeObserver = new ResizeObserver(() => loop.flush())
  resizeObserver.observe(root.value)
  loop.start(root.value)                 // 传入元素 → 离屏检测的目标
})
onBeforeUnmount(() => { loop.stop(); resizeObserver?.disconnect() })
```

数据变化后补一帧，保证 reduced-motion 下立即落到终态：

```ts
watch(() => [props.nodes, props.links, paused.value], () => nextTick(() => loop.flush()))
```

**注意 `flush()` 和 `snap` 是两套机制**：`snap`（帧回调内部判 `motionSkipped()`）负责「reduced-motion 时把目标值直接赋给弹簧当前值，跳过积分」；`flush()` 负责「数据变更、burst、resize 后立刻多画一帧，不等下一帧」。两者都要有。

### 帧循环里零 `querySelector`

模板 ref 回调把元素按连线下标写进数组、按节点 id 写进 Map，每帧只读缓存：

```ts
const pathEls: Array<SVGPathElement | null> = []
const pulseEls: Array<Array<SVGCircleElement | null>> = []
const nodeEls = new Map<string, HTMLElement>()

// 模板里：:ref="el => { pathEls[i] = el as SVGPathElement | null }"
//         :ref="el => { (pulseEls[i] ||= [])[0] = el as SVGCircleElement | null }"
function bindNode(id: string, el: unknown) {
  if (el instanceof HTMLElement) nodeEls.set(id, el)
  else nodeEls.delete(id)                       // 卸载时同步清掉
}
```

每帧几十次 `querySelector` 会直接把帧预算吃光。**ref 回调是「挂载时建立索引、卸载时清理」的唯一时机**，`instanceof HTMLElement` 用来区分挂载（元素）与卸载（`null`）。

### 尺寸回传要留死区

```ts
resizeObserver = new ResizeObserver(([entry]) => {
  const { width, height } = entry.contentRect
  if (Math.abs(width - size.value.w) > 0.5 || Math.abs(height - size.value.h) > 0.5) {
    size.value = { w: width, h: height }
  }
})
```

亚像素抖动（滚动条出现/消失、`dvh` 变化、缩放）会让 `ResizeObserver` 连续触发。不留 0.5px 死区的话，每次抖动都会重算整图布局并重设 Canvas 尺寸——后者会清空画布，视觉上就是闪烁。

### 卸载时必须显式杀补间

补间不随组件卸载自动停止。只 `loop.stop()` 不够，还要杀掉可能仍在跑的 GSAP 补间：

```ts
onBeforeUnmount(() => {
  loop.stop()
  resizeObserver?.disconnect()
  themeObserver?.disconnect()
  gsap.killTweensOf(list)          // 指向具体元素或集合
})
```

漏了这条的后果：组件销毁后补间继续写已移除节点的 `style`，控制台报错，且那部分内存不会被回收。

## 七、弹簧布局：节点追随 + 触须 + 幽灵

每个节点四个弹簧（位置、透明度、缩放）+ 出生时间：

```ts
interface NodeState { x: SpringState; y: SpringState; o: SpringState; s: SpringState; born: number; el: HTMLElement | null }

function ensureState(node, now) {
  const origin = node.from ? states.get(node.from) : null
  const snap = motionSkipped()
  const sx = snap ? node.x : origin ? origin.x.x : node.x     // 新节点从 from 节点当前位置出生
  st = { x: springOf(sx), y: springOf(sy),
         o: springOf(snap ? 1 : 0),
         // 缩放起始：无 from 的独立新节点从 0.82 长出，从父节点长出的触须从 0.4 长出（更小，读作「抽出来」）
         s: springOf(snap ? 1 : origin ? 0.4 : 0.82), born: now, el: null }
}
```

**两个不同的缩放起始值是有意的**：从父节点长出的触须从 0.4 开始（明显是「从别处抽出来的」），独立出现的新节点从 0.82 开始（只是「显形」）。混用一个值会让这两种语义分不开。

每帧：

```ts
const ready = snap || now - st.born >= (node.delay ?? 0) * 1000    // delay 依次长出 = 触须
const tx = ready || ghost ? node.x + drift.x : st.x.x
spring(st.x, tx, dt, 70); spring(st.y, ty, dt, 70)
spring(st.o, ghost ? 0 : ready ? 1 : 0, dt, ghost ? 120 : 50)     // 退场比进场硬
spring(st.s, ghost ? 0.5 : ready ? 1 : st.s.x, dt, 60)
el.style.transform = `translate3d(${st.x.x}px, ${st.y.x}px, 0) scale(${st.s.x})`
el.style.opacity = String(o)
el.style.visibility = o < 0.01 ? 'hidden' : ''
```

**连线的可见性取两端节点透明度的最小值**——任一端点还在淡入，连线就不出现：

```ts
const vis = Math.max(0, Math.min(A.o.x, B.o.x, 1))
if (vis < 0.5 || !l.flow || l.flow === 'none') { c.style.opacity = '0'; return }   // 两端都到位脉冲才启播
```

不取最小值会看到「线已画到位置、节点还没出现」的穿帮。

四个技巧：

- **直写 `style.transform`，不经响应式**：每帧改响应式状态会触发 Vue 渲染，60fps 下必卡。
- **`visibility: hidden` 而不是 `display: none`**：不可见的节点不参与命中测试，但保留布局信息。
- **幽灵退场**：被移除的节点不立刻删状态，而是变成 `ghost`，弹簧把它的目标指回 `from` 节点，透明度归零后再清理——视觉上「收回触须」。
- **透明伪元素把零尺寸锚点的可点区域撑成整颗球**：珍珠球画在 Canvas 上，DOM 只剩 0×0 锚点，用一个无边框无背景的 `::before` 等大圆撑出命中区：

```css
.rg.is-stage .rg-node.is-core::before {
  content: ""; position: absolute; border-radius: 50%;
  width: var(--size, 96px); height: var(--size, 96px);
  left: calc(var(--size, 96px) / -2); top: calc(var(--size, 96px) / -2);
}
```

### 一层邻居高亮：一个 computed 驱动全图降亮

```ts
const neighbors = computed(() => {              // 双向邻接表
  const map = new Map<string, Set<string>>()
  for (const l of props.links) {
    if (!map.has(l.a)) map.set(l.a, new Set())
    if (!map.has(l.b)) map.set(l.b, new Set())
    map.get(l.a)!.add(l.b); map.get(l.b)!.add(l.a)
  }
  return map
})
const lit = computed<Set<string> | null>(() => {
  if (hoverId.value) return new Set([hoverId.value, ...(neighbors.value.get(hoverId.value) ?? [])])
  return props.highlight?.length ? new Set(props.highlight) : null
})
const isDim = (id: string) => Boolean(lit.value && !lit.value.has(id))
```

降亮系数按元素类型分别给，不用同一个值——越「实」的元素降得越少：

| 元素 | 降亮系数 |
| --- | --- |
| 连线（stage） | 0.1 |
| 圆点 | 0.25 |
| 刻度表盘 | 0.35 |
| 台阶光柱 | 0.35 |
| 珍珠球 | 0.45 |

**「几何归帧循环、颜色与降亮归 CSS 类」**：浅色变体里帧循环只写 `d` 和 `opacity`，连线的 `cat-N` / `is-lit` / `is-dim` / `is-active` 类切换交给 `transition: stroke .3s, stroke-width .3s`。两条通道不打架，也不必每帧写样式。

### 上限要看得见，不能静默截断

一列放不下时，末尾追加一枚不可交互的「还有 N 项」节点，并给它更长的 `delay`——它最后长出，读作「这列还没完」：

```ts
if (items.length > cap) {
  nodes.push({ id: moreId, x, y: y0 + shown.length * gap,
               label: `还有 ${items.length - cap} 项`, kind: 'item', align,
               interactive: false, delay: 0.5 })     // 比正常项更晚出现
}
```

`interactive: false` 让它渲染成 `div` 而不是 `button`，`tabindex="-1"`，不参与键盘导航。**静默截断会让用户以为数据只有这么多**；把上限本身变成一个可见元素，信息就诚实了。同理适用于列表的 `slice(0, 14)`——要么让截断点落在感知阈值内，要么明确告知。

## 八、常驻轻漂

```ts
const drifts = node.float && live && (node.kind === 'hub' || node.kind === 'core')
const drift = drifts
  ? { x: Math.sin(t * 0.37 + i * 1.7) * 7, y: Math.sin(t * 0.9 + i * 2.1) * 6 }
  : { x: 0, y: 0 }
```

- 用**索引** `i` 做相位偏移，避免所有节点同步漂（那会看起来像整体在晃）。
- 两个不同频率（0.37 / 0.9）叠加成李萨如轨迹，比单轴往复自然。
- 幅度 6–7px，再大就成「飘」而不是「活」。

### GSAP 时间轴的位置参数不接受负值

按层级递增延迟时必须夹紧：

```ts
const delay = Math.max(0, d * 0.2 - 0.12)      // 不能直接写 d * 0.2 - 0.12
```

`tl.to(el, {...}, delay)` 的第三个参数是「绝对时间点」。传负数会被当成 0 或直接报错，浅层节点的延迟会比预期短，触须的长出顺序就乱了。**凡是「算出某个时间偏移」的地方，都要 `Math.max(0, ...)`。**

## 九、连线几何与脉冲

```ts
function geometry(l, t, live) {
  const A = states.get(l.a), B = states.get(l.b)
  const dx = B.x.x - A.x.x, dy = B.y.x - A.x.x
  const d = Math.hypot(dx, dy) || 1
  const bend = (live ? 14 * Math.sin(t * 0.5 + (A.x.x + B.y.x) * 0.01) : 0) + d * 0.08
  const ux = dx / d, uy = dy / d
  return {
    x1: A.x.x, y1: A.y.x,
    c1x: A.x.x + dx * 0.35 - uy * bend, c1y: A.y.x + dy * 0.35 + ux * bend,
    c2x: A.x.x + dx * 0.70 - uy * bend, c2y: A.y.x + dy * 0.70 + ux * bend,
    x2: B.x.x, y2: B.y.x,
  }
}
```

- 弯折量 `bend` 由「距离的 8%」+「随时间缓慢变化的正弦」组成，短线微弯、长线大弯。
- **相位源用端点坐标**（`Math.sin(t * 0.5 + (x1 + y2) * 0.01)`），每条线的摆动节奏不同；用全局统一相位的话所有线同时呼吸，看起来像整页在抖。
- `live` 为假时弯折归零，reduced-motion 下画成静态弧线。

脉冲沿三次贝塞尔走，取 `u ∈ [0,1]`：

```ts
export function bezierAt(p0, p1, p2, p3, u) {
  const m = 1 - u
  return m*m*m*p0 + 3*m*m*u*p1 + 3*m*u*u*p2 + u*u*u*p3
}
let u = (t * 0.3 + i * 0.137 + k * 0.5) % 1
if (k === 1) u = 1 - u                       // 第二条线反向走
paintPulse(ctx, bezierAt(g.x1, g.c1x, g.c2x, g.x2, u), bezierAt(g.y1, g.c1y, g.c2y, g.y2, u), ...)
```

- `+ i * 0.137` 给每条线一个相位偏移，脉冲不同步。
- 透明度用 `Math.sin(u * Math.PI)`——两端淡入淡出，中间最亮，没有「突然出现/消失」。

### 沿路径取点：`getPointAtLength` 比手写贝塞尔简单

关系图的连线是自己算的三次贝塞尔（用 `bezierAt` 求值）。但如果是现成的 SVG `<path>`，直接用原生 API：

```ts
// 预缓存每条路径的总长，避免每帧重算
const pathLens = links.map(l => l.el.getTotalLength())
// 每帧按进度取点
const pt = link.el.getPointAtLength(pathLens[i] * u)
paintPulse(ctx, pt.x, pt.y, color, Math.sin(u * Math.PI) * 0.9)
```

`getPointAtLength` 内部是查表 + 插值，比每帧解六次贝塞尔方程快，而且不受路径类型限制（折线、弧线、复合路径都行）。代价是每帧一次 DOM 读取，所以**路径长度必须缓存**，不能每帧调 `getTotalLength()`。

### 按层级两段式入场

组织图一层一层铺开，每层都是「先画线、后落节点」：

```ts
// 第一段：连线从满偏移描到 0
gsap.fromTo(links, { strokeDasharray: len, strokeDashoffset: len }, {
  strokeDashoffset: 0, duration: 0.42, ease: EASE.glide, clearProps: 'strokeDasharray,strokeDashoffset',
})
// 第二段：该层节点按 stagger 浮现
gsap.fromTo(nodes, { opacity: 0, y: 6, scale: 0.96 }, {
  opacity: 1, y: 0, scale: 1, duration: 0.4, ease: EASE.reveal,
  stagger: { each: 0.04, from: 'start' }, clearProps: 'opacity,transform',
})
// 层与层之间错开 0.2s
```

线先到、节点后到，读作「先建立关系，再放置实体」。如果同时进行，视觉上会糊成一团。

## 十、生长与级联

背景网络按「层级深度 + 种子」依次蔓延：

```ts
const g = live ? Math.min(1, Math.max(0, (since - 0.4 - (n.depth ?? 1) * 0.3 - seed * 0.3) / 0.8)) : 1
const e = 1 - Math.pow(1 - g, 3)             // easeOutCubic
```

连线随生长从起点伸出（不是整条同时出现）：

```ts
const bx = A.x + (B.x - A.x) * g, by = A.y + (B.y - A.y) * g
ctx.moveTo(A.x, A.y); ctx.lineTo(bx, by)
```

`since` 是舞台启动至令的秒数，`live` 为假时直接 `g = 1`。

## 十一、命中测试

Canvas 画的图形没有原生事件。两条路：

1. **DOM 零尺寸锚点**（推荐）：锚点跟着节点弹簧移动，点它就是了。键盘焦点、`aria-label`、`Tab` 顺序全部免费获得。
2. 纯 Canvas 场景：`elementFromPoint` 或手写距离判断。

方向键在图谱节点间空间导航：

```ts
const dir = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key]
let bestScore = Infinity
for (const other of props.nodes) {
  const dx = other.x - node.x, dy = other.y - node.y
  const along = dx * dir[0] + dy * dir[1]
  if (along <= 4) continue                        // 只考虑该方向上的
  const across = Math.abs(dx * dir[1]) + Math.abs(dy * dir[0])
  const score = along + across * 2.2              // 偏离主轴加权惩罚
  if (score < bestScore) { bestScore = score; best = other }
}
if (best) nodeEls.get(best.id)?.focus()
```

`across * 2.2` 是关键：纯按距离会选到斜对面的节点，加权后优先选正前方的。

## 十二、平移缩放

```ts
function zoomAt(factor, cx?, cy?) {
  const px = cx ?? box.width / 2, py = cy ?? box.height / 2
  const k = Math.min(maxK, Math.max(minK, view.k * factor))
  view.x = px - ((px - view.x) / view.k) * k       // 保持指针下的点不动
  view.y = py - ((py - view.y) / view.k) * k
  view.k = k
}
```

- 以指针为中心缩放的代数：先把指针点换算到世界坐标，再换算回新的屏幕坐标。
- 用 `setPointerCapture` 保证拖拽中指针移出容器不丢事件。
- `exclude` 是字符串选择器（`'.rg-node, .rg-corner'`），`enabled` 是函数（`() => props.pannable`）——两者类型不同，别搞混。
- 渲染路径由各组件自定：关系图用响应式 `transform`（要配合 CSS 过渡），组织画布直接写 `style`。

**`transform-origin` 必须钉在左上角**：

```css
.rg-layer, .org-layer { transform-origin: 0 0 }
```

视口变换是 `translate(view.x, view.y) scale(view.k)`。原点不钉在左上角的话，缩放会绕元素中心发生，`view.x/y` 的数学与视觉对不上——往右拖再放大，内容会往左跳。这是平移缩放层最容易被漏的一行。

**手势容器的两件套 + 一件按需**：

```css
.org-canvas { cursor: grab; touch-action: none; user-select: none }
.org-canvas.is-panning { cursor: grabbing }
.rg.is-pannable { cursor: grab; touch-action: none }
```

`touch-action: none` 和 `cursor` 是必需的（前者阻止触屏滚动抢手势，后者给出可拖拽的暗示）；`user-select: none` 只在「桌面端会框选文字的拖拽区」补——本项目 `.org-canvas` 和看板卡片补了，`.rg.is-pannable` 没补。关系图常驻平移的话建议加上。

### 跟手直写，程序触发才补间

`useViewportPan` 的 `apply(view, animate)` 回调区分两种来源：

```ts
const { view, zoomAt, ... } = useViewportPan({
  el: () => root.value,
  apply: (_v, animate) => apply(animate),
})

let setX: ((v: number) => void) | null = null
function apply(animate = true) {
  const layer = layerEl.value
  if (!layer) return
  if (!animate) {                                   // 拖拽 / 滚轮：严格跟手
    gsap.set(layer, { x: view.x, y: view.y, scale: view.k })
    return
  }
  if (!setX) {                                      // 点缩放按钮 / 重置：平滑过去
    setX = gsap.quickTo(layer, 'x', { duration: 0.55, ease: 'power3.out' })
    setY = gsap.quickTo(layer, 'y', { duration: 0.55, ease: 'power3.out' })
    setK = gsap.quickTo(layer, 'scale', { duration: 0.55, ease: 'power3.out' })
  }
  setX(view.x); setY(view.y); setK(view.k)
}
```

**拖拽必须直写**：任何补间都会让图层滞后于手指，手感立刻变糊。反过来，点「放大」「重置」按钮时如果没有补间，视角会「跳」过去，失去空间连续性。`useViewportPan` 内部已经区分好了（`render(false)` 是手势，`render(true)` 是 `zoomAt` / `reset`），组件只需顺着用。

## 十三、SVG 侧的两个描边技巧

舞台变体把图形画进 Canvas，但浅色变体仍是 SVG。两个只属于描边的技巧：

### 光环画在填充之下：`paint-order: stroke`

```css
.rg-pulse {
  fill: currentColor;
  opacity: 0;
  stroke: var(--pulse-halo);     /* 同色 18% 外圈 */
  stroke-width: 6;               /* 比半径大得多 */
  paint-order: stroke;           /* 关键：先描边、后填充 */
}
```

默认绘制顺序是「填充 → 描边」，描边会压在圆点上，把 6px 的光环画成一张糊住圆点的膜。`paint-order: stroke` 反转顺序：先画 6px 半透明描边，再用纯色填充盖在中间，于是光环只从圆点边缘向外溢出。**不撑大命中区、不遮挡点击**（再加 `pointer-events: none` 双保险），比另画一个 `<circle>` 便宜。

### 加粗即高亮，不碰几何数据

```css
.rg-path { fill: none; stroke: var(--thread); stroke-width: 1.2; stroke-linecap: round;
           transition: stroke .3s, stroke-width .3s }
.rg-link.is-lit .rg-path, .rg-link.is-active .rg-path { stroke: currentColor; stroke-width: 1.6 }
.rg-link.is-dim .rg-path { stroke-opacity: .35 }
```

高亮只把 `stroke-width` 从 1.2 推到 1.6，**完全不改 `d` 属性**。改路径数据要重算贝塞尔、要重排，而改线宽只是重新栅格化一条路径，成本差一个量级。降亮用 `stroke-opacity` 而不是换颜色，主题切换时不用重新取色。

## 十四、暂停与重播

```ts
const paused = ref(false)
function replay() {
  states.clear(); ghosts.value = []
  props.nodes.forEach(n => ensureState(n, performance.now()))
  stageStart = performance.now(); burstAt = performance.now()
  paused.value = false
}
```

舞台上放「重播 / 暂停」两个按钮——常驻动画必须给用户关掉的权利，这既是无障碍也是性能礼让。
