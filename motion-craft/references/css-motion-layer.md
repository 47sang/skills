# CSS 层动效全景

CSS 负责「状态切换」类动效：不需要编排、单元素、可声明式表达。GSAP 负责跨元素编排。两者的边界见 `SKILL.md` 第二节。

## 一、可补间的自定义属性

渐变进度、占比这类值不在可过渡属性列表里。用 `@property` 注册后就能过渡：

```css
/* 必须注册；inherits: false 避免把变量打脏到后代 */
@property --fill { syntax: "<percentage>"; inherits: false; initial-value: 0%; }

.switch-track {
  --fill: 0%;
  background: linear-gradient(90deg, var(--lime) var(--fill), rgba(var(--shade), .14) var(--fill));
  transition: --fill .32s var(--ease-premium);
}
.switch.is-on .switch-track { --fill: 100%; }
```

同一手法适用于：环形进度、占比条、斜线填充的显现、刻度尺当前位置。

**注意**：`@property` 在旧浏览器不支持，需要写静态回退值（把 `--fill` 的兜底直接写成最终态）。

## 二、`@keyframes`：全局只留四种

| 名称 | 用途 | 写法 |
| --- | --- | --- |
| `spin` | 加载中 | `to { transform: rotate(360deg) }` + `linear infinite` |
| `fade-in` | 滑块/浮层首现 | `from { opacity: 0 }` + `both` |
| `pulse` | 骨架屏 | `0%,100% { opacity: 1 } 50% { opacity: .5 }` |
| `toast-count` | 倒计时细环 | `to { stroke-dashoffset: 44 }` + `linear forwards` |

这四种放在 `components.css`，全站共用。模块私有的（呼吸光环、柱体生长、占比条生长）写在各自模块的样式里，不要往全局层堆。

呼吸类常驻动画（如核心盘光环）也走 `@keyframes`，因为它是无限循环、无交互：

```css
.rg-node.is-core .rg-body::before {
  content: ""; position: absolute; inset: -18px; border-radius: 50%; z-index: -1;
  background: radial-gradient(circle closest-side, var(--pulse-halo), transparent);
  animation: rg-breathe 5.5s ease-in-out infinite;
}
@keyframes rg-breathe { 50% { transform: scale(1.12); opacity: .6 } }
```

**周期决定读法**：5.5s 读作「呼吸」，1.4s 读作「等待」，0.7s 读作「忙碌」。别落在 1.4s 和 5.5s 之间——那个区间既不像呼吸也不像等待，看起来像出了故障。

## 三、倒计时环：CSS 动画 + JS 时长

```css
.toast-ring .ring-time {
  stroke: currentColor;
  stroke-dasharray: 44;          /* 2πr，r=7 → 43.98 */
  stroke-dashoffset: 0;
  transform: rotate(-90deg);     /* 从顶部开始 */
  transform-origin: 50% 50%;
  animation: toast-count linear forwards;
}
.toast.is-paused .ring-time { animation-play-state: paused }
@keyframes toast-count { to { stroke-dashoffset: 44 } }
```

时长由 JS 按每条提示的存活时间设置：`:style="{ animationDuration: `${t.duration}ms` }"`。
悬停展开时加 `is-paused` 类即可冻结，与计时器逻辑解耦。

## 四、一个变量驱动整套堆叠

Toast 牌堆用单个 `--depth` 同时驱动四个属性，新增一条只改一个变量：

```css
.toast-slot {
  transform: translateY(calc(var(--depth) * -9px)) scale(calc(1 - var(--depth) * .05));
  opacity: calc(1 - var(--depth) * .28);
  z-index: calc(10 - var(--depth));
  transition: transform .42s var(--ease-premium), opacity .3s ease;
}
.toast-host.is-expanded .toast-slot {
  transform: translateY(calc(var(--depth) * (var(--toast-h) + 8px) * -1));
  opacity: 1;
}
.toast-slot:nth-last-child(n+4) { opacity: 0 }        /* 只露三条 */
.toast-host.is-expanded .toast-slot:nth-last-child(n+4) { opacity: 1 }
```

**关键分工**：位置（牌堆 ↔ 展开）由 CSS 过渡负责，进出场由 GSAP 负责内层卡片，两条通道互不覆盖。

## 五、数字滚动

每一位是一列 0–9 的竖带，用 `transform` 推到目标偏移：

