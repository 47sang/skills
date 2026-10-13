# 移植清单

把动效系统搬到另一个项目（或另一个框架）时的对照表与最小可用实现。

## 一、框架对照

| 范本做法 | React | 原生 / 其他 |
| --- | --- | --- |
| `<Transition :css="false" @enter>` | `react-transition-group` 的 `addEndListener`，或自写挂载/卸载钩子 | `Web Animations API` + `element.animate()` |
| `composables/motion.ts` 单例 | 一个 `motion.ts` 模块 + `useMotion()` hook | 一个 ES module，导出函数 |
| `watch(() => props.nodes, ...)` | `useEffect(() => {...}, [nodes])` | 数据变更后手动调 `loop.flush()` |
| `onBeforeUnmount(() => loop.stop())` | `useEffect` 的清理函数 | `disconnectedCallback` |
| `ref` + 模板 ref | `useRef` | `querySelector` / `element.refs` |
| Teleport 到 body | `createPortal` | `document.body.appendChild` |

**不变的部分**：GSAP 调用、Canvas 绘制、弹簧数学、CSS 层全部原样可用。动效系统的九成与框架无关。

## 二、最快的落地路径：直接拷走核心

不想从零搭，就拿 `assets/motion-core.ts`——框架无关、只用 GSAP，已过严格模式类型检查和 12 项冒烟测试：

```bash
cp assets/motion-core.ts            <你的项目>/src/composables/   # 或 src/lib/
cp assets/motion-core.smoke.test.ts <同目录>/
cd <你的项目> && npm i gsap
node --test --experimental-strip-types src/composables/motion-core.smoke.test.ts   # 先验证落地成功
```

入口处装配，用完卸载：

```ts
import { installAll } from './composables/motion-core'

const uninstall = installAll()     // 按压 + 悬停 + 涟漪
// 需要时：uninstall()
```

它比范本多三处改进，都是范本里被标记过的缺陷：① `install*` 返回卸载函数而非幂等锁；② 状态全在闭包里，没有模块级可变状态；③ `done` 回调按 `out-in` 与否区分同步/异步。

**然后**：CSS 层照 `references/css-motion-layer.md` 第八~十四节配（材质、令牌、reduced-motion 兜底），页面过渡接 `pageLeave` / `pageEnter`，最后跑一遍 `scripts/motion-audit.sh` 看能力缺口。

## 三、从零实现（想自己写的再看这节）

按此顺序落地，每一步都能独立验证：

### 第 1 步：常量与闸门

```ts
import { gsap } from 'gsap'

export const EASE = Object.freeze({
  reveal: 'expo.out', glide: 'power4.out', exit: 'power2.in',
  swap: 'power2.inOut', settle: 'back.out(1.6)',
})
export const DUR = Object.freeze({
  press: 0.14, release: 0.46, hoverIn: 0.34, hoverOut: 0.42,
  slide: 0.52, pageOut: 0.18, pageIn: 0.62, overlayIn: 0.42, overlayOut: 0.2,
})

const reducedQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
export const prefersReducedMotion = () => reducedQuery.matches
export function motionSkipped() {
  return prefersReducedMotion() || document.hidden
}
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) return
  gsap.globalTimeline.getChildren(false, true, true).forEach(t => t.progress(1, false))
})

// 把 gsap 实例本身从唯一入口转发：页面连裸 gsap.set 都从这里导入
export { gsap }
```

**验证**：在系统设置里打开「减弱动态效果」，所有动效应立即跳到终态；把标签页切走再切回，不应有动画停在中途。

### 第 2 步：CSS 兜底与预隐藏

```css
/* 兜底隐藏：JS 未执行时元素不以终态闪现 */
.page:not(.is-entrance-ready) .reveal { opacity: 0 }

/* 预隐藏：由 JS 延迟定位的单个元素，先用 CSS 按住 */
@keyframes fade-in { from { opacity: 0 } }
.nav-thumb, .seg-thumb { animation: fade-in .24s ease both }

/* 全局 reduced-motion 一刀切 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important; animation-iteration-count: 1 !important;
    animation-delay: 0s !important; transition-duration: .01ms !important;
    transition-delay: 0s !important; scroll-behavior: auto !important;
  }
}
```

### 第 3 步：帧循环

```ts
export function createFrameLoop(step: (dt: number, t: number) => void) {
  let target: Element | null = null, offscreen = false, frames = 0
  let running = false, last = 0, time = 0, warned = false
  const run = (force: boolean) => {
    if (document.hidden && !force) { last = 0; return }
    if (target && (offscreen || frames++ % 20 === 0)) {
      const r = target.getBoundingClientRect()
      offscreen = r.width === 0 || r.bottom < 0 || r.top > window.innerHeight
    }
    if (offscreen && !force) { last = 0; return }
    const now = performance.now()
    const dt = last ? Math.max(0, Math.min(1 / 30, (now - last) / 1000)) : 1 / 60
    last = now; time += dt
    try { step(dt, time) } catch (e) { if (!warned) { warned = true; console.error(e) } }
  }
  const tick = () => run(false)
  return {
    start(el) { if (running) return; running = true; last = 0; target = el ?? null; gsap.ticker.add(tick) },
    stop() { running = false; gsap.ticker.remove(tick); target = null },
    flush() { run(true) },
    get time() { return time },
  }
}
```

**验证**：打开性能面板，滚动页面让画布离开视口，帧率应回到空闲水平；切标签页 10 秒再回来，弹簧不应炸开。

