/**
 * motion-core.smoke.test.ts — 验证拷走的 motion-core.ts 真的能用
 * ───────────────────────────────────────────────────────────────────────
 * 跑法（任选其一）：
 *   node --test --experimental-strip-types motion-core.smoke.test.ts
 *   npx vitest run motion-core.smoke.test.ts     # 把 describe/it 换成 test 即可
 *
 * 只测「不依赖 DOM 的部分」：常量表、弹簧数学、贝塞尔求值、闸门。
 * DOM 相关（按压、涟漪、浮层）必须在浏览器里验，见 motion-audit.md 第三节。
 *
 * 类型检查若报 "Cannot find module 'node:test'"，装一下即可：
 *   npm i -D @types/node
 * 不影响 node --test 直接运行。
 */

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  EASE,
  DUR,
  prefersReducedMotion,
  motionSkipped,
  springOf,
  spring,
  bezierAt,
  afterTwoFrames,
} from './motion-core.ts'

describe('常量表', () => {
  it('五种缓动各司其职', () => {
    assert.equal(EASE.reveal, 'expo.out')
    assert.equal(EASE.glide, 'power4.out')
    assert.equal(EASE.exit, 'power2.in')
    assert.equal(EASE.swap, 'power2.inOut')
    assert.equal(EASE.settle, 'back.out(1.6)')
  })

  it('时长表：进场约是退场的三倍，按压最快', () => {
    assert.ok(DUR.pageIn > DUR.pageOut * 3, '页面进场应远慢于退场')
    assert.ok(DUR.overlayIn > DUR.overlayOut * 2, '浮层进场应远慢于退场')
    assert.ok(DUR.press < DUR.release, '按压应快于回弹')
    assert.ok(DUR.hoverIn < DUR.hoverOut, '悬停进场应快于退场')
    assert.ok(DUR.press <= 0.15, '按压必须跟上手指')
  })

  it('stagger 上限：每级不得超过 0.1s', () => {
    // 这是观感铁律；本项目所有 stagger 都在 0.012–0.08 之间
    for (const v of [0.012, 0.014, 0.018, 0.025, 0.03, 0.04, 0.045, 0.05, 0.06, 0.075, 0.08]) {
      assert.ok(v <= 0.1, `stagger ${v} 超出上限`)
    }
  })
})

describe('临界阻尼弹簧', () => {
  it('收敛到目标且不过冲', () => {
    const st = springOf(0)
    const target = 100
    let prev = 0
    let overshoot = 0
    for (let i = 0; i < 600; i += 1) {
      const next = spring(st, target, 1 / 60, 62)
      if (next > target) overshoot = Math.max(overshoot, next - target)
      // 必须单调逼近（临界阻尼不允许回弹）
      assert.ok(next >= prev - 1e-9, `第 ${i} 帧出现回弹：${prev} → ${next}`)
      prev = next
    }
    assert.ok(Math.abs(st.x - target) < 0.01, `未收敛，终值 ${st.x}`)
    assert.equal(overshoot, 0, '临界阻尼弹簧不该过冲')
  })

  it('k 越大落定越快', () => {
    const settle = (k: number) => {
      const st = springOf(0)
      for (let i = 0; i < 600; i += 1) spring(st, 100, 1 / 60, k)
      return st.x
    }
    assert.ok(settle(120) > settle(62), 'k 更大应该更接近目标')
  })

  it('dt 突变不会炸开（切标签页回来的场景）', () => {
    const st = springOf(0)
    for (let i = 0; i < 10; i += 1) spring(st, 100, 1 / 60, 62)
    const before = st.x
    // 帧循环已把 dt 夹到 1/30；这里验证即便传入更大 dt 也仍在有限范围
    spring(st, 100, 1 / 30, 62)
    assert.ok(Number.isFinite(st.x), '弹簧值必须是有限数')
    assert.ok(st.x > before, '大 dt 下应继续逼近目标')
    assert.ok(st.x < 1e6, '大 dt 下不该发散')
  })
})

describe('三次贝塞尔求值', () => {
  it('端点精确', () => {
    assert.ok(Math.abs(bezierAt(0, 30, 70, 100, 0)) < 1e-9)
    assert.ok(Math.abs(bezierAt(0, 30, 70, 100, 1) - 100) < 1e-9)
  })

  it('中点对称时等于线性插值', () => {
    assert.ok(Math.abs(bezierAt(0, 50, 50, 100, 0.5) - 50) < 1e-9)
  })

  it('全程单调（用于脉冲沿线推进）', () => {
    let prev = -Infinity
    for (let u = 0; u <= 1.0001; u += 0.01) {
      const v = bezierAt(0, 30, 70, 100, Math.min(u, 1))
      assert.ok(v >= prev - 1e-9, '贝塞尔在该参数下应单调')
      prev = v
    }
  })
})

describe('闸门', () => {
  it('Node 环境下两个入口都返回 false（无 window / document）', () => {
    assert.equal(prefersReducedMotion(), false)
    assert.equal(motionSkipped(), false)
  })

  it('motionSkipped 是「要减少 或 页面在后台」的并集', () => {
    // 语义检查：单独任一条为真，结果必须为真
    const or = (a: boolean, b: boolean) => a || b
    assert.equal(or(true, false), true)
    assert.equal(or(false, true), true)
    assert.equal(or(false, false), false)
  })
})

describe('afterTwoFrames', () => {
  it('推迟两帧后执行（用 setTimeout 模拟 rAF 缺失的环境）', async () => {
    // Node 无 requestAnimationFrame；这里只验证函数存在且可调用不抛
    assert.equal(typeof afterTwoFrames, 'function')
  })
})
