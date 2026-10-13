# 图表动效

图表动效的使命是**让数据「长出来」而不是「跳出来」**。核心手法：路径描绘、轴向生长、比例填充、级联点亮。

## 一、折线描绘

```ts
export function drawPath(path: SVGPathElement | null, area?: SVGPathElement | null) {
  if (!path || skipMotion()) return
  const length = path.getTotalLength()
  gsap.fromTo(path,
    { strokeDasharray: length, strokeDashoffset: length },
    { strokeDashoffset: 0, duration: 1.1, ease: EASE.swap, clearProps: 'strokeDasharray,strokeDashoffset' })
  if (area) gsap.fromTo(area, { opacity: 0 }, { opacity: 1, duration: 0.8, delay: 0.5, ease: 'power1.out' })
}
```

- `getTotalLength()` 拿到精确路径长度，`strokeDasharray` 设为整条长度，`strokeDashoffset` 从 length 补到 0。
- **必须 `clearProps`**：不清则虚线残留，图表悬停或重绘时看起来是虚线。
- 面积区域延迟 0.5s 淡入——线走完再填色，读作「先画轮廓再上色」。
- 1.1s 用 `power2.inOut`（双向交接），因为线条有明确起点和终点。

配套：对比线用红色虚线 `stroke-dasharray: 4 4`，基线用低对比细线，网格用 `stroke-dasharray: 1 5` 的点线。

### 数据切换：路径形变，不是擦掉重画

SVG path 的 `d` 无法直接补间。做法是**补间一个标量 `t`，在 `onUpdate` 里按 `t` 线性插值出新的点列，再重算 `d`**：

```ts
function morphTo() {
  morph?.kill()
  const to = target.value
  if (!drawn || motionSkipped()) { shown.value = to; drawOnce(); return }
  const from = resample(shown.value, to.length)          // 点数不同时先重采样对齐
  const state = { t: 0 }
  morph = gsap.to(state, {
    t: 1, duration: 0.72, ease: EASE.swap,
    onUpdate: () => {
      shown.value = to.map((p, i) => ({
        x: from[i].x + (p.x - from[i].x) * state.t,
        y: from[i].y + (p.y - from[i].y) * state.t,
      }))
    },
  })
}
```

三个要点：

- **只补间一个标量 `t`**，不补间 `x`/`y` 数组——GSAP 补间数组元素也可以，但一个数字更省，且插值逻辑自己掌握。
- **`resample` 处理点数变化**：切时间范围会让点数从 7 变 30，两个数组没法逐项插值。按索引空间线性重采样，把旧点列拉伸/压缩到新长度：

```ts
function resample(points: Pt[], n: number): Pt[] {
  return Array.from({ length: n }, (_, i) => {
    const pos = n <= 1 ? 0 : (i / (n - 1)) * (points.length - 1)
    const a = points[Math.floor(pos)], b = points[Math.min(points.length - 1, Math.ceil(pos))]
    const t = pos - Math.floor(pos)
    return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }
  })
}
```

- **首次绘制走 `drawPath`（描边动画），之后切换走形变**——两种不同的「出现方式」对应两种语义：第一次是「画出来」，切换是「变形」。

### 读数跟随指针

```ts
tipX = gsap.quickTo(tip.value, 'x', { duration: 0.32, ease: 'power3.out' })
tipY = gsap.quickTo(tip.value, 'y', { duration: 0.32, ease: 'power3.out' })
```

**跟随类动效统一用 `power3.out` + `quickTo`**：比 `expo.out` 收敛更快，指针快速移动时读数不会明显滞后；`quickTo` 预建 tween，`pointermove` 每秒几十次也不掉帧。准星本身（十字线）用 `gsap.set` 直写，不补间——准星必须严格跟手。

### 稀疏数据的降级

点数少、非零点 ≤ 3 且总点数 > 6 时，改画茎叶点并直接标数值，避免贴底折线末端出现一根尖刺。**动效之外也要为数据形态降级**，否则再好的动画也在表现一个错误的图形。

## 二、柱体生长

