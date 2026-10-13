/**
 * motion-core.ts — 框架无关的动效核心
 * ───────────────────────────────────────────────────────────────────────
 * 从 motion-craft skill 的范本实现提炼，零框架依赖（只用 GSAP 3）。
 * Vue / React / Svelte / 原生都能用：所有函数收 Element 参数，
 * 不 import 任何框架，不改响应式状态。
 *
 * 落地三步：
 *   1. npm i gsap
 *   2. 把这个文件拷进 src/（或 src/composables/、src/lib/）
 *   3. 入口处 installAll()，用完调它的返回值卸载
 *
 * 相比范本做的三处改进（都是范本里被标记过的缺陷）：
 *   ① install* 返回卸载函数，不用幂等锁——可测试、可热更新、可卸载
 *   ② 每处状态都在闭包里，没有模块级可变状态——同屏多实例不互相顶
 *   ③ transition 钩子的 done 在 out-in 下用 setTimeout 推迟，其余同步
 *
 * 许可提示：GSAP 标准许可对多数场景免费，商用再分发前核对
 * https://gsap.com/community/standard-license/
 */

import { gsap } from 'gsap'
import { Flip } from 'gsap/Flip'

gsap.registerPlugin(Flip)

/* ═══════════════════════════════════════════════════════════════════════
   常量表：缓动只留五种，时长按交互类型分档
   ═══════════════════════════════════════════════════════════════════════ */

export const EASE = Object.freeze({
  reveal: 'expo.out',      // 显现：快出慢收，落点清晰
  glide: 'power4.out',     // 位移滑行：长距离、有重量
  exit: 'power2.in',       // 退场：加速离开
  swap: 'power2.inOut',    // 双向交接：来回对称
  settle: 'back.out(1.6)', // 落定确认：全站唯一允许的过冲
})

export const DUR = Object.freeze({
  press: 0.14,      // 按压：最快，跟随手指
  release: 0.46,    // 回弹
  hoverIn: 0.34,
  hoverOut: 0.42,
  slide: 0.52,      // 玻璃滑块位移
  pageOut: 0.18,
  pageIn: 0.62,
  overlayIn: 0.42,
  overlayOut: 0.2,
})

/* ═══════════════════════════════════════════════════════════════════════
   闸门：减少动态效果 / 页面在后台，都直接给终态
   ═══════════════════════════════════════════════════════════════════════ */

const reducedQuery =
  typeof window !== 'undefined' ? window.matchMedia('(prefers-reduced-motion: reduce)') : null

/** 只回答「用户要不要减少动态」 */
export function prefersReducedMotion(): boolean {
  return Boolean(reducedQuery?.matches)
}

/**
 * 对外总闸门：要减少 **或** 页面在后台。
 * 页面在后台时 rAF 被节流，补间会停在中途，所以此时也跳过。
 */
export function motionSkipped(): boolean {
  return prefersReducedMotion() || (typeof document !== 'undefined' && document.hidden)
}

// 切到后台的那一刻把进行中的补间推到终态；回到前台看到的永远是完成态
if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) return
    // getChildren(nested, tweens, timelines)：false = 不递归取嵌套后代
    gsap.globalTimeline.getChildren(false, true, true).forEach((t) => t.progress(1, false))
  })
}

/** 等两帧合成后再起播：避开 backdrop-filter 首次栅格化那一帧 */
export function afterTwoFrames(fn: () => void): void {
  requestAnimationFrame(() => requestAnimationFrame(fn))
}

/* ═══════════════════════════════════════════════════════════════════════
   帧循环：挂 gsap.ticker，隐藏停帧 + 离屏停帧
   ═══════════════════════════════════════════════════════════════════════ */

export interface FrameLoop {
  /** el 用于离屏检测；不传则只受隐藏门禁 */
  start(el?: Element | null): void
  stop(): void
  /** 立即执行一帧（数据变更 / 减动效时钉到终态） */
  flush(): void
  readonly time: number
}

