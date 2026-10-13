# 页面切换与浮层

## 一、页面切换

### 接线

```vue
<router-view v-slot="{ Component }">
  <Transition mode="out-in" :css="false" appear
    @leave="pageLeave"
    @enter="pageEnter"
    @after-leave="content?.scrollTo({ top: 0 }); scrolled = false">
    <component :is="Component" :key="route.path" />
  </Transition>
</router-view>
```

| 配置 | 原因 |
| --- | --- |
| `mode="out-in"` | 先播完离场再进场，两页不同时在屏幕上 |
| `:css="false"` | 动效由 JS 钩子驱动，Vue 不等 CSS `transitionend` |
| `appear` | 首屏也走一遍进场 |
| `:key="route.path"` | 同路径参数变化也重建，拿到完整的进场 |

### 离场：退纵深

```ts
export function pageLeave(el: Element, done: () => void) {
  if (skipMotion()) { setTimeout(done, 0); return }        // 必须延后！
  gsap.to(el, { opacity: 0, scale: 0.988, duration: DUR.pageOut, ease: EASE.exit, onComplete: done })
}
```

**`out-in` 模式下同步调用 `done` 会让 Vue 在补丁过程中重渲染**，产生「页面闪一下又动」的问题。两条出路：`setTimeout(done, 0)`，或（有补间时）放进 `onComplete`。

`scale: 0.988` 只缩 1.2%——读作「退到景深里」，不是「缩小没了」。

### 进场：推进 + 阅读序 + 中心展开

```ts
export function pageEnter(el: Element, done: () => void) {
  const page = el as HTMLElement
  if (skipMotion()) { page.classList.add('is-entrance-ready'); return done() }
  const items = page.querySelectorAll('.reveal')
  const cards = page.querySelectorAll('.bento')
  // 隐藏态写在时间轴开头的 set 里，内部只用 to 推进
  gsap.set(page, { opacity: 1, scale: 0.994 })
  gsap.set(items, { opacity: 0, y: 12 })
  gsap.set(cards, { opacity: 0, y: 18 })
  page.classList.add('is-entrance-ready')
  const tl = gsap.timeline({ onComplete: () => { gsap.set(page, { clearProps: 'transform' }); done() } })
  tl.to(page, { scale: 1, duration: DUR.pageIn, ease: EASE.glide }, 0)
  tl.to(items, { opacity: 1, y: 0, duration: DUR.pageIn, ease: EASE.reveal,
    stagger: { each: 0.05, from: 'start' }, clearProps: 'transform' }, 0.04)
  if (cards.length) tl.to(cards, { opacity: 1, y: 0, duration: 0.72, ease: EASE.reveal,
    stagger: { each: 0.045, from: 'center' }, clearProps: 'opacity,transform' }, 0.1)
}
```

- 容器 `scale: 0.994 → 1` 是「推进」，比位移更含蓄。
- `.reveal` 走 `from: 'start'`（阅读序），`.bento` 卡片走 `from: 'center'`（从中间向两侧展开）——并列卡片用中心序读作「一副牌摊开」。
- 全部 `clearProps` 收尾，不在元素上留 `transform` 残值。

### 首屏：不走路由过渡的页面自己写编排

路由过渡只覆盖 `<router-view>` 里的页面。登录页、工作台首屏这类**没有过渡钩子**的页面，自己写开场更合适——因为它们需要完全不同的编排（登录页是「对焦品牌 → 标题逐行 → 能力逐条 → 登录卡交付」，工作台是「卡片从中心弹簧飞出落位」），复用 `pageEnter` 反而受限。

共用的骨架是三件事：

```ts
// 1. 本会话只播一次；刷新不重播，跨会话重播
if (!firstTimeInSession('dashboard') || motionSkipped()) return
// 2. 兜底隐藏由 CSS 负责（.login:not(.is-entrance-ready) .hero-line { opacity: 0 }），
//    时间轴第一步再把 is-entrance-ready 类加上
intro.add(() => el.classList.add('is-entrance-ready'))
// 3. 任意点击或按键 6 倍速快进，而不是硬切
const fastForward = () => intro?.timeScale(6)
window.addEventListener('pointerdown', fastForward, { once: true })
```