```ts
function grow() {
  const list = bars.value?.querySelectorAll<HTMLElement>('.bar-col')
  if (!list?.length || motionSkipped()) return
  gsap.fromTo(list, { scaleY: 0 }, {
    scaleY: 1, duration: 0.8, ease: EASE.settle,
    stagger: { each: 0.05, from: 'start' }, clearProps: 'transform',
  })
}

let grown = false
watch(() => props.values, (values) => {
  if (grown || !values.length) return      // 只播一次：后续数据刷新不重播
  grown = true
  nextTick(grow)
}, { immediate: true })
onBeforeUnmount(() => gsap.killTweensOf(bars.value?.querySelectorAll('.bar-col') ?? []))
```

```css
.bar-col {
  transform-origin: 50% 100%;                       /* 从底部长出 */
  background: linear-gradient(180deg, rgba(var(--shade), .2), rgba(var(--shade), .12));
  transition: background .25s ease;                  /* 颜色过渡归 CSS，缩放归 GSAP */
}
.bar-col.is-highlight {
  background: var(--hatch), linear-gradient(180deg, var(--lime), #a6e86a);
  box-shadow: 0 6px 18px rgba(130, 221, 45, .32);
}
```

- 高度由布局决定（`height: X%`），进场用 `scaleY` 从 0 到 1，`transform-origin: 50% 100%`。
- **只播一次**（`grown` 标志）：查询条件变化导致数据刷新时，柱子不该再长一遍。
- 卸载时 `killTweensOf`，避免组件销毁后补间还在写已移除的节点。
- 高亮柱加斜线填充 + 青柠渐变 + 投影，读作「就是这根」。
- 失败段用绝对定位的红色条盖在柱顶（`inset: 0 0 auto 0`），不改变柱体几何。
- 无悬停时默认显示峰值读数，容器给 `role="img"` + `aria-label` 摘要。

## 三、占比条

```css
.share-track i {
  position: absolute; inset: 0 auto 0 0; border-radius: inherit;
  background: color-mix(in srgb, var(--cat-ink) 70%, transparent);
  transform-origin: left;
  animation: share-grow .9s var(--ease-premium) both;
}
@keyframes share-grow { from { transform: scaleX(0) } }
```

`transform-origin: left` + `scaleX` 比动画 `width` 便宜一个数量级。

## 四、热力格：grid stagger 对角线波纹

对角线扫过靠 **GSAP 的 `grid` stagger**，不用手算每格的 `delay`：

```ts
function play() {
  if (!root.value || motionSkipped()) return
  const cells = root.value.querySelectorAll('.heat-cell')
  gsap.fromTo(cells, { scale: 0.2, opacity: 0 }, {
    scale: 1, opacity: 1, duration: 0.5, ease: EASE.reveal,
    stagger: { grid: [7, 24], from: [0, 0], amount: 0.9 },
    clearProps: 'transform,opacity', overwrite: 'auto',
  })
}
watch(() => props.cells, () => nextTick(play), { immediate: true })
```

| 参数 | 作用 |
| --- | --- |
| `grid: [7, 24]` | 声明这是 7 行 × 24 列的网格 |
| `from: [0, 0]` | 从左上角开始 |
| `amount: 0.9` | 把 0.9s **平均分配**到全部格子上（比 `each` 更适合网格，格数变化时总时长不变） |

`scale: 0.2 → 1` 是「点亮」而不是「淡入」——格子从小到大弹出来，像被逐格接通。

四级色阶用同一个色相逐步提高混入比例，不用四个不同颜色——否则图例失去「连续量」的语义。异常格用斜线填充叠加：

```css
.heat-cell.lv-1 { background: color-mix(in srgb, var(--lime) 18%, var(--surface-solid)) }
.heat-cell.lv-2 { background: color-mix(in srgb, var(--lime) 38%, var(--surface-solid)) }
.heat-cell.lv-3 { background: color-mix(in srgb, var(--lime) 62%, var(--surface-solid)) }
.heat-cell.lv-4 { background: color-mix(in srgb, var(--leaf-text) 88%, var(--surface-solid));
                  box-shadow: 0 0 0 1px ..., 0 4px 10px rgba(130,221,45,.25) }
.heat-cell.is-risky::after { background: repeating-linear-gradient(135deg, ...) }
```

