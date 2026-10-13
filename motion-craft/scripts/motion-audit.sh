#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────
# motion-audit.sh — 前端动效系统反模式扫描
#
# 用法:
#   ./motion-audit.sh [项目目录]        # 默认当前目录
#
# 退出码 = 高危类数（0 = 通过），可直接用于 CI 卡点。
#
# 依赖: POSIX sh + grep(--include/--exclude-dir) + find
# 适配: macOS / Linux；只读，不修改任何文件。
#
# ⚠️ 设计纪律: 只收录「误报可接受」的检查。每条都做了防误报处理：
#    - 属性名加边界（stroke-width 不算 width）
#    - 配对类检查按文件比对（有 add 就必须同文件有 remove）
#    - 否定类检查按行排除（有 Math.min 的 devicePixelRatio 不算）
#    宁可漏报，不要误报——误报会训练人忽略整个脚本。
#    机械检测抓不到的（时序、语义、观感）见 references/motion-audit.md。
# ─────────────────────────────────────────────────────────────────────────

set -u

TARGET="${1:-.}"
HIGH=0
WARN=0
NOTE=0
TMP=$(mktemp -d 2>/dev/null || mktemp -d -t motionaudit)
trap 'rm -rf "$TMP"' EXIT INT TERM

if [ ! -d "$TARGET" ]; then
  echo "❌ 目录不存在: $TARGET" >&2
  exit 2
fi

# ── 扫描范围 ────────────────────────────────────────────────────────────
GREP_ARGS="-rnEH"
for d in node_modules dist build .git coverage .next .nuxt .cache out .output; do
  GREP_ARGS="$GREP_ARGS --exclude-dir=$d"
done
for e in ts tsx js jsx mjs cjs vue svelte css scss sass less styl; do
  GREP_ARGS="$GREP_ARGS --include=*.$e"
done

# scan <ERE> → "文件:行号: 内容"（路径相对 TARGET）
scan() {
  # shellcheck disable=SC2086
  grep $GREP_ARGS "$1" "$TARGET" 2>/dev/null | sed "s|^$TARGET/||"
}

# show <级别> <标题> <为什么> <怎么改> <内容> [最多显示条数]
show() {
  _lvl="$1"; _title="$2"; _why="$3"; _fix="$4"; _out="$5"; _max="${6:-10}"
  [ -z "$_out" ] && return 0
  _n=$(printf '%s\n' "$_out" | wc -l | tr -d ' ')
  if [ "$_lvl" = high ]; then
    HIGH=$((HIGH + 1))
    printf '\n\033[41;97m 高危 \033[0m %s\n' "$_title"
  else
    WARN=$((WARN + 1))
    printf '\n\033[43;30m 提醒 \033[0m %s\n' "$_title"
  fi
  printf '      为什么: %s\n' "$_why"
  printf '      怎么改: %s\n' "$_fix"
  printf '      命中 %s 处:\n' "$_n"
  printf '%s\n' "$_out" | head -"$_max" | sed 's/^/        /'
  [ "$_n" -gt "$_max" ] && printf '        …其余 %s 处从略\n' "$((_n - _max))"
}

printf '\n\033[1m🔎 动效反模式扫描: %s\033[0m\n' "$TARGET"

# ═══════════════════════════════════════════════════════════════════════
# 高危
# ═══════════════════════════════════════════════════════════════════════