```css
.odo-cell { position: relative; display: inline-block; height: 1em; overflow: hidden }
.odo-strip { display: flex; flex-direction: column; transition: transform .9s var(--ease-premium) }
.odo-strip > span { display: block; height: 1em; line-height: 1; text-align: center }
```

```vue
<span class="odo-strip" :style="{
  transform: `translateY(${-(mounted ? c.digit : 0) * 10}%)`,
  transitionDelay: `${(c.key % 6) * 40}ms`,
}"><span v-for="n in 10" :key="n">{{ n - 1 }}</span></span>
```

0.9s 的时长读作「仪表在读数」，比 0.3s 更有分量。四个实现要点：

- **竖带是 10 个等高 span**，所以每位是条高的 10%，偏移量就是 `-digit * 10%`。
- **位次 key 从右往左编号**（`key: text.length - i`）：99 变 100 时多出一位，个位和十位的 key 不变，Vue 不会重排这两个 cell。从左往右编号会让所有位错位重滚一遍。
- **只有变化的位会滚**：每位是独立的 strip，不变的数字原地不动——比整块数字重播更真实，也更省。
- **`transitionDelay: (c.key % 6) * 40ms`**：高位比低位稍慢，滚动读起来像机械字轮逐级落定，而不是同时跳。

**后台标签页的兜底**：首帧要从 0 滚到目标值，但后台标签页里 `requestAnimationFrame` 不触发，`mounted` 永远为 false，数字会卡在 0：

```ts
onMounted(() => {
  const settle = () => { mounted.value = true }
  if (document.hidden) return settle()
  requestAnimationFrame(settle)
  window.setTimeout(settle, 120)      // rAF 不触发时的兜底
})
```

外层容器给 `role="img"` + `:aria-label="完整文本"`，屏幕阅读器读整个数，不会把「1」「2」「3」逐位念出来。

## 六、`:has()` 做联动高亮

无需 JS 即可实现「悬停一项，其他项降级」：

```css
/* 导航：被指向的那一个更清楚 */
.nav-list:has(.nav-item:hover) .nav-item:not(:hover):not(.is-active) { opacity: .62 }

/* 热力格：悬停十字高亮，其余格子降亮 */
.heat:has(.is-hover) .heat-cell:not(.is-cross) { filter: saturate(.4) opacity(.55) }
```

`filter` 在这里是合理的——它只作用于合成层，不触发重排，且降亮是瞬时状态切换而非补间。

## 七、斜线填充：只承载「范围」语义

```css
--hatch-ink: rgba(var(--shade), .16);
--hatch: repeating-linear-gradient(135deg, var(--hatch-ink) 0 1.5px, transparent 1.5px 6px);
```

用于表示区间、目标、当前柱、慢操作、异常——**只表达「这是一段范围/特殊状态」**，不作装饰。135° 细斜线在两种主题下都成立。

## 八、材质即动效载体

`materials.css` 定义**五个材质类 + 一个指针光**，差别只靠「背景不透明度 + 模糊 + 饱和度 + 白边强度」拉开，不换颜色：

| 类名 | blur | saturate | 用途 |
| --- | --- | --- | --- |
| `m-rail` | 22px | — | 导航轨，几乎实色 |
| `m-pill` | 22px | 1.18 | 高亮玻璃块，白边最亮 |
| `m-float` | 28px | 1.08 | 高层浮层，压住底下一切 |
| `m-surface` | 无 | — | 阅读面，接近实色 |
| `m-groove` | 无 | — | 凹槽，只有一道内高光 |
| `m-glow` | — | — | 容器级指针光（见下） |

`.overlay` 的配方例外地写在 `components.css` 而不是 `materials.css`——它与 `.modal` / `.drawer` 同生命周期，放在一起才找得到：

```css
.overlay { background: var(--overlay); backdrop-filter: blur(3px); -webkit-backdrop-filter: blur(3px) }
```

模糊强度形成一条完整阶梯：阅读面（无）< 遮罩 3px < 轨 22px < 块 22px+饱和 < 浮层 28px。

**「不换颜色」是关键**：四种材质用同一套色相，只改透明度和模糊。换成四种不同颜色，界面立刻从「一套系统」退化成「四块补丁」。

### 让动效有地方发生的视觉底座

动效显得高级，一半靠运动，一半靠它发生的舞台。三样静态元素（都不参与动画）：