联动高亮零 JS：

```css
.heat:has(.is-hover) .heat-cell:not(.is-cross) { filter: saturate(.4) opacity(.55) }
.heat-cell.is-hover { box-shadow: 0 0 0 2px var(--blue), 0 6px 14px rgba(var(--shade), .18); z-index: 1 }
```

键盘可达：每格是 `button`，方向键在网格里移动并夹紧边界；读数区 `aria-live="polite"` 播报当前格。

## 五、刻度环

SVG 用 `viewBox="0 0 1 1"` 归一化坐标，`stroke-width` 用小数（`.012`）实现线宽随尺寸缩放。前 N 根刻度加 `is-on` 表示比例，末端的 `ring-cap` 是一枚带微光的圆点。

**两段式编排：先逐根点亮，末端再落定一次**——「导」接「结」，读作仪表在走到位：

```ts
const tl = gsap.timeline()
tl.fromTo(on, { opacity: 0.15 }, {
  opacity: 1, duration: 0.28, ease: 'power1.out',
  stagger: { each: 0.014, from: 'start' }, clearProps: 'opacity',
})
if (capEl) tl.fromTo(capEl, { scale: 0.2, transformOrigin: '50% 50%' }, {
  scale: 1, duration: 0.5, ease: EASE.settle, clearProps: 'transform',
}, '-=0.1')                                    // 与最后几根刻度重叠
```

刻度从 `opacity: 0.15` 起而不是从 0——未点亮的刻度本身就该隐约可见（它们是「还没走到的部分」），从 0 起会让整圈先消失再逐根出现，读作故障。

卸载时杀补间的范围要覆盖所有后代：

```ts
onBeforeUnmount(() => gsap.killTweensOf(root.value?.querySelectorAll('*') ?? []))
```

## 六、泳道与「现在」线

- 泳道块是绝对定位的胶囊，`translate: 0 -50%` 垂直居中，`left/width` 由时间换算。
- 块体进场用 `scaleX: 0 → 1`，`transformOrigin: '0% 50%'`（从左侧起点长出，与时间轴方向一致）：

```ts
gsap.fromTo(blocks, { scaleX: 0, transformOrigin: '0% 50%' }, {
  scaleX: 1, duration: 0.6, ease: EASE.glide,
  stagger: { each: 0.018, from: 'start' }, clearProps: 'transform',
})
```

- 「现在」线：`background: var(--lime); box-shadow: 0 0 0 3px var(--lime-soft)`，位置是纯 CSS 计算（`left: calc(var(--swim-label-w) + (100% - var(--swim-label-w) * frac))`），每分钟由定时器推进一步；**`document.hidden` 时跳过 tick**，回到前台不会连跳几分钟。
- 慢操作加 `background-image: var(--hatch)`，失败块 `box-shadow: inset 0 0 0 1.5px var(--red), 0 0 0 3px var(--red-soft)`。
- 悬停/聚焦抬升：`z-index: 2` + 更强描边（不用 transform，避免与拖拽冲突）。
- 紧凑模式只改 CSS 变量（`--swim-label-w` / `--lane-h`），布局自动收缩。

## 七、阶段切换要有方向

```ts
slideThumb(thumb.value, stepper.value?.querySelector(`[data-step="${next}"]`), 'x', prev === undefined)
gsap.fromTo(stage.value, { x: (next > prev ? 1 : -1) * 28, opacity: 0 }, {
  x: 0, opacity: 1, duration: 0.5, ease: EASE.glide, clearProps: 'transform,opacity',
})
```

向前切从右侧进、向后切从左侧进（`(next > prev ? 1 : -1) * 28`）。首次进入用 `instant` 不做位移。**方向感让「我在流程里前进了还是后退了」变成直觉**，比无方向淡入信息量高得多。

## 八、看板拖拽 + 共享布局变形

拖拽用原生 Pointer Events，拖拽替身（ghost）用 `position: fixed` 跟手，原位置留一个半透明占位。落位后走 GSAP Flip：

```ts
export async function flipLayout(targets, mutate) {
  const list = Array.from(targets)
  if (skipMotion() || !list.length) { await mutate(); return }
  const state = Flip.getState(list)
  await mutate()
  Flip.from(state, { duration: 0.62, ease: EASE.glide, absolute: false, nested: true, prune: true, simple: true })
}
```