`motion.ts` 导出的 `revealPage(page)` 是「给没有过渡钩子的首屏补跑一次 `pageEnter`」的通用兜底，但本项目没有调用点——真实首屏都走了自己的编排。**保留它作为降级路径，别以为首屏动效会自动发生。**

外壳首次入场是单独一套，在 `onMounted` 里手动触发：

```ts
export function playShellEntrance(frame: HTMLElement) {
  const brand = frame.querySelectorAll('.rail-brand')
  const groups = frame.querySelectorAll('.nav-group')
  const top = frame.querySelectorAll('.topbar > *')
  const tl = gsap.timeline({ paused: true })
  tl.set([...brand, ...groups, ...top], { opacity: 0, y: 8 })
  tl.add(() => frame.classList.add('is-entrance-ready'))
  tl.to(brand, { opacity: 1, y: 0, duration: 0.6, ease: EASE.reveal }, 0)
  tl.to(groups, { opacity: 1, y: 0, duration: 0.6, ease: EASE.reveal,
    stagger: { each: 0.06, from: 'start' } }, 0.08)
  tl.to(top, { opacity: 1, y: 0, duration: 0.5, ease: EASE.reveal, stagger: 0.04 }, 0.14)
  tl.add(() => gsap.set([...brand, ...groups, ...top], { clearProps: 'transform' }))
  afterTwoFrames(() => tl.play(0))       // 避开 backdrop-filter 首次栅格化
}
```

顺序 = 品牌 → 导航组 → 顶栏，与视线落点一致。`paused: true` + `afterTwoFrames(() => tl.play(0))` 保证第一帧不掉。

## 二、浮层三类

一套 `overlayEnter` / `overlayLeave` 覆盖弹窗、抽屉、浮出菜单：

```ts
export function overlayEnter(el, done, kind: 'modal' | 'drawer' | 'pop' = 'modal', origin?) {
  const panel = el.querySelector('.modal, .drawer') ?? el
  if (skipMotion()) return done()
  const tl = gsap.timeline({ onComplete: done })
  if (kind === 'pop') {
    tl.fromTo(el, { opacity: 0, y: -6, scale: 0.98 },
                  { opacity: 1, y: 0, scale: 1, duration: 0.32, ease: EASE.reveal, clearProps: 'transform' })
    return
  }
  tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 0.22, ease: 'power1.out' }, 0)   // 遮罩
  if (kind === 'drawer') { /* 见下 */ }
  else {
    gsap.set(panel, { transformOrigin: originOf(panel) })
    const from = recentPointer() ? { scale: 0.86, opacity: 0, y: 0 } : { y: 14, scale: 0.975, opacity: 0 }
    tl.fromTo(panel, from, { y: 0, scale: 1, opacity: 1, duration: 0.48, ease: EASE.reveal,
      clearProps: 'transform,transformOrigin' }, 0.02)
  }
}
```

| 形态 | 进场 | 退场 |
| --- | --- | --- |
| 弹窗 | 从指针点 `scale: 0.86` 展开 | `scale: 0.94` 收拢 |
| 抽屉 | 从被点行 `morphGhost` 生长 / 右侧滑入 | 内容先退，玻璃缩回来处 |
| 浮出菜单 | `y: -6, scale: 0.98` 轻落 | `y: -4` 收起 |

遮罩单独一层 `opacity` 过渡（0.22s），与面板并行——遮罩快、面板慢，层次更清楚。

## 三、共享元素：一块玻璃长成抽屉

来处在打开瞬间用 `document.elementFromPoint` 反查（见 `SKILL.md` 第五节第 6 条），关闭时若该元素仍在页面中就收回原处：

```ts
// 打开
if (origin && document.contains(origin)) {
  const ghost = morphGhost(origin.getBoundingClientRect(), panel.getBoundingClientRect())
  gsap.set(panel, { opacity: 0 })
  tl.add(ghost, 0)
  tl.to(panel, { opacity: 1, duration: 0.26, ease: 'power1.out' }, 0.3)
  tl.fromTo(panel.querySelectorAll('.drawer-head, .drawer-body > *, .drawer-foot'),
    { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.42, ease: EASE.reveal,
      stagger: 0.03, clearProps: 'opacity,transform' }, 0.34)
  return
}
tl.fromTo(panel, { x: 36, opacity: 0 }, { x: 0, opacity: 1, duration: 0.52, ease: EASE.glide, clearProps: 'transform' }, 0)
```