```css
/* 1. 深色外框：整页像一块设备屏幕，圆角 38px、10px 深色描边 */
.app-frame { height: calc(100dvh - 16px); border: 10px solid var(--frame); border-radius: 38px;
  background:
    radial-gradient(55% 45% at 92% 0%, var(--ambient-a), transparent 70%),   /* 环境光 A */
    radial-gradient(45% 40% at 20% 100%, var(--ambient-b), transparent 70%), /* 环境光 B */
    var(--canvas);
  box-shadow: 0 24px 70px rgba(17,23,27,.24), 0 3px 12px rgba(17,23,27,.16); }
.stage { padding: 8px; background: var(--stage); overflow: clip }           /* 外圈留白 */
```

| 元素 | 作用 |
| --- | --- |
| 深色外框 + 大圆角 | 给页面一个「物体」的边界，动效在这个边界内发生才有容器感 |
| 两团环境光 | 青柠 / 蓝各一团，极淡（5–7%），位置错开。让大片浅色面不至于死板，同时给玻璃材质提供可折射的内容 |
| 外圈 8px 留白 | 外框不贴屏幕边缘，投影才看得出来 |

环境光必须是**静态**的——它一动，整页的明暗关系就在呼吸，反而干扰真正的动效。透明度压在 7% 以下，深色主题换一组更低的取值。

容器级指针光写在叶子容器上，不写在上层：

```css
.m-glow { --px: 50%; --py: 50%; position: relative; isolation: isolate }
.m-glow > .glow-layer {
  position: absolute; inset: 0; z-index: 0; border-radius: inherit;
  pointer-events: none; opacity: 0;
  background: radial-gradient(circle 120px at var(--px) var(--py),
              rgba(255,255,255,.9), rgba(130,221,45,.08) 42%, transparent 72%);
  mix-blend-mode: screen;
  transition: opacity .28s ease;         /* 只过渡 opacity，不动背景 */
}
@media (hover: hover) { .m-glow:hover > .glow-layer { opacity: .72 } }
```

坐标由 JS 写入（见 `micro-interactions.md`）。深色主题下 `mix-blend-mode` 换成 `normal` 并压低亮度；`pointer: coarse` 与 reduced-motion 下直接 `display: none`。

## 九、颗粒层：静态、不接指针、不混合

```css
.grain-layer {
  position: fixed; inset: 0; z-index: 200; pointer-events: none; opacity: .032;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='matrix' values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-size: 180px 180px;
}
```

作用是打散大面积渐变的色带，消除塑料感。三条纪律：**静态**（不参与动画）、**不接指针**、**不用混合模式**（用混合模式会让整页发灰）。`prefers-contrast: more` 时移除。

**`feColorMatrix` 那 20 个数字是最容易写错的地方**。矩阵按 4 行 × 5 列读（行优先）：

| 行 | 值 | 含义 |
| --- | --- | --- |
| R | `0 0 0 0 0` | 红通道归零 |
| G | `0 0 0 0 0` | 绿通道归零 |
| B | `0 0 0 0 0` | 蓝通道归零 |
| A | `1 0 0 0 0` | **alpha 取噪声的红通道** |

所以输出是「黑色斑点，但每一点的不透明度随噪声变化」——这才是颗粒感。最后一行写成 `0 0 0 0 1`（alpha 恒为 1）会得到一整块不透黑矩形，把页面全糊住。`stitchTiles="stitch"` 让 180px 瓦片在重复时无缝，否则能看到格子边界。

### 深色态的降透明度

```css
@media (prefers-reduced-transparency: reduce) {
  .m-rail, .m-pill, .m-float { backdrop-filter: none; -webkit-backdrop-filter: none }
  .m-float { background: var(--surface-solid) }
  .m-rail  { background: var(--surface-solid) }
}
```

三种玻璃的模糊都被关掉，但只有 `.m-rail` 和 `.m-float` 额外换成实色——`.m-pill` 靠白边和高光就能在实色背景上成立，换背景反而破坏它的层级。**降级不是一律换成同一个值，是按「这个材质靠什么成立」决定。**

### 投影的三层物理隐喻

```css
.brand-mark { box-shadow: 0 1px 3px rgba(14,18,20,.16),      /* 接触：贴平的那一层 */
                            0 6px 16px rgba(14,18,20,.16),      /* 环境：浮起的那一层 */
                            inset 0 1px 0 rgba(255,255,255,.12) } /* 顶部受光边 */
```