# ── 1. transition 里过渡布局属性 ────────────────────────────────────────
# 属性名前必须是 行首/空格/{/,，排除 stroke-width / max-width / min-height 之类
LAYOUT_PROPS='(width|height|top|left|right|bottom|margin|padding)'
show high 'transition 里过渡布局属性' \
  '这些属性每帧触发重排（layout），动画必卡，且违反「常驻动画只动 transform/opacity」' \
  '改用 transform / translate / rotate；一次性布局变形（共享元素中介层）例外，但要确认它是廉价实色盒' \
  "$(scan "transition:[^;]*[ {,]${LAYOUT_PROPS}[[:space:]]")"

# ── 2. backdrop-filter 被补间 ───────────────────────────────────────────
show high 'transition / animation 里出现 backdrop-filter' \
  'backdrop-filter 每帧重新栅格化背后全部内容，是最贵的 CSS 属性' \
  '预置一层带模糊的静态玻璃，只补间它的 opacity' \
  "$(scan '(transition|animation):[^;]*backdrop-filter')"

# ── 3-5. 配对类检查（按文件比对，不按行） ────────────────────────────────
# pair <标题> <add模式> <remove模式> <为什么> <怎么改>
pair() {
  _title="$1"; _add="$2"; _rm="$3"; _why="$4"; _fix="$5"
  scan "$_add" | cut -d: -f1 | sort -u > "$TMP/files"
  : > "$TMP/hits"
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    if ! grep -qE "$_rm" "$TARGET/$f" 2>/dev/null; then
      printf '%s\n' "$f" >> "$TMP/hits"
    fi
  done < "$TMP/files"
  [ -s "$TMP/hits" ] || return 0
  HIGH=$((HIGH + 1))
  printf '\n\033[41;97m 高危 \033[0m %s\n' "$_title"
  printf '      为什么: %s\n' "$_why"
  printf '      怎么改: %s\n' "$_fix"
  printf '      以下文件有 add 无 remove（同文件内未找到配对）:\n'
  sed 's/^/        /' "$TMP/hits"
  printf '      ⚠️ 先分清两种情况再动手:\n'
  printf '         · 组件级监听（装在 onMounted / 组件实例里）→ 必须移除\n'
  printf '         · 应用级单例监听（装在 install 函数里、有幂等锁、只装一次）→ 不移除是正确的\n'
  printf '           判据：文件里是否有 pressInstalled / hoverInstalled 这类幂等锁\n'
}

pair 'addEventListener 没有配对的 removeEventListener' \
  '\.addEventListener\(' \
  '\.removeEventListener\(' \
  '监听不移除 → 内存泄漏 + 组件卸载后回调写已销毁的节点' \
  '同一作用域内成对移除；框架里放卸载钩子（onBeforeUnmount / useEffect 清理 / disconnectedCallback）'

pair 'Observer 没有配对 disconnect' \
  'new (ResizeObserver|MutationObserver|IntersectionObserver)' \
  '\.disconnect\(' \
  'Observer 不断开 → 持续触发，且持有被观察元素的引用导致无法回收' \
  'onBeforeUnmount(() => observer?.disconnect())；确认 disconnect 在同一文件出现'

pair 'setInterval 没有配对 clearInterval' \
  'setInterval\(' \
  'clearInterval\(' \
  '定时器不清理 → 组件卸载后仍在跑，且持有闭包' \
  'onBeforeUnmount(() => clearInterval(timer))；确认 clearInterval 在同一文件出现'

# ── 6. offsetParent 做可见性判断 ────────────────────────────────────────
show high '用 offsetParent 判断元素可见性' \
  '规范规定 position: fixed 的元素 offsetParent 恒为 null，浮层内的 fixed 控件会被静默踢出 Tab 循环' \
  '改用 el.getClientRects().length > 0（对 fixed / display:none / 零尺寸都正确）' \
  "$(scan 'offsetParent[[:space:]]*(!==|===|!=|==)')"

# ── 7. 硬编码大额 z-index ───────────────────────────────────────────────
show high '硬编码大额 z-index' \
  '与层级令牌脱节；嵌套浮层会按 DOM 顺序而非打开顺序叠加' \
  '用令牌（--layer-overlay 等）+ 焦点栈动态计算；至少把数值收敛到一处' \
  "$(scan 'z-index:[[:space:]]*([5-9][0-9]{2}|[0-9]{4,})')"

# ── 8. devicePixelRatio 没夹上限（按行排除已夹的） ──────────────────────
show high 'devicePixelRatio 未夹上限' \
  '3x 屏上 9 倍像素，收益极小、成本翻倍' \
  'Math.min(window.devicePixelRatio || 1, 2)' \
  "$(scan 'devicePixelRatio' | grep -v 'Math\.min')"

# ── 9. 帧循环里用 Math.random（只在有帧循环的文件里查） ──────────────────
scan 'createFrameLoop|gsap\.ticker\.add|function[[:space:]]+\w*[Ll]oop|requestAnimationFrame\([^)]*=>' \
  | cut -d: -f1 | sort -u > "$TMP/loopfiles"
if [ -s "$TMP/loopfiles" ]; then
  : > "$TMP/rand"
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    grep -nE 'Math\.random\(\)' "$TARGET/$f" 2>/dev/null | sed "s|^|$f:|" >> "$TMP/rand"
  done < "$TMP/loopfiles"
  show high '帧循环所在文件里用了 Math.random()' \
    '每帧随机 → 节点抖动、长度跳变、级联顺序错乱。注意：生成唯一 id 的用法是合法的' \
    '绘制逻辑改用 id 字符串哈希拿稳定伪随机（同一 id 每帧一致）；仅生成 id 可保留' \
    "$(cat "$TMP/rand" 2>/dev/null)"
fi

# ── 10. GSAP 时间轴位置参数传了裸负数 ───────────────────────────────────
# 合法: '-=0.1'（字符串相对偏移）；非法: 第三参直接给 -0.1
show high 'GSAP 时间轴位置参数可能是裸负数' \
  '位置参数是绝对时间点，传负数会被当 0 或报错；触须/层级的长出顺序会乱' \
  'Math.max(0, 算出来的偏移)。字符串 "-=0.1" 是合法的相对偏移，不要误改' \
  "$(scan '\.(to|from|fromTo|set|add)\([^;]*,[[:space:]]*-[0-9.]')"

# ═══════════════════════════════════════════════════════════════════════
# 提醒：按文件粒度的粗筛，需要人确认
# ═══════════════════════════════════════════════════════════════════════

# ── 11. 模块级可变状态 ──────────────────────────────────────────────────
# 只查 .ts/.js/.mjs/.cjs：.vue 的 <script setup> 顶层 let 是实例级，不是模块级
MOD_ARGS="-rnEH"
for d in node_modules dist build .git coverage .next .nuxt .cache out .output; do
  MOD_ARGS="$MOD_ARGS --exclude-dir=$d"
done
for e in ts tsx js jsx mjs cjs; do
  MOD_ARGS="$MOD_ARGS --include=*.$e"
done
# 排除幂等安装锁与已知合法的单例标志，剩下的才需要人看
# shellcheck disable=SC2086
show warn '模块级可变状态（可能被多实例共享）' \
  '普通模块的模块级变量全应用共享一份；同屏两个实例会互相顶掉响应' \
  '收进组合函数/组件函数体，让每个实例各有一份闭包变量。确需单例的（toast 队列、安装锁）加注释说明' \
  "$(grep $MOD_ARGS '^let[[:space:]]+[a-zA-Z_]+' "$TARGET" 2>/dev/null | sed "s|^$TARGET/||" \
     | grep -vE ':let[[:space:]]+\w*(Installed|Tracked|Ready|Initialized|Loaded|Bound|Listening)')" 8

# ── 12. storage 读写没包 try/catch ──────────────────────────────────────
scan '(localStorage|sessionStorage)\.(get|set|remove)Item' | cut -d: -f1 | sort -u > "$TMP/stfiles"
: > "$TMP/sthits"
while IFS= read -r f; do
  [ -z "$f" ] && continue
  grep -q 'try' "$TARGET/$f" 2>/dev/null || printf '%s\n' "$f" >> "$TMP/sthits"
done < "$TMP/stfiles"
if [ -s "$TMP/sthits" ]; then
  WARN=$((WARN + 1))
  printf '\n\033[43;30m 提醒 \033[0m storage 读写所在文件没有 try/catch\n'
  printf '      为什么: 隐私模式/存储被禁时抛异常，直接白屏\n'
  printf '      怎么改: 包 try/catch，失败走内存兜底\n'
  printf '      以下文件用了 storage 但全文无 try:\n'
  sed 's/^/        /' "$TMP/sthits"
fi

# ── 13. !important：按文件汇总，人工确认是否都在降级块内 ─────────────────
scan '!important' | cut -d: -f1 | sort | uniq -c | sort -rn > "$TMP/imp"
if [ -s "$TMP/imp" ]; then
  WARN=$((WARN + 1))
  printf '\n\033[43;30m 提醒 \033[0m !important 用法（按文件计数）\n'
  printf '      为什么: 除「全局降级」场景外用 !important 会压掉后续所有覆写，主题与密度切换会失效\n'
  printf '      怎么改: 确认每一处都在 prefers-reduced-motion / prefers-contrast / reduced-transparency 块内;\n'
  printf '              在业务选择器里的 !important 一律改成提高特异性或改用令牌\n'
  printf '      以下为各文件命中数（预期只有 base.css 这类全局降级文件出现）:\n'
  awk '{printf "        %-52s %s 处\n", $2, $1}' "$TMP/imp"
fi

# ═══════════════════════════════════════════════════════════════════════
# 能力探测：这个项目有没有该有的东西
# ═══════════════════════════════════════════════════════════════════════

printf '\n\033[1m🧭 能力探测\033[0m\n'

probe() { # probe <标题> <存在模式> <缺失时的说明>
  if scan "$2" | grep -q .; then
    printf '  ✓ %s\n' "$1"
  else
    printf '  － %s\n' "$1"
    printf '      %s\n' "$3"
    NOTE=$((NOTE + 1))
  fi
}

probe '有 prefers-reduced-motion 处理' \
  'prefers-reduced-motion' \
  '减少动态效果的用户会看到全部动画；CSS 与 JS 两侧都要有'
probe '有 reduced-transparency 降级' \
  'prefers-reduced-transparency' \
  '玻璃拟态对低视力用户不友好，需要实色回退'
probe '有统一动效入口（motion.ts / useMotion 等）' \
  '(composables/motion|hooks/useMotion|utils/motion|lib/motion|motion\.ts)' \
  '动效散落在各组件里，改一处手感要改十个地方'
probe '有缓动/时长常量表' \
  '(EASE|easing)[[:space:]]*=[[:space:]]*Object\.freeze|const[[:space:]]+DUR' \
  '没有常量表就会出现魔法数字，全站手感不一致'
probe '有 :focus-visible 焦点环' \
  'focus-visible' \
  '键盘用户看不到焦点位置'
probe '有隐藏/离屏停帧' \
  '(document\.hidden|IntersectionObserver)' \
  '画布离开视口仍在跑，白烧 CPU'
probe '有 @property 注册的可补间变量' \
  '@property' \
  '（未使用；需要补间渐变进度/占比时才需要）'

# ═══════════════════════════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════════════════════════

printf '\n\033[1m📊 汇总\033[0m  高危 %s 类 · 提醒 %s 类 · 能力缺口 %s 项\n' "$HIGH" "$WARN" "$NOTE"

if [ "$HIGH" -gt 0 ]; then
  printf '\033[41;97m ✗ %s 类高危，逐条人确认后修复 \033[0m\n' "$HIGH"
  printf '机械检测只覆盖「高度可疑」；时序、语义与观感问题请配合\n'
  printf 'references/motion-audit.md 的人工审查清单过一遍。\n'
else
  printf '\033[42;30m ✓ 未发现高危反模式 \033[0m\n'
fi

printf '\n'
exit "$HIGH"