关闭反向：

```ts
if (kind === 'drawer' && origin && document.contains(origin)) {
  const ghost = morphGhost(panel.getBoundingClientRect(), origin.getBoundingClientRect(), true)
  tl.to(panel, { opacity: 0, duration: 0.14, ease: EASE.exit }, 0)
  tl.add(ghost, 0.06)                       // 内容先退，玻璃再缩回
  tl.to(el, { opacity: 0, duration: 0.3, ease: EASE.exit }, 0.08)
  return
}
```

`morphGhost` 实现见 `SKILL.md` 第五节第 6 条。要点：中介层 `position: fixed` + `pointer-events: none`，用 `x`/`y`/`width`/`height` 补间。`x`/`y` 走 `transform`（合成层），`width`/`height` 仍触发重排，所以它必须是一块廉价实色盒（无 `backdrop-filter`、固定圆角），结束即 `remove()`。

## 四、底部浮条

```ts
export function floatBarEnter(el, done) {
  gsap.fromTo(el, { y: 40, opacity: 0, scale: 0.96 },
    { y: 0, opacity: 1, scale: 1, duration: 0.56, ease: EASE.settle, clearProps: 'transform', onComplete: done })
}
export function floatBarLeave(el, done) {
  gsap.to(el, { y: 30, opacity: 0, duration: 0.22, ease: EASE.exit, onComplete: done })
}
```

升起用 `back.out`（落定确认），收回用 `power2.in`（停摆）。批量操作条、未保存变更条、设置差异条共用。

## 五、Toast 牌堆

CSS 负责堆叠位置，GSAP 负责单条进出，两条通道互不覆盖：

```ts
function enter(el: Element, done: () => void) {
  const card = el.querySelector('.toast')
  if (!card || prefersReducedMotion() || document.hidden) return done()
  gsap.fromTo(card, { opacity: 0, y: 16, scale: 0.9 },
    { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: EASE.settle, clearProps: 'transform', onComplete: done })
}
function leave(el: Element, done: () => void) {
  gsap.to(card, { opacity: 0, y: 8, scale: 0.96, duration: 0.2, ease: EASE.exit, onComplete: done })
}
```

配合 `<TransitionGroup :css="false">`。CSS 侧的 `--depth` 驱动见 `css-motion-layer.md` 第四节。

### 倒计时的暂停与恢复

悬停展开时要暂停自动消失，且**剩余时间要接续**，不是重置：

```ts
const timers = new Map<number, { handle: number; endsAt: number; remaining: number }>()

function schedule(id: number, ms: number) {
  timers.set(id, { handle: paused ? 0 : window.setTimeout(() => dismiss(id), ms),
                   endsAt: Date.now() + ms, remaining: ms })
}

export function pauseToasts() {
  if (paused) return
  paused = true
  timers.forEach((timer) => {
    window.clearTimeout(timer.handle)
    timer.remaining = Math.max(0, timer.endsAt - Date.now())   // 记下还剩多久
  })
}

export function resumeToasts() {
  if (!paused) return
  paused = false
  timers.forEach((timer, id) => schedule(id, Math.max(600, timer.remaining)))
}
```

记 `endsAt`（绝对时刻）而不是倒扣剩余：暂停时用 `endsAt - now` 反推剩余，恢复时按剩余重启。`Math.max(600, ...)` 保证刚恢复的提示不会立刻消失。

**两套暂停机制必须同步**：CSS 的倒计时细环用 `animation-play-state: paused`，JS 的自动消失用上面的剩余时间法。两处都要停，否则环走完了提示还在，或者提示没了环还在走。

## 六、焦点管理：栈 + 层级联动

