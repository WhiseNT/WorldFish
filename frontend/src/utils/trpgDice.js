const DICE_TERM_PATTERN = /([+-]?)(\d*d\d+|\d+)/gi

const normalizeExpression = (expression = '') => String(expression || '').replace(/\s+/g, '').toLowerCase()

export function parseDiceExpression(expression = '') {
  const normalized = normalizeExpression(expression)
  if (!normalized) {
    throw new Error('请输入骰子表达式')
  }

  const parts = []
  let consumed = ''
  let match
  DICE_TERM_PATTERN.lastIndex = 0

  while ((match = DICE_TERM_PATTERN.exec(normalized)) !== null) {
    const [raw, signText, body] = match
    consumed += raw
    const sign = signText === '-' ? -1 : 1

    if (body.includes('d')) {
      const [countText, sidesText] = body.split('d')
      const count = countText ? Number(countText) : 1
      const sides = Number(sidesText)
      if (!Number.isInteger(count) || count < 1 || count > 100) {
        throw new Error('骰子数量必须在 1 到 100 之间')
      }
      if (!Number.isInteger(sides) || sides < 2 || sides > 10000) {
        throw new Error('骰面必须在 2 到 10000 之间')
      }
      parts.push({ type: 'dice', raw, sign, count, sides })
    } else {
      const value = Number(body)
      if (!Number.isInteger(value) || value < 0 || value > 100000) {
        throw new Error('修正值必须在 0 到 100000 之间')
      }
      parts.push({ type: 'modifier', raw, sign, value })
    }
  }

  if (!parts.length || consumed !== normalized) {
    throw new Error('骰子表达式格式错误，例如 d20、2d6+3、d20+2d4-1')
  }

  return { expression: normalized, parts }
}

export function rollDiceExpression(expression = '', options = {}) {
  const { rng = Math.random } = options
  const parsed = parseDiceExpression(expression)
  let total = 0

  const parts = parsed.parts.map(part => {
    if (part.type === 'modifier') {
      const value = part.sign * part.value
      total += value
      return { ...part, total: value }
    }

    const rolls = Array.from({ length: part.count }, () => Math.floor(rng() * part.sides) + 1)
    const rawTotal = rolls.reduce((sum, value) => sum + value, 0)
    const signedTotal = part.sign * rawTotal
    total += signedTotal
    return { ...part, rolls, rawTotal, total: signedTotal }
  })

  return {
    expression: parsed.expression,
    parts,
    total,
    summary: formatRollResult({ expression: parsed.expression, parts, total }),
  }
}

export function formatRollResult(result = {}) {
  const details = (result.parts || []).map(part => {
    const prefix = part.sign < 0 ? '-' : '+'
    if (part.type === 'modifier') {
      return `${prefix}${part.value}`
    }
    const diceText = `${part.count}d${part.sides}`
    return `${prefix}${diceText}[${(part.rolls || []).join(',')}]`
  })
  const normalizedDetails = details.join(' ').replace(/^\+/, '')
  return `${result.expression || 'roll'} => ${normalizedDetails} = ${result.total ?? 0}`
}