一个 34px 的图标底座就把「贴平 / 浮起 / 受光」三件事写全了。这是全站投影的通用配方：`--e1` / `--e2` / `--e3` 是「接触 + 环境」两层的三档刻度，`--edge` 是顶部受光边，两者叠加才是完整的材质。

## 十、令牌工程：六个不显眼但决定质感的模式

### 1. RGB 三元组墨色：一个变量控制全站描边与阴影

```css
:root { --shade: 46, 58, 62 }                                  /* 注意：没有 rgb() 包裹 */
:root { --line: rgba(var(--shade), .085); --line-strong: rgba(var(--shade), .11) }
:root { --e1: 0 1px 2px rgba(var(--shade), .05), 0 5px 14px rgba(var(--shade), .04) }
:root[data-theme="dark"] { --shade: 0, 0, 0 }                  /* 深色态只换三元组 */
```

描边、悬停底、按压底、三层阴影、滚动条——全部写成 `rgba(var(--shade), <alpha>)`。**深色主题切换时只改这一个三元组和若干 alpha，不重写任何选择器**。这是「令牌单一来源」真正落地的手法，比给每个语义色都写一份深色值省一个量级。

同理，Canvas 侧另有一套 `--graph-1` ~ `--graph-paper` 三元组供 `readStagePalette` 读取（见 `canvas-stage.md`）。

### 2. 玻璃上沿高光令牌

```css
--edge: inset 0 1px 0 rgba(255, 255, 255, .92);         /* 浅色态 */
--edge-strong: inset 0 1px 0 rgba(255, 255, 255, .98);
:root[data-theme="dark"] { --edge: inset 0 1px 0 rgba(255, 255, 255, .06) }
```

玻璃材质「受光的上沿」由这对令牌统一控制，深色态从 .92 降到 .06。珍珠玻璃那种「白边强度」的层级感（`m-pill` 最亮、`m-rail` 次之、`m-surface` 最淡）就是靠选哪条 `--edge` 拉开的，不是各自写死颜色。

### 3. 作用域覆写：同一个 token 在不同作用域重定义

```css
:root { --rail-w: 232px }
.app-frame.is-collapsed { --rail-w: 76px }                    /* 折叠态 */
@media (max-width: 1180px) { .app-frame:not(.is-collapsed) { --rail-w: 208px } }
@media (max-width: 820px)  { .app-frame.is-collapsed { --rail-w: 0px } }
```

组件规则（`grid-template-columns: var(--rail-w) minmax(0, 1fr)`）一行不动，布局自动跟着变。**能用 token 覆写解决的，不要写第二条组件规则。** 同理 `--row-h` / `--cell-px` 由密度属性覆写、`--swim-label-w` / `--lane-h` 由紧凑类覆写。

### 2. 恒深面：两种主题下都保持深色

```css
--plate-bg: rgba(21, 24, 26, .9);      /* 规格铭牌、底部浮条 */
--dark-surface: #131619;               /* 深色胶囊按钮、代码块、品牌标记底座 */
```

这类面在浅色态是「深色块」，在深色态还是「深色块」。它们靠 **inset 白边高光**在深底上做出受光边，而不是靠提亮底色：

```css
.spec-plate { box-shadow: var(--e2), inset 0 1px 0 rgba(255, 255, 255, .1) }
```

**别给恒深面写两套配色**——只调 inset 白边的透明度（浅色态 .1、深色态 .06），面本身就是深的。

### 4. 彩色光晕投影阶梯

中性面用 `--e1 → --e2 → --e3` 升档；主操作与危险按钮另有一组带色相的：

```css
--e-accent: 0 1px 2px rgba(20, 66, 148, .28), 0 8px 18px rgba(35, 109, 233, .24);
--e-accent-hover: 0 1px 2px rgba(20, 66, 148, .32), 0 12px 24px rgba(35, 109, 233, .3);
--e-danger: 0 1px 2px rgba(150, 40, 34, .26), 0 8px 18px rgba(255, 90, 80, .24);

.btn-primary { box-shadow: var(--e-accent) }
.btn-primary:hover:not(:disabled) { box-shadow: var(--e-accent-hover) }
```

hover 时**互换预生成的 token**，不在 `:hover` 里现场拼 `box-shadow`。深色态改成「黑底 + 同色相彩色光」双层。规则可以概括成：

- 中性面 hover：`--e1 → --e2 → --e3` 内升一档
- 主操作 hover：`--e-accent → --e-accent-hover` 互换
- 光环（`0 0 0 Npx soft色`）、彩色投射、整框投影属于另一类，单独命名，不参与升降档