```ts
const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'
const scopes: FocusScope[] = []

function updateLayers() {
  const base = Number.parseInt(getComputedStyle(document.documentElement).getPropertyValue('--layer-overlay')) || 200
  scopes.forEach((scope, index) => {
    const overlay = scope.container.closest<HTMLElement>('.overlay')
    if (overlay) overlay.style.zIndex = String(base + index * 20)
    scope.container.setAttribute('aria-modal', String(index === scopes.length - 1))
  })
}
```

- **栈**：嵌套浮层按打开顺序入栈，`Tab` 只在栈顶循环（`isTop()` 门禁）。
- **关闭后还给触发者**：`activate` 时记 `restoreTo = document.activeElement`，`deactivate` 时若该元素仍在文档中就 `focus({ preventScroll: true })`。
- **层级跟随**：`Teleport to body` 的下拉框脱离了浮层 DOM，用 `floatingLayerFor(anchor)` 读所在 `.overlay` 的 `z-index` 再 +10，保证下拉永远盖在自己的弹窗之上。
- 只有栈顶是 `aria-modal="true"`，屏幕阅读器不会把下层浮层也念成模态。

### 层级秩序

| 层 | z-index | 说明 |
| --- | --- | --- |
| 移动端遮罩 | 105 | 侧栏抽屉背后的压暗 |
| 移动端侧栏 | 110 |  fixed 定位的窄屏导航 |
| 菜单浮层 | 120 | 顶栏用户菜单等独立浮出 |
| 下拉选项 | 宿主 overlay + 10 | 由 `floatingLayerFor` 反查，Teleport 后仍盖在宿主之上 |
| 弹窗 / 抽屉遮罩 | 200 起，每层 +20 | **不是静态值**，由焦点栈在运行期重写 |
| 共享元素中介层 | overlay + 1 | 盖在抽屉自身之上 |
| 颗粒层 | 200 | 与 overlay 同级 |
| 提示牌堆 | 400 | 全站最高 |

两个反直觉的点：

- **overlay 的 z-index 是动态的**：`updateLayers()` 按打开顺序把每个 `.overlay` 的行内 `z-index` 重算为 `--layer-overlay + index * 20`。写死 200 的话，嵌套弹窗会按 DOM 顺序而非打开顺序叠。
- **颗粒层并不盖在弹窗之上**：它与 overlay 同级（200），而 `.overlay` 经 `<Teleport to="body">` 追加到 `body` 末尾，同级下后绘制的盖住先绘制的，所以浮层反而盖住颗粒层。真正稳定压在颗粒之上的是 400 的提示层。若确需颗粒覆盖弹窗，必须显式给更高 z-index。

**`Esc` 只关最顶层**，嵌套弹窗不会一按全关：

```ts
function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape' && trap.isTop()) {
    event.stopImmediatePropagation()      // 阻止按键继续传到外层浮层
    emit('close')
  }
}
```

没有 `stopImmediatePropagation()` 的话，里层浮层的 `keydown` 监听器和外层的同时触发，两个弹窗一起关。

### 焦点陷阱的两个坑

```ts
const items = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE))
  .filter(el => el.offsetParent !== null)
```

- **`offsetParent !== null` 对 `position: fixed` 的元素恒为 `null`**（规范如此）。任何以 `fixed` 定位落在浮层内的可聚焦控件会被静默踢出 Tab 循环，用户永远 Tab 不到它。更稳的判据是 `el.getClientRects().length > 0`，或者补一条 `|| getComputedStyle(el).position === 'fixed'`。
- **只有首焦和还焦必须带 `{ preventScroll: true }`**。Tab 循环回绕处的 `first.focus()` / `last.focus()` 也建议补——在弹窗内最后一个元素上按 Tab，浏览器会把页面滚到那个元素，弹窗里这个跳动特别明显。

### 点当前导航项不重播进场

```ts
function go(path: string) {
  if (route.path !== path) router.push(path)     // 同路径不 push
}
```

不判断的话，点已选中的导航项也会推一次路由，`<Transition>` 拿到新的 key 就重播整页进场——用户会以为页面坏了自己在重复刷新。

## 七、顶栏凝结：只切 opacity

```ts
function onContentScroll() {
  const next = (content.value?.scrollTop ?? 0) > 8
  if (next !== scrolled.value) scrolled.value = next
}
```

