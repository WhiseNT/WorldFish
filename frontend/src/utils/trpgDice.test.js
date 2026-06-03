import assert from 'node:assert/strict'
import test from 'node:test'
import { parseDiceExpression, rollDiceExpression } from './trpgDice.js'

const fixedRng = (values) => {
  let index = 0
  return () => values[index++ % values.length]
}

test('parseDiceExpression parses simple d20', () => {
  const parsed = parseDiceExpression('d20')
  assert.equal(parsed.expression, 'd20')
  assert.deepEqual(parsed.parts[0], { type: 'dice', raw: 'd20', sign: 1, count: 1, sides: 20 })
})

test('rollDiceExpression supports dice and modifiers', () => {
  const result = rollDiceExpression('2d6+3', { rng: fixedRng([0, 0.5]) })
  assert.equal(result.total, 8)
  assert.deepEqual(result.parts[0].rolls, [1, 4])
  assert.match(result.summary, /2d6\[1,4\]/)
})

test('rollDiceExpression supports multiple dice groups and negative modifiers', () => {
  const result = rollDiceExpression('d20+2d4-1', { rng: fixedRng([0.95, 0, 0.75]) })
  assert.equal(result.total, 24)
  assert.equal(result.parts.length, 3)
})

test('parseDiceExpression rejects invalid expressions', () => {
  assert.throws(() => parseDiceExpression('abc'), /格式错误/)
  assert.throws(() => parseDiceExpression('0d6'), /骰子数量/)
  assert.throws(() => parseDiceExpression('2d1'), /骰面/)
})