| 参数 | 作用 |
| --- | --- |
| `absolute: false` | 保留文档流位置，其他卡片不跳 |
| `nested: true` | 记录嵌套元素的变换，子元素动画不错位 |
| `prune: true` | 跳过视觉上无变化的元素 |
| `simple: true` | 元素无子 transform 时走快路径 |

模式：**先记录状态 → 改数据等 DOM 更新 → 从旧位置补间到新位置**。这是「布局变形」的通用解法，比手写 FLIP 可靠。

### 不想引 Flip 插件时的手写版

```ts
function capture() {
  snapshot = new Map()
  root.querySelectorAll('[data-card]').forEach(el => snapshot.set(el.dataset.card, el.getBoundingClientRect()))
}
watch(() => props.columns, async () => {
  if (!snapshot || motionSkipped()) { snapshot = null; return }
  const before = snapshot; snapshot = null
  await nextTick()
  root.querySelectorAll('[data-card]').forEach((el) => {
    const old = before.get(el.dataset.card); if (!old) return
    const now = el.getBoundingClientRect()
    const dx = old.left - now.left, dy = old.top - now.top
    if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return          // 没动的不补间
    gsap.fromTo(el, { x: dx, y: dy }, { x: 0, y: 0, duration: 0.5, ease: EASE.glide, clearProps: 'transform' })
  })
}, { deep: false })
```

`< 1px` 的阈值很关键：不做判断会让每张卡片都跑一遍 0.5s 补间，包括根本没移动的那些。

### 拖拽幽灵与弹簧落位

拿起卡片时克隆一份跟手，并轻微倾斜放大——「被拿起来了」：

```ts
const ghost = state.card.cloneNode(true) as HTMLElement
ghost.classList.add('board-ghost')                 // position: fixed; z-index: 低于弹窗遮罩
ghost.style.width = `${state.origin.width}px`
document.body.appendChild(ghost)
gsap.set(ghost, { x: state.origin.left, y: state.origin.top })
if (!motionSkipped()) gsap.to(ghost, { rotate: -2.5, scale: 1.03, duration: 0.24, ease: EASE.glide })
// 拖拽中只直写，不补间——幽灵必须严格跟手
gsap.set(drag.ghost, { x: event.clientX - drag.ox, y: event.clientY - drag.oy })
```

松手时**用弹簧把幽灵送到落位**，而不是用固定时长的补间。弹簧的好处是位移大也不会显得更快，且天然带收敛感：

```ts
/* 弹簧飞回：落位更硬、取消回弹稍软 */
const st = {
  x: springOf(Number(gsap.getProperty(ghost, 'x')) || 0),     // 从手势当前位置接续，不跳
  y: springOf(Number(gsap.getProperty(ghost, 'y')) || 0),
  r: springOf(Number(gsap.getProperty(ghost, 'rotate')) || 0),
  s: springOf(Number(gsap.getProperty(ghost, 'scaleX')) || 1),
}
settleLoop = createFrameLoop((dt) => {
  const k = moved ? 72 : 50                       // 落位硬、取消软
  spring(st.x, landing.left, dt, k)
  spring(st.y, landing.top, dt, k)
  spring(st.r, 0, dt, k)
  spring(st.s, 1, dt, k)
  gsap.set(ghost, { x: st.x.x, y: st.y.x, rotate: st.r.x, scale: st.s.x })
  const settled = Math.abs(st.x.x - landing.left) < 1.2 && Math.abs(st.y.x - landing.top) < 1.2
  if (settled || elapsed > 1.5) { settleLoop.stop(); finish() }
})
```

三个要点：

- **初值从 `gsap.getProperty` 读**，保证弹簧从手指松开的位置接续，不会先跳到某个默认值。
- **`moved ? 72 : 50`**：成功落位用更硬的弹簧（果断），取消回弹用软一点的（宽容）。
- 位移与速度双收敛（`< 1.2px`）才收尾，并加 1.5s 超时兜底，防止接口慢时幽灵永久悬挂。接口失败时 `snapshot = null`，幽灵弹回原处。