### 第 4 步：微交互（事件委托）

```ts
const PRESSABLE = '.btn, .icon-btn, .nav-item'
export function installPressFeedback() {
  if (window.matchMedia('(hover: hover)').matches === false) return
  const pressed = new Set<Element>()
  const release = () => {
    pressed.forEach(el => gsap.to(el, { scale: 1, duration: DUR.release, ease: EASE.settle, overwrite: 'auto' }))
    pressed.clear()
  }
  document.addEventListener('pointerdown', (e) => {
    if (motionSkipped() || e.button !== 0) return
    const el = (e.target as Element)?.closest(PRESSABLE)
    if (!el || (el as HTMLButtonElement).disabled) return
    pressed.add(el)
    gsap.to(el, { scale: 0.955, duration: DUR.press, ease: 'power2.out', overwrite: 'auto' })
  }, { passive: true })
  window.addEventListener('pointerup', release, { passive: true })
  window.addEventListener('pointercancel', release, { passive: true })
}
```

**验证**：按住按钮拖到外面松手，按钮应回弹；右键点击不应有缩放。

### 第 5 步：`@property` 注册可补间变量

```css
@property --fill { syntax: "<percentage>"; inherits: false; initial-value: 0% }
.switch-track { background: linear-gradient(90deg, var(--lime) var(--fill), rgba(0,0,0,.14) var(--fill));
                transition: --fill .32s cubic-bezier(.16,1,.3,1) }
.switch.is-on .switch-track { --fill: 100% }
```

不注册的自定义属性不可过渡。`inherits: false` 避免把变量打脏到后代。

### 第 6 步：按需加模式

| 需要 | 抄哪一节 |
| --- | --- |
| 页面切换 | `page-and-overlay.md` 第一节 |
| 弹窗 / 抽屉 | `page-and-overlay.md` 第二、三节 |
| Canvas 图谱 | `canvas-stage.md` 全篇 |
| 图表生长 | `chart-motion.md` 第一、二、三节 |
| Toast 堆叠 | `css-motion-layer.md` 第四节 |
| 玻璃质感 | `css-motion-layer.md` 第八、九、十节 |

## 四、检查清单

上线前逐条过：

**正确性**
- [ ] 所有动效在写补间前都过了 `motionSkipped()` 双闸门，且闸门分支显式给终态
- [ ] 会复用的节点补间结束有 `clearProps`（补间完就卸载的可以不写）
- [ ] 弹窗 `@leave` 的 `done` 回调在 `out-in` 模式下用 `setTimeout(done, 0)` 推迟

**性能**
- [ ] 常驻动画只写 `transform` / `opacity`
- [ ] 没有补间 `backdrop-filter`（它每帧重新栅格化背后全部内容）
- [ ] Canvas DPR 上限 2，尺寸不变时不重设 `canvas.width`
- [ ] 每帧不创建新对象 / 新 tween / 新闭包
- [ ] 响应式状态不在帧循环里改（用 `ref` 直写 style）
- [ ] 卸载时 `loop.stop()` + `gsap.killTweensOf(...)` + 断开 Observer + 移除监听，四件事都做
- [ ] `{ passive: true }` 只加在不 `preventDefault` 的高频监听上；`wheel` 用 `{ passive: false }`
- [ ] 高频跟随用 `gsap.quickTo()` 预建，拖拽跟手用 `gsap.set` 直写
- [ ] GSAP 时间轴位置参数传的是绝对时间点，算出来的偏移要 `Math.max(0, ...)`

**无障碍**
- [ ] 打开「减弱动态效果」后全部直接到终态，功能不缺失
- [ ] 键盘能触发所有交互，且键盘触发时动效有合理回落（如涟漪从中心化开）
- [ ] 焦点环只有一种颜色，`:focus-visible` 覆盖所有可交互元素
- [ ] 状态不只靠颜色区分，有文字或图标
- [ ] 常驻动画有关闭开关（暂停/重播）
- [ ] `prefers-reduced-transparency: reduce` 下有实色回退

**观感**
- [ ] 时长只在常量表里取，没有散落的魔法数字
- [ ] 进场约是退场的三倍
- [ ] `stagger` 每级 ≤ 0.08s
- [ ] 每段动效说得出口属于哪种能量语态

## 五、依赖说明

范本使用 GSAP 3（`gsap` + `gsap/Flip`）。GSAP 标准许可对大多数场景免费，但商用再分发前需核对 [GSAP 许可条款](https://gsap.com/community/standard-license/)。

若不引第三方库，可替换的部分：

| GSAP 能力 | 原生替代 |
| --- | --- |
| `gsap.to/fromTo` + 时间轴 | Web Animations API `element.animate()` + `Animation` 队列 |
| `gsap.ticker` | 自建 `requestAnimationFrame` 循环 |
| `gsap.set` | 直写 `element.style` |
| `Flip.from` | 手写 FLIP：记录 `getBoundingClientRect()` → 改 DOM → 用 `transform` 从旧位置补间 |
| `gsap.quickTo` | 缓存一个 `Animation` 实例反复改 `currentTime` / 关键帧值 |
| 缓动字符串 | `cubic-bezier()` 参数（`expo.out` ≈ `cubic-bezier(.16,1,.3,1)`） |

**原生方案要多写的部分**：时间轴编排（`delay` / 重叠）、`overwrite` 语义、`stagger` 计算。建议先用 GSAP 把动效逻辑跑通，再按需替换。