```css
.topbar::before {
  content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none; opacity: 0;
  background: var(--rail-bg);
  box-shadow: 0 1px 0 var(--line-strong), 0 10px 26px rgba(var(--shade), .07);
  transition: opacity .3s ease;      /* 只过渡 opacity */
}
.workspace.is-scrolled .topbar::before { opacity: 1 }
```

**绝不补间 `backdrop-filter`**——它每帧都要重新栅格化背后全部内容，是最贵的 CSS 属性之一。做法是预置一层带 `backdrop-filter` 的静态玻璃，只切它的 `opacity`。

## 八、悬停意图：延迟出现 + 宽限离开

```ts
function show(now = false) {
  window.clearTimeout(timer)
  timer = window.setTimeout(async () => {
    open.value = true
    await nextTick(); place()          // 先挂载再量高度，才能决定朝上还是朝下
  }, now ? 0 : props.delay)            // 指针 300ms；键盘聚焦立即
}
function hide() {
  window.clearTimeout(timer)
  timer = window.setTimeout(() => { open.value = false }, 120)   // 宽限 120ms
}
```

三个要点：

- **300ms 延迟**：指针扫过不该触发预览；停下来了才认为「想看」。
- **120ms 宽限**：指针从触发区移向卡片的途中会经过间隙，没有宽限卡片会闪退。
- **键盘 `focusin` 立即显示**（`now = true`）：键盘用户没有「停留」概念，且预览内容常常正是他们需要的信息。
- `Esc` 关闭；`aria-describedby` 只在打开时挂上，`role="tooltip"`。

**必须 `Teleport to="body"` + `position: fixed`**：卡片要避开祖先的 `overflow: hidden` 和 `transform` 容器裁切。挂在触发元素旁边的话，只要任何一个祖先开了 `overflow: clip`（本项目外壳和内容区都开了），卡片就被切掉。样式只负责玻璃与圆角，定位完全由 JS 算。

定位时双向避让：

```ts
const h = card.value?.offsetHeight ?? 120
const below = props.placement === 'bottom'
  ? t.bottom + h + 12 < window.innerHeight      // 默认朝下，放不下就朝上
  : t.top - h - 12 < 0
const left = Math.min(Math.max(t.left + t.width / 2 - width / 2, 12), window.innerWidth - width - 12)
```

`left` 用 `min/max` 夹在视口内 12px——**浮层定位必须做视口夹紧**，否则靠边的元素会让预览卡溢出屏幕。

### 下拉菜单的上下翻转

```ts
function place() {
  const rect = trigger.value?.getBoundingClientRect()
  if (!rect) return
  const menuHeight = menu.value?.offsetHeight ?? 260
  const below = window.innerHeight - rect.bottom
  // 下方空间不够、且上方更宽裕时翻到上面去
  const top = below < menuHeight + 12 && rect.top > menuHeight + 12
    ? rect.top - menuHeight - 6
    : rect.bottom + 6
  const width = Math.max(rect.width, 160)                                    // 不窄于触发器
  const left = Math.min(rect.left, window.innerWidth - width - 8)             // 不溢出右边界
  pos.value = { top, left, width }
}
```

注意 `menu.value?.offsetHeight ?? 260`——菜单还没挂载时用估值先定位，挂载后再量一次修正。

重新定位的挂载点：

```ts
document.addEventListener('pointerdown', onOutside, true)
window.addEventListener('scroll', place, true)      // 捕获阶段：任何祖先容器滚动都能收到
window.addEventListener('resize', place)
onBeforeUnmount(() => hide())                       // 统一在这里移除
```

**`scroll` 必须开捕获阶段**：页面里的滚动容器很多（`.content`、`.table-wrap`、`.select-options` 自身），不开捕获只监听 `window` 的冒泡会漏掉内层滚动，下拉框会浮在错误的位置。这也是「为什么浮层定位总是错」的高频原因。

## 九、移动端侧栏抽屉

```css
.rail { translate: -105% 0; transition: translate .42s var(--ease-premium) }
.app-frame.is-mobile-open .rail { translate: 0 0 }
```

用 `translate` 属性而不是 `transform`，因为它不与其他 transform 用途冲突（导航滑块用 `transform` 走 GSAP）。