### 5. 关掉伪粗体合成

```css
:root { font-synthesis: none }
```

项目大量使用 620 / 650 / 660 / 680 / 720 / 740 这类非整百字重。系统字体没有对应字重时浏览器会**伪粗体合成**，字形发糊、边缘发虚——这是「说不出来但觉得不精致」的高频原因。关掉合成后，浏览器回落到最近的真实字重，字形干净。

配套：字体栈本身也定义在 `:root`（`font-family` 与 `--font-mono` 各一支），不要让组件自己拼字体。

### 6. 外观状态外置到 DOM

**首屏防闪是两层，缺一不可**：

```html
<!-- index.html：在 CSS 之前的内联脚本，直接读 localStorage 写 data-theme -->
<script>
  try {
    const a = JSON.parse(localStorage.getItem('scaffold.appearance') || '{}')
    if (a.theme && a.theme !== 'light') document.documentElement.dataset.theme = a.theme
    if (a.density) document.documentElement.dataset.density = a.density
  } catch {}
</script>
```

```ts
// appearance.ts：挂载后负责同步、跟随系统、持久化
watch(() => [appearance.theme, appearance.density], apply, { immediate: true })
darkQuery.addEventListener('change', () => { if (appearance.theme === 'auto') apply() })
watch(appearance, (v) => { localStorage.setItem(KEY, JSON.stringify(v)) }, { deep: true })
```

内联脚本解决「CSS 加载完到 JS 执行前那一瞬的闪白」，模块解决「之后的跟随系统与持久化」。只做后者的话，深色用户每次刷新都会先白一下。

两个 watch 粒度分开：`apply` 只 watch 决定 DOM 契约的字段（`theme` / `density`），持久化 deep watch 整个对象（含不写进 `dataset` 的 `railCollapsed`）。这样 `apply` 不会因为「折叠导航」这种纯本地状态重跑。

**一个隐蔽的坑**：默认值必须返回副本。

```ts
function load(): Appearance {
  // ...
  return { ...DEFAULTS }        // 不能 return DEFAULTS
}
```

直接返回常量对象的话，`reactive()` 会把它包装并**就地改写**，之后再读 `DEFAULTS` 拿到的是被污染过的值。

## 十一、控件层的细节配方

这些是不写在任何「设计规范」里、但决定了控件是否精致的细节。

### 1. 过渡时长按控件尺寸分档，不按控件类型

```css
/* .15s 密集列表：下拉选项、树行、表格行 */
.select-option { transition: background .15s ease, color .15s ease }
/* .18s 小控件：17px 勾选框 */
.checkbox-box { transition: background .18s ease, border-color .18s ease, box-shadow .18s ease }
/* .2s 标准控件：按钮、图标按钮、分页、 chips */
.btn { transition: color .2s ease, background .2s ease, border-color .2s ease, box-shadow .2s ease }
/* .25s / .3s 大块面：看板列、面板、组织节点 */
.board-col { transition: border-color .25s ease, box-shadow .25s ease, background .25s ease }
.org-node { transition: box-shadow .3s ease, border-color .3s ease, translate .34s var(--ease-premium) }
```

**判据是控件尺寸**：越小的控件过渡越快（按下去要立刻有反应），越大的面越慢（大面积变色太快会闪）。不要按「这是按钮所以 .2s」分类。

### 2. 选中态免跳变：置 `transparent` 而不是删 `border`

```css
.perm-chip { border: 1px solid var(--line-strong); transition: color .2s ease, background .2s ease, border-color .2s ease }
.perm-chip.is-on { color: var(--blue); border-color: transparent; background: var(--blue-soft) }
```

把 `border-color` 置成 `transparent` 而不是 `border: 0`——边框宽度不变，选中瞬间不产生 1px 的布局抖动。同理适用于所有「有边框 ↔ 无边框」的状态切换。

### 3. 零 DOM 的状态点光环

```css
.toast-dot { width: 8px; height: 8px; border-radius: 999px; background: var(--blue) }
.toast.tone-ok .toast-dot { background: var(--lime); box-shadow: 0 0 0 4px var(--lime-soft) }
```

用**纯扩散的 `box-shadow`** 在 6–8px 圆点外做一圈同色光晕，不增加任何 DOM、不增加一次绘制。换语气只换 `currentColor` 和软色变量。这比 `filter: drop-shadow` 便宜，也比画第二个圆点简单。