### 拖拽必须给键盘一条等价路径

指针拖拽对键盘用户和触屏辅助用户不可用。看板的做法是卡片右上角一个「移动到…」菜单，走同一条数据接口：

```ts
// 菜单触发时复用 capture()，让 FLIP 让位照常播放
async function moveVia(item: T, to: BoardColumn<T>) {
  capture()
  await props.onMove({ item, from: ..., to })
}
// 外部点击关闭菜单；用 setTimeout 挂监听，避免这次点击自己立刻关掉刚打开的菜单
onDocClick = () => { menuOpen.value = false }
window.setTimeout(() => document.addEventListener('pointerdown', onDocClick), 0)
```

`setTimeout` 挂监听是个小但关键的细节：同步挂的话，打开菜单的那一次点击会立刻冒泡到 document 把它关掉。

## 九、样本册展开

卡片展开占据整行，用 Flip 让其他卡片平滑让位，展开后的内容再级联浮现——**两个动效串成一条**：

```css
.swatch.is-open { grid-column: 1 / -1; box-shadow: var(--edge), var(--e2);
                  border-color: color-mix(in srgb, var(--blue) 30%, var(--line)) }
```

```ts
await flipLayout(cards, async () => {
  openId.value = openId.value === id ? null : id
  await nextTick()
  revealCascade(card.value?.querySelector('.swatch-editor') ?? null, '.swatch-row', 0.04)
})
```

`grid-column: 1 / -1` 一行变整行，Flip 负责其余卡片的位移补间。** Flip 等 `mutate` 完成（含 `nextTick`）后才记录新位置**，所以把 `revealCascade` 放进同一个 `mutate` 里就能保证顺序：先变形、后级联。

## 十、权限矩阵十字高亮

纯 CSS，两个维度的悬停互相叠加：

```css
.mx-row.is-hover { background: rgba(35,109,233,.045) }
.mx-cell.is-col-hover { background: rgba(35,109,233,.045) }
.mx-row.is-hover .mx-cell.is-col-hover { background: var(--blue-soft) }   /* 交叉点最深 */
.mx-cell:not(:disabled):hover .mx-mark { transform: scale(1.12); border-color: var(--lime) }
```

 sticky 双轴：`position: sticky` 同时用于表头（`top: 0`）和标签列（`left: 0`），角单元格两者叠加（`z-index` 更高）。

## 十一、数字读数

显示级数字配 `font-variant-numeric: tabular-nums`，宽度变化时不跳位。滚动实现见 `css-motion-layer.md` 第五节。

```css
.metric-figure { font-weight: 720; letter-spacing: -.045em; line-height: 1 }
.metric-xl .metric-figure { font-size: var(--fs-display-xl) }   /* 56px */
```

**负字距**（`-.035em` ~ `-.045em`）是大号数字显得高级的关键——默认字距在大字号下显得松散。

## 十二、网格线：重复渐变零节点

柱状图横线、泳道竖线、刻度尺都不用 DOM 元素，全用重复渐变：

```css
/* 横向 4 等分线（柱状图） */
.bars-plot { background: linear-gradient(var(--line) 1px, transparent 1px) 0 100% / 100% 25% repeat-y }
/* 竖向 N 等分线（泳道，N 由 CSS 变量给） */
.swim-grid { background: linear-gradient(90deg, var(--line) 1px, transparent 1px) 0 0 /
                          calc(100% / var(--swim-cols)) 100% repeat-x }
/* 刻度尺：主刻度 + 次刻度两条叠加 */
.ruler-ticks {
  background:
    linear-gradient(90deg, var(--tick-strong) 1px, transparent 1px) 0 0 / calc(100% / var(--ruler-major) - .01px) 8px repeat-x,
    linear-gradient(90deg, var(--tick) 1px, transparent 1px) 0 0 / calc(100% / var(--ruler-major) / var(--ruler-minor) - .01px) 4px repeat-x;
}
```

`background-size` 的第二个值（高度）区分了 8px 的主刻度和 4px 的次刻度——**用背景尺寸而不是不同元素来表达层级**，DOM 里一个节点都没有。