export function createFrameLoop(step: (dt: number, t: number) => void): FrameLoop {
  let target: Element | null = null
  let offscreen = false
  let frames = 0
  let running = false
  let last = 0
  let time = 0
  let warned = false

  const run = (force: boolean) => {
    if (document.hidden && !force) {
      last = 0
      return
    }
    // 每 20 帧量一次位置：离开视口就停帧（比 IntersectionObserver 不受过渡与隐藏祖先影响）
    if (target && (offscreen || frames++ % 20 === 0)) {
      const r = target.getBoundingClientRect()
      offscreen = r.width === 0 || r.bottom < 0 || r.top > window.innerHeight
    }
    if (offscreen && !force) {
      last = 0
      return
    }
    const now = performance.now()
    // dt 夹在 1/30 内：切标签页回来时 dt 可能是几秒，不夹会让弹簧炸开
    const dt = last ? Math.max(0, Math.min(1 / 30, (now - last) / 1000)) : 1 / 60
    last = now
    time += dt
    try {
      step(dt, time)
    } catch (error) {
      // 单帧出错只报一次，不让整个循环停摆
      if (!warned) {
        warned = true
        console.error(error)
      }
    }
  }

  const tick = () => run(false)

  return {
    start(el) {
      if (running) return
      running = true
      last = 0
      target = el ?? null
      gsap.ticker.add(tick)
    },
    stop() {
      running = false
      gsap.ticker.remove(tick)
      target = null
    },
    flush() {
      run(true)
    },
    get time() {
      return time
    },
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   物理底座：临界阻尼弹簧 + 三次贝塞尔求值
   ═══════════════════════════════════════════════════════════════════════ */

export interface SpringState {
  x: number
  v: number
}

export const springOf = (x: number): SpringState => ({ x, v: 0 })

/**
 * 临界阻尼弹簧：每帧把 state 推向 target，返回新值。
 * k 越大越硬（62 ≈ 0.5s 落定）；c = 2√k 是临界阻尼，不过冲。
 */
export function spring(state: SpringState, target: number, dt: number, k = 62): number {
  const c = 2 * Math.sqrt(k)
  state.v += (-k * (state.x - target) - c * state.v) * dt
  state.x += state.v * dt
  return state.x
}

/** 三次贝塞尔在 u 处的坐标分量 */
export function bezierAt(p0: number, p1: number, p2: number, p3: number, u: number): number {
  const m = 1 - u
  return m * m * m * p0 + 3 * m * m * u * p1 + 3 * m * u * u * p2 + u * u * u * p3
}

/* ═══════════════════════════════════════════════════════════════════════
   指针来处：浮层据此从触发点展开
   ═══════════════════════════════════════════════════════════════════════ */

export const lastPointer = { x: 0, y: 0, at: 0 }

if (typeof document !== 'undefined') {
  document.addEventListener(
    'pointerdown',
    (event) => {
      lastPointer.x = event.clientX
      lastPointer.y = event.clientY
      lastPointer.at = performance.now()
    },
    { capture: true, passive: true },
  )
  // 键盘触发时作废「来处」，回落中心
  document.addEventListener(
    'keydown',
    (event) => {
      if (event.key === 'Enter' || event.key === ' ') lastPointer.at = 0
    },
    { capture: true, passive: true },
  )
}

/** 刚刚（600ms 内）由指针触发的打开动作才有「来处」 */
function recentPointer() {
  return lastPointer.at && performance.now() - lastPointer.at < 600 ? lastPointer : null
}

/** 指针下方匹配选择器的元素（共享元素的「来处」）；键盘触发时为 null */
export function originAtPointer(selector: string): Element | null {
  const point = recentPointer()
  if (!point) return null
  return document.elementFromPoint(point.x, point.y)?.closest(selector) ?? null
}

/** 触发点相对面板的位置，clamp 在面板外扩一圈内，避免从屏幕角落飞入 */
function originOf(panel: Element): string {
  const point = recentPointer()
  if (!point) return '50% 50%'
  const r = panel.getBoundingClientRect()
  const x = Math.min(Math.max(point.x - r.left, -r.width * 0.25), r.width * 1.25)
  const y = Math.min(Math.max(point.y - r.top, -r.height * 0.25), r.height * 1.25)
  return `${x}px ${y}px`
}

/* ═══════════════════════════════════════════════════════════════════════
   微交互：事件委托，新控件命中选择器即获得同一手感
   ═══════════════════════════════════════════════════════════════════════ */

export interface PressOptions {
  /** 命中选择器即获得按压手感 */
  selector?: string
  scale?: number
}

/** 按压反馈。返回卸载函数。 */
export function installPressFeedback(options: PressOptions = {}): () => void {
  if (typeof document === 'undefined') return () => {}
  const SELECTOR =
    options.selector ??
    ['.btn', '.icon-btn', '.nav-item', '.segmented button', '.pg-btn', '.perm-chip'].join(', ')
  const scale = options.scale ?? 0.955
  // pressed 在闭包里：多处安装互不干扰，也避免模块级状态
  const pressed = new Set<Element>()

  const release = () => {
    pressed.forEach((el) =>
      gsap.to(el, { scale: 1, duration: DUR.release, ease: EASE.settle, overwrite: 'auto' }),
    )
    pressed.clear()
  }

  const onDown = (event: PointerEvent) => {
    if (motionSkipped() || event.button !== 0) return
    const el = (event.target as Element | null)?.closest(SELECTOR)
    if (!el || (el as HTMLButtonElement).disabled) return
    pressed.add(el)
    gsap.to(el, { scale, duration: DUR.press, ease: 'power2.out', overwrite: 'auto' })
  }

  document.addEventListener('pointerdown', onDown, { passive: true })
  window.addEventListener('pointerup', release, { passive: true })
  window.addEventListener('pointercancel', release, { passive: true })

  return () => {
    document.removeEventListener('pointerdown', onDown)
    window.removeEventListener('pointerup', release)
    window.removeEventListener('pointercancel', release)
    pressed.clear()
  }
}

export interface HoverLiftOptions {
  selector?: string
  y?: number
}

/**
 * 悬停抬起。只写 y，与按压的 scale 是两条通道，可同时发生不打架。
 * 触屏设备（无 hover 能力）直接不装。
 */
export function installHoverLift(options: HoverLiftOptions = {}): () => void {
  if (typeof document === 'undefined') return () => {}
  if (!window.matchMedia('(hover: hover)').matches) return () => {}
  const SELECTOR = options.selector ?? '.lift'
  const y = options.y ?? -3

  const onOver = (event: PointerEvent) => {
    if (motionSkipped()) return
    const el = (event.target as Element | null)?.closest(SELECTOR)
    // 从卡片内部子元素移入移出不重复触发
    if (!el || el.contains(event.relatedTarget as Node | null)) return
    gsap.to(el, { y, duration: DUR.hoverIn, ease: EASE.glide, overwrite: 'auto' })
  }
  const onOut = (event: PointerEvent) => {
    const el = (event.target as Element | null)?.closest(SELECTOR)
    if (!el || el.contains(event.relatedTarget as Node | null)) return
    gsap.to(el, { y: 0, duration: DUR.hoverOut, ease: EASE.settle, overwrite: 'auto' })
  }

  document.addEventListener('pointerover', onOver)
  document.addEventListener('pointerout', onOut)

  return () => {
    document.removeEventListener('pointerover', onOver)
    document.removeEventListener('pointerout', onOut)
  }
}

export interface RippleOptions {
  selector?: string
}

/**
 * 主按钮涟漪：从真正被点到的位置化开，键盘触发落回中心。
 * 半径取到四角的最大距离，保证铺满。
 */
export function installRipple(options: RippleOptions = {}): () => void {
  if (typeof document === 'undefined') return () => {}
  const SELECTOR = options.selector ?? '.btn-primary, .btn-danger'

  const fire = (button: HTMLElement, x?: number, y?: number) => {
    if (motionSkipped()) return
    const rect = button.getBoundingClientRect()
    const px = x === undefined ? rect.width / 2 : x - rect.left
    const py = y === undefined ? rect.height / 2 : y - rect.top
    const radius = Math.max(
      Math.hypot(px, py),
      Math.hypot(rect.width - px, py),
      Math.hypot(px, rect.height - py),
      Math.hypot(rect.width - px, rect.height - py),
    )

    let clip = button.querySelector<HTMLElement>(':scope > .ripple-clip')
    if (!clip) {
      clip = document.createElement('span')
      clip.className = 'ripple-clip'
      clip.setAttribute('aria-hidden', 'true')
      button.appendChild(clip)
    }
    const dot = document.createElement('span')
    dot.className = 'ripple-dot'
    clip.appendChild(dot)
    gsap.set(dot, { left: px, top: py, xPercent: -50, yPercent: -50, width: 20, height: 20 })
    gsap
      .timeline({ onComplete: () => dot.remove() })
      .to(dot, { scale: (radius * 2.2) / 20, duration: 0.62, ease: EASE.reveal }, 0)
      .to(dot, { opacity: 0, duration: 0.42, ease: 'power1.out' }, 0.2)
  }

  const onDown = (event: PointerEvent) => {
    if (event.button !== 0) return
    const button = (event.target as Element | null)?.closest<HTMLElement>(SELECTOR)
    if (button && !(button as HTMLButtonElement).disabled) fire(button, event.clientX, event.clientY)
  }
  const onKey = (event: KeyboardEvent) => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    const button = (event.target as Element | null)?.closest<HTMLElement>(SELECTOR)
    if (button && !(button as HTMLButtonElement).disabled) fire(button)
  }

  document.addEventListener('pointerdown', onDown, { passive: true })
  document.addEventListener('keydown', onKey)

  return () => {
    document.removeEventListener('pointerdown', onDown)
    document.removeEventListener('keydown', onKey)
  }
}

/**
 * 容器级指针光：坐标写在容器自身（叶子）上，不写在上层。
 * 配套 CSS：
 *   .m-glow > .glow-layer {
 *     background: radial-gradient(circle 120px at var(--px) var(--py),
 *                 rgba(255,255,255,.9), rgba(130,221,45,.08) 42%, transparent 72%);
 *     transition: opacity .28s ease;   ← 只过渡 opacity，不动背景
 *   }
 */
export function trackGlow(event: PointerEvent): void {
  const el = event.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  el.style.setProperty('--px', `${event.clientX - rect.left}px`)
  el.style.setProperty('--py', `${event.clientY - rect.top}px`)
}

/** 一次装齐三个交互，返回总卸载函数 */
export function installAll(): () => void {
  const offs = [installPressFeedback(), installHoverLift(), installRipple()]
  return () => offs.forEach((off) => off())
}

/* ═══════════════════════════════════════════════════════════════════════
   页面切换
   ═══════════════════════════════════════════════════════════════════════ */

/**
 * 离场：退纵深。
 * ⚠️ out-in 模式下必须用 setTimeout 推迟 done——同步调用会让 Vue 在补丁过程中重渲染。
 * 非 out-in 的场景同步 return done() 即可。
 */
export function pageLeave(el: Element, done: () => void): void {
  if (motionSkipped()) {
    setTimeout(done, 0)
    return
  }
  gsap.to(el, { opacity: 0, scale: 0.988, duration: DUR.pageOut, ease: EASE.exit, onComplete: done })
}

/**
 * 进场：推进 + 阅读序显现 + 并列卡片从中间展开。
 * 约定：页面里 `.reveal` 是阅读序元素，`.bento` 是并列卡片。
 * 隐藏态由 CSS 兜底（.page:not(.is-entrance-ready) .reveal { opacity: 0 }）。
 */
export function pageEnter(el: Element, done: () => void): void {
  const page = el as HTMLElement
  if (motionSkipped()) {
    page.classList.add('is-entrance-ready')
    done()
    return
  }
  const items = page.querySelectorAll('.reveal')
  const cards = page.querySelectorAll('.bento')
  // 隐藏态写在时间轴开头的 set 里，内部只用 to 推进
  gsap.set(page, { opacity: 1, scale: 0.994 })
  gsap.set(items, { opacity: 0, y: 12 })
  gsap.set(cards, { opacity: 0, y: 18 })
  page.classList.add('is-entrance-ready')
  const tl = gsap.timeline({
    onComplete: () => {
      gsap.set(page, { clearProps: 'transform' })
      done()
    },
  })
  tl.to(page, { scale: 1, duration: DUR.pageIn, ease: EASE.glide }, 0)
  tl.to(
    items,
    {
      opacity: 1,
      y: 0,
      duration: DUR.pageIn,
      ease: EASE.reveal,
      stagger: { each: 0.05, from: 'start' },
      clearProps: 'transform',
    },
    0.04,
  )
  if (cards.length) {
    tl.to(
      cards,
      {
        opacity: 1,
        y: 0,
        duration: 0.72,
        ease: EASE.reveal,
        stagger: { each: 0.045, from: 'center' },
        clearProps: 'opacity,transform',
      },
      0.1,
    )
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   浮层：弹窗 / 抽屉 / 浮出菜单
   ═══════════════════════════════════════════════════════════════════════ */

export type OverlayKind = 'modal' | 'drawer' | 'pop'

/**
 * 一块独立的玻璃从 from 矩形变形到 to 矩形，结束即移除。
 * x/y 走 transform（合成层）；width/height 仍触发重排，
 * 所以中介层必须是廉价实色盒：无 backdrop-filter、固定圆角。
 */
export function morphGhost(from: DOMRect, to: DOMRect, closing = false): gsap.core.Timeline {
  const ghost = document.createElement('div')
  ghost.className = 'morph-ghost'
  document.body.appendChild(ghost)
  gsap.set(ghost, {
    left: 0,
    top: 0,
    x: from.left,
    y: from.top,
    width: from.width,
    height: from.height,
    opacity: closing ? 1 : 0.9,
  })
  const tl = gsap.timeline({ onComplete: () => ghost.remove() })
  tl.to(
    ghost,
    {
      x: to.left,
      y: to.top,
      width: to.width,
      height: to.height,
      duration: closing ? 0.36 : 0.5,
      ease: closing ? EASE.swap : EASE.glide,
    },
  )
  tl.to(ghost, { opacity: 0, duration: closing ? 0.16 : 0.22, ease: 'power1.out' }, closing ? '-=0.12' : '-=0.18')
  return tl
}

export function overlayEnter(
  el: Element,
  done: () => void,
  kind: OverlayKind = 'modal',
  origin?: Element | null,
): void {
  const panel = el.querySelector('.modal, .drawer') ?? el
  if (motionSkipped()) {
    done()
    return
  }
  const tl = gsap.timeline({ onComplete: done })

  if (kind === 'pop') {
    tl.fromTo(
      el,
      { opacity: 0, y: -6, scale: 0.98 },
      { opacity: 1, y: 0, scale: 1, duration: 0.32, ease: EASE.reveal, clearProps: 'transform' },
    )
    return
  }

  // 遮罩单独一层，与面板并行：遮罩快、面板慢，层次更清楚
  tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 0.22, ease: 'power1.out' }, 0)

  if (kind === 'drawer') {
    // 共享元素：一块玻璃从被点的行生长成抽屉，内容随后显现
    if (origin && document.contains(origin)) {
      const ghost = morphGhost(origin.getBoundingClientRect(), panel.getBoundingClientRect())
      gsap.set(panel, { opacity: 0 })
      tl.add(ghost, 0)
      tl.to(panel, { opacity: 1, duration: 0.26, ease: 'power1.out' }, 0.3)
      tl.fromTo(
        panel.querySelectorAll('.drawer-head, .drawer-body > *, .drawer-foot'),
        { opacity: 0, y: 8 },
        {
          opacity: 1,
          y: 0,
          duration: 0.42,
          ease: EASE.reveal,
          stagger: 0.03,
          clearProps: 'opacity,transform',
        },
        0.34,
      )
      return
    }
    tl.fromTo(
      panel,
      { x: 36, opacity: 0 },
      { x: 0, opacity: 1, duration: DUR.overlayIn + 0.1, ease: EASE.glide, clearProps: 'transform' },
      0,
    )
    return
  }

  gsap.set(panel, { transformOrigin: originOf(panel) })
  const from = recentPointer() ? { scale: 0.86, opacity: 0, y: 0 } : { y: 14, scale: 0.975, opacity: 0 }
  tl.fromTo(
    panel,
    from,
    {
      y: 0,
      scale: 1,
      opacity: 1,
      duration: DUR.overlayIn + 0.06,
      ease: EASE.reveal,
      clearProps: 'transform,transformOrigin',
    },
    0.02,
  )
}

export function overlayLeave(
  el: Element,
  done: () => void,
  kind: OverlayKind = 'modal',
  origin?: Element | null,
): void {
  if (motionSkipped()) {
    done()
    return
  }
  const panel = el.querySelector('.modal, .drawer') ?? el
  const tl = gsap.timeline({ onComplete: done })

  if (kind === 'pop') {
    tl.to(el, { opacity: 0, y: -4, duration: 0.14, ease: EASE.exit })
    return
  }

  if (kind === 'drawer' && origin && document.contains(origin)) {
    // 收回原行（停摆）：内容先退，玻璃再缩回来处
    const ghost = morphGhost(panel.getBoundingClientRect(), origin.getBoundingClientRect(), true)
    tl.to(panel, { opacity: 0, duration: 0.14, ease: EASE.exit }, 0)
    tl.add(ghost, 0.06)
    tl.to(el, { opacity: 0, duration: 0.3, ease: EASE.exit }, 0.08)
    return
  }

  if (kind === 'drawer') tl.to(panel, { x: 24, duration: DUR.overlayOut, ease: EASE.exit }, 0)
  else tl.to(panel, { scale: 0.94, opacity: 0, duration: DUR.overlayOut, ease: EASE.exit }, 0)
  tl.to(el, { opacity: 0, duration: DUR.overlayOut, ease: EASE.exit }, 0)
}

/** 底部浮条：升起用 back.out（落定确认），收回用 power2.in（停摆） */
export function floatBarEnter(el: Element, done: () => void): void {
  if (motionSkipped()) {
    done()
    return
  }
  gsap.fromTo(
    el,
    { y: 40, opacity: 0, scale: 0.96 },
    { y: 0, opacity: 1, scale: 1, duration: 0.56, ease: EASE.settle, clearProps: 'transform', onComplete: done },
  )
}

export function floatBarLeave(el: Element, done: () => void): void {
  if (motionSkipped()) {
    done()
    return
  }
  gsap.to(el, { y: 30, opacity: 0, duration: 0.22, ease: EASE.exit, onComplete: done })
}

/* ═══════════════════════════════════════════════════════════════════════
   群组进场与状态确认
   ═══════════════════════════════════════════════════════════════════════ */

/**
 * 列表行按阅读序显现。
 * slice(0, 14) 是隐性上限：14 行 × 0.025s ≈ 0.35s，落在感知阈值内，用户看不出截断。
 * 超出就让截断点落在感知阈值内，或像「还有 N 项」那样明确告知。
 */
export function revealRows(rows: ArrayLike<Element>): void {
  if (motionSkipped() || !rows.length) return
  const list = Array.from(rows).slice(0, 14)
  gsap.fromTo(
    list,
    { opacity: 0, y: 6 },
    {
      opacity: 1,
      y: 0,
      duration: 0.5,
      ease: EASE.reveal,
      stagger: { each: 0.025, from: 'start' },
      clearProps: 'opacity,transform',
    },
  )
}

/** 面板内容级联浮现：分析栏、抽屉正文等 */
export function revealCascade(
  container: Element | null,
  selector = ':scope > *',
  gap = 0.075,
): void {
  if (!container || motionSkipped()) return
  const items = Array.from(container.querySelectorAll(selector)).slice(0, 18)
  if (!items.length) return
  gsap.fromTo(
    items,
    { opacity: 0, y: 10 },
    {
      opacity: 1,
      y: 0,
      duration: 0.56,
      ease: EASE.reveal,
      stagger: { each: gap, from: 'start' },
      clearProps: 'opacity,transform',
      overwrite: 'auto',
    },
  )
}

/** 状态确认：一次 back.out 的 scale 弹入，不用 opacity 脉冲 */
export function settlePop(el: Element | null): void {
  if (!el || motionSkipped()) return
  gsap.fromTo(el, { scale: 0.6 }, { scale: 1, duration: 0.42, ease: EASE.settle, clearProps: 'transform' })
}

/** 打字机：逐字写出，结束回调 done；减动效时一次写完。返回取消函数（必须调） */
export function typeOut(
  text: string,
  write: (value: string) => void,
  done?: () => void,
  speed = 42,
): () => void {
  if (motionSkipped()) {
    write(text)
    done?.()
    return () => {}
  }
  let i = 0
  write('')
  const timer = window.setInterval(() => {
    i += 1
    write(text.slice(0, i))
    if (i >= text.length) {
      window.clearInterval(timer)
      window.setTimeout(() => done?.(), 180)
    }
  }, speed)
  return () => window.clearInterval(timer)
}

/* ═══════════════════════════════════════════════════════════════════════
   SVG 与布局变形
   ═══════════════════════════════════════════════════════════════════════ */

/** 折线描绘：数据沿路径推进 */
export function drawPath(path: SVGPathElement | null, area?: SVGPathElement | null): void {
  if (!path || motionSkipped()) return
  const length = path.getTotalLength()
  gsap.fromTo(
    path,
    { strokeDasharray: length, strokeDashoffset: length },
    { strokeDashoffset: 0, duration: 1.1, ease: EASE.swap, clearProps: 'strokeDasharray,strokeDashoffset' },
  )
  if (area) gsap.fromTo(area, { opacity: 0 }, { opacity: 1, duration: 0.8, delay: 0.5, ease: 'power1.out' })
}

/**
 * 共享布局变形（Flip）：先记下 targets 的位置，执行 mutate（改 class / 数据并等 DOM 更新），
 * 再从旧位置平滑过渡到新布局。
 */
export async function flipLayout(
  targets: Element[] | NodeListOf<Element>,
  mutate: () => void | Promise<void>,
): Promise<void> {
  const list = Array.from(targets)
  if (motionSkipped() || !list.length) {
    await mutate()
    return
  }
  const state = Flip.getState(list)
  await mutate()
  Flip.from(state, {
    duration: 0.62,
    ease: EASE.glide,
    absolute: false,
    nested: true,
    prune: true,
    simple: true,
  })
}

/* ═══════════════════════════════════════════════════════════════════════
   滑动玻璃滑块
   ═══════════════════════════════════════════════════════════════════════ */

/**
 * 导航选中、分段控件共用一块玻璃。
 * 用几何差值定位：目标与滑块不必是同一个定位父级。
 * ⚠️ 祖先正在缩放时（弹窗从触发点展开），包围盒带着缩放比例，必须折算回布局像素，
 *    否则首帧量到的位置与宽度偏小，滑块错位直到下次切换才纠正。
 */
export function slideThumb(
  thumb: HTMLElement | null,
  target: HTMLElement | null,
  axis: 'x' | 'y',
  instant = false,
): void {
  const parent = thumb?.offsetParent as HTMLElement | null
  if (!thumb || !target || !parent) return
  const pr = parent.getBoundingClientRect()
  const tr = target.getBoundingClientRect()
  const kx = parent.offsetWidth ? pr.width / parent.offsetWidth : 1
  const ky = parent.offsetHeight ? pr.height / parent.offsetHeight : 1
  const props =
    axis === 'y'
      ? { y: (tr.top - pr.top) / ky - parent.clientTop + parent.scrollTop, height: tr.height / ky }
      : { x: (tr.left - pr.left) / kx - parent.clientLeft + parent.scrollLeft, width: tr.width / kx }
  if (instant || motionSkipped()) {
    gsap.set(thumb, props)
    return
  }
  gsap.to(thumb, { ...props, duration: DUR.slide, ease: EASE.glide, overwrite: true })
}

export { gsap }