### 4. 禁用态借用凹槽材质

```css
.input-shell.is-disabled { opacity: .6; background: var(--groove-bg) }
```

「不可用」直接复用凹槽配方，读作「陷下去、按不到」，不新造一种灰色。材质复用比新增材质更能维持系统感。

### 5. 按压时禁文本选择

```css
.btn { user-select: none }
.checkbox, .switch { user-select: none }
.table th.is-sortable { cursor: pointer; user-select: none }
```

不设的话，在按钮上按下并轻微拖动会拖出文字选区，蓝色高亮会盖住按压反馈，手势反馈整个废掉。可排序表头同理。

### 6. 负字距分级收紧

| 场景 | 值 |
| --- | --- |
| 大号显示数字（56px） | `-.045em` |
| 中号数字（28–40px） | `-.035em` |
| 页面标题 | `-.03em` |
| 卡片标题 / 头像 | `-.02em` / `-.015em` |
| 按钮 | `.005em`（微开） |
| 正文 | 不调 |

**只在大号数字和标题级收紧**，正文调负字距会伤害可读性。字号越大，需要的负字距越大——这是排版的基本规律，但很容易被忽略。

### 7. flex 列浮层的滚动修复

```css
.modal { max-height: calc(100dvh - 48px); display: flex; flex-direction: column }
.modal-body { min-height: 0; padding: 14px 22px 20px; overflow-y: auto }
```

两个条件缺一不可：外层限高（数值与 `.overlay` 的 24px 内边距联动），可滚动子项 `min-height: 0`。**flex 子项默认 `min-height: auto`，会被内容撑高**，弹窗直接溢出视口。`dvh` 而不是 `vh`，适配移动端动态视口。

### 8. 占位对齐：`visibility` 而不是 `display`

```css
.tree-toggle.is-leaf { visibility: hidden }
```

叶子行的展开按钮保留 22px 占位但不显示，让叶子行与可展开行的文字左边缘对齐。`display: none` 会移除占位，整列文字错位。

### 9. 偏离 token 必须就地写明理由

```css
/* 小尺寸控件的形状例外：5px 让方框在 17px 上仍读作方框 */
.checkbox-box { border-radius: 5px }
```

圆角五档（8/12/16/20/24）之外，小控件（2–7px）和整屏外框（30px/38px）是尺度外的刻意例外。**例外本身没问题，不写理由的例外才是问题**——三个月后没人知道 5px 是算过的还是随手写的。

## 十二、排版、滚动与响应：另一半「高级感」

动效之外，字与布局的处理决定了同样的动画是「精致」还是「廉价」。

### 1. 字体平滑三件套

```css
body {
  -webkit-font-smoothing: antialiased;    /* WebKit：灰阶抗锯齿，不用次像素 */
  -moz-osx-font-smoothing: grayscale;     /* Firefox macOS 同义 */
  text-rendering: optimizeLegibility;
}
```

项目大量使用 620 / 650 / 680 / 720 这类细字重，还放在半透明玻璃面上。不开灰阶抗锯齿的话，细字重会发糊、深色底上会出彩边——这是「说不出来但觉得不精致」的高频原因。

### 2. 文本收尾：`text-wrap` 与选区色

```css
.page-title { text-wrap: balance }        /* 标题：各行长度均衡，不出现单字行 */
.page-desc  { text-wrap: pretty }         /* 段落：消除末行孤词 */
::selection { background: var(--blue-soft) }   /* 选区色也走令牌，不跳 UA 默认蓝 */
```

`balance` 只用于短标题（浏览器实现有成本，长文本用 `pretty`）。选区色是最容易被漏掉的一处主题破口。

### 3. 断点降级要显式排除用户主动状态

```css
/* 只降级「未折叠」态，把意图写进选择器 */
@media (max-width: 1180px) {
  .app-frame:not(.is-collapsed) { --rail-w: 208px }
}
```

不要依赖 `.is-collapsed` 的特异性偶然胜出。**媒体查询降级的是「屏幕变小了」，用户主动选择的折叠态不该被连带改掉**——这两件事的意图不同，选择器要分开写。

### 4. `clamp()` 与断点是双层响应

```css
.login-title { font-size: clamp(34px, 3.5vw, 58px) }     /* 断点之间连续缩放 */
.login-dial  { width: clamp(200px, 21vw, 300px) }
@media (max-width: 820px) { .page-title { font-size: 22px } }   /* 断点上离散降级 */
```

`clamp()` 负责「平滑」，断点负责「换挡」。只用断点会在 1180px 和 1080px 之间看到字号跳变；只用 `clamp()` 又没法在窄屏上彻底改版式。两者叠加才是完整的响应策略。

### 5. 细滚动条：`padding-box` 让拇指变细

```css
* { scrollbar-width: thin; scrollbar-color: rgba(var(--shade), .18) transparent }
::-webkit-scrollbar { width: 8px; height: 8px }
::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(var(--shade), .16);
  border: 2px solid transparent;         /* 关键 */
  background-clip: padding-box;          /* 背景只画到 padding 内沿 */
}
::-webkit-scrollbar-track { background: transparent }
```

`border: 2px solid transparent` + `background-clip: padding-box` 让 8px 轨道里只露出约 4px 的拇指，且不与轨道粘连。标准属性（`scrollbar-width` / `scrollbar-color`）负责 Firefox，深色主题单独换色。

### 6. 禁用态的不透明度阶梯

```css
.btn:disabled { opacity: .5 }  .icon-btn:disabled { opacity: .45 }
.pg-btn:disabled { opacity: .35 }  .checkbox.is-disabled { opacity: .5 }
.input-shell.is-disabled { opacity: .6 }
```

按「控件本来多重」给不透明度：分页按钮最淡（.35，因为它是辅助操作），输入框最实（.6，因为用户还需要读出里面的值）。统一给 `.5` 会让输入框里的文字也跟着变糊。

### 7. 动态视口单位 `dvh`

```css
body { min-height: 100dvh }
.stage { min-height: 100dvh }
.app-frame { height: calc(100dvh - 16px) }
@media (max-width: 820px) { .app-frame { height: 100dvh } }
```

`vh` 在移动端浏览器工具栏收起时会变（视口高度变了但 `100vh` 不变），整个外壳会突然跳一下。`dvh` 跟着动态视口走，是「外壳不跳」的前提。

### 8. 焦点环内缩，避免被裁

```css
:focus { outline: none }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 3px }
.nav-item:focus-visible { outline-offset: -2px }     /* 导航项内缩 */
```

默认外扩 3px，但导航项有圆角、父级 `overflow: clip`，外扩的环会被切掉一角。这类容器内的可聚焦元素统一用负 offset 把环画到内侧。

## 十三、reduced-motion 降级

CSS 侧一刀切，保留语义、去掉过程：

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    animation-delay: 0s !important;
    transition-duration: .01ms !important;
    transition-delay: 0s !important;
    scroll-behavior: auto !important;
  }
}
```

JS 侧（GSAP、Canvas）不吃这套，必须自己判 `prefersReducedMotion()` 并走 `snap` 分支直写终态，见 `canvas-stage.md`。

**全局兜底已经同时掐掉时长和迭代次数**——无限循环的 `@keyframes` 会被压成「一次 0.01ms 后停止」，不会一直跑。那为什么有些地方还要显式写 `animation: none`？

```css
@media (prefers-reduced-motion: reduce) {
  .rg-node.is-core .rg-body::before { animation: none }
  .ripple-clip, .morph-ghost { display: none }
}
```

两个理由：

1. **`fill-mode: both` 的生长动画会被直接落到终态**，跳过「裁切窗里的初始态」。对 `insight-grow` 这类从 `scaleY(0)` 开始的动画，压成 0.01ms 等于瞬间长满——视觉上仍有一次跳变。
2. **彻底摘掉元素上的动画对象**：补间的创建与销毁、合成层的提升与释放都有成本。常驻动画（呼吸光环、转圈）在减动效下应该一个都不留。

`scroll-behavior: auto !important` 也别忘了——否则命令面板和下拉的 `scrollIntoView`、页面内的平滑滚动在减动效下仍然会滑。

## 十四、入场兜底隐藏

```css
.page:not(.is-entrance-ready) .reveal { opacity: 0 }
.app-frame:not(.is-entrance-ready) .rail-brand,
.app-frame:not(.is-entrance-ready) .nav-group,
.app-frame:not(.is-entrance-ready) .topbar > * { opacity: 0 }
```

GSAP 就绪前元素是隐藏的；时间轴第一步 `tl.add(() => el.classList.add('is-entrance-ready'))` 揭开。这解决了「JS 未执行时元素以终态闪现」的闪烁。
