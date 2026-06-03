const DEFAULT_EXPORT_OPTIONS = {
  includeOverview: true,
  includeEntities: true,
  includeEvents: true,
  includeSettings: true,
  includeStages: true,
  includeRelationships: true,
  includeAliases: true,
  constantOverview: true,
  defaultDepth: 4,
}

const CATEGORY_LABELS = {
  character: '人物',
  organization: '组织',
  geography: '地理',
  item: '物品',
  ability: '能力',
  other: '其他',
}

const normalizeText = (value = '') => String(value ?? '').trim()

const normalizeList = (value) => {
  if (Array.isArray(value)) {
    return value.map(item => normalizeText(item)).filter(Boolean)
  }
  if (typeof value === 'string') {
    return value
      .split(/[、,，/|]/)
      .map(item => item.trim())
      .filter(Boolean)
  }
  return []
}

const dedupe = (values = []) => {
  const seen = new Set()
  const result = []
  values.forEach(value => {
    const text = normalizeText(value)
    const key = text.toLowerCase().replace(/\s+/g, '')
    if (!text || seen.has(key)) return
    seen.add(key)
    result.push(text)
  })
  return result
}

const formatValue = (value) => {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return normalizeText(value)
  }
  if (Array.isArray(value)) {
    return value
      .map(item => formatValue(item))
      .filter(Boolean)
      .join('；')
  }
  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([key, val]) => {
        const formatted = formatValue(val)
        return formatted ? `${key}: ${formatted}` : ''
      })
      .filter(Boolean)
      .join('；')
  }
  return normalizeText(value)
}

const pushLine = (lines, label, value) => {
  const text = formatValue(value)
  if (text) lines.push(`${label}: ${text}`)
}

const createEntry = ({ uid, keys, comment, content, constant = false, order = 100, position = 0, depth = 4 }) => ({
  uid,
  key: dedupe(keys),
  keysecondary: [],
  comment: normalizeText(comment),
  content: normalizeText(content),
  constant: Boolean(constant),
  selective: false,
  selectiveLogic: 0,
  addMemo: true,
  order,
  position,
  disable: false,
  excludeRecursion: false,
  preventRecursion: false,
  delayUntilRecursion: false,
  probability: 100,
  useProbability: false,
  depth,
  group: '',
  groupOverride: false,
  groupWeight: 100,
  scanDepth: null,
  caseSensitive: false,
  matchWholeWords: false,
  useGroupScoring: false,
  automationId: '',
  role: 0,
  vectorized: false,
  sticky: 0,
  cooldown: 0,
  delay: 0,
  displayIndex: uid,
})

const buildOverviewEntry = (world, options, uid) => {
  const lines = []
  lines.push(`世界观: ${normalizeText(world.name) || '未命名世界观'}`)
  pushLine(lines, '时代背景', world.era)
  pushLine(lines, '锚定时间', world.anchor_time)
  pushLine(lines, '简介', world.description)
  pushLine(lines, '文风', world.writing_style)
  pushLine(lines, '参考文本', world.reference_text)

  return createEntry({
    uid,
    keys: [world.name, world.era].filter(Boolean),
    comment: `${normalizeText(world.name) || '未命名世界观'} · 世界观概览`,
    content: lines.filter(Boolean).join('\n'),
    constant: options.constantOverview,
    order: 10,
    depth: options.defaultDepth,
  })
}

const buildStageLines = (stages = []) => stages
  .map(stage => {
    const parts = []
    pushLine(parts, '阶段', stage?.name)
    pushLine(parts, '时期', stage?.era)
    pushLine(parts, '描述', stage?.description)
    const attrs = stage?.attributes && typeof stage.attributes === 'object'
      ? Object.entries(stage.attributes).map(([key, value]) => `${key}: ${formatValue(value)}`).filter(Boolean)
      : []
    return [...parts, ...attrs].filter(Boolean).join('；')
  })
  .filter(Boolean)

const buildRelationshipLines = (relationships = []) => relationships
  .map(item => {
    const parts = []
    pushLine(parts, '对象', item?.target || item?.name)
    pushLine(parts, '关系', item?.type || item?.relation)
    pushLine(parts, '时期', item?.time_period)
    pushLine(parts, '来源事件', item?.source_event)
    pushLine(parts, '描述', item?.description)
    return parts.filter(Boolean).join('；')
  })
  .filter(Boolean)

const buildEntityEntry = (entity, options, uid) => {
  const attrs = entity.attributes && typeof entity.attributes === 'object' ? entity.attributes : {}
  const aliases = options.includeAliases ? normalizeList(entity.aliases) : []
  const lines = []
  lines.push(`实体: ${normalizeText(entity.name) || '未命名实体'}`)
  pushLine(lines, '类型', entity.type || '未分类')
  if (aliases.length) pushLine(lines, '别名', aliases.join('、'))
  pushLine(lines, '简介', attrs['简介'] || attrs.intro || attrs.description)

  Object.entries(attrs).forEach(([key, value]) => {
    if (['简介', 'intro', 'description', '阶段', 'stages', 'relationships', '关系'].includes(key)) return
    const text = formatValue(value)
    if (text) lines.push(`${key}: ${text}`)
  })

  if (options.includeStages) {
    const stageLines = buildStageLines(entity.stages || attrs['阶段'] || attrs.stages || [])
    if (stageLines.length) {
      lines.push('成长阶段:')
      stageLines.forEach(line => lines.push(`- ${line}`))
    }
  }

  if (options.includeRelationships) {
    const relationshipLines = buildRelationshipLines(entity.relationships || attrs.relationships || attrs['关系'] || [])
    if (relationshipLines.length) {
      lines.push('关系:')
      relationshipLines.forEach(line => lines.push(`- ${line}`))
    }
  }

  return createEntry({
    uid,
    keys: [entity.name, ...aliases],
    comment: `${normalizeText(entity.name) || '未命名实体'} · ${normalizeText(entity.type) || '实体'}`,
    content: lines.filter(Boolean).join('\n'),
    order: 100,
    depth: options.defaultDepth,
  })
}

const buildEventEntry = (event, options, uid) => {
  const entities = normalizeList(event.entities)
  const lines = []
  lines.push(`事件: ${normalizeText(event.name) || '未命名事件'}`)
  pushLine(lines, '时间', event.date || event.estimated_date)
  pushLine(lines, '时间类型', event.time_type)
  pushLine(lines, '关联实体', entities.join('、'))
  pushLine(lines, '描述', event.description)

  return createEntry({
    uid,
    keys: [event.name],
    comment: `${normalizeText(event.name) || '未命名事件'} · 事件`,
    content: lines.filter(Boolean).join('\n'),
    order: 200,
    depth: options.defaultDepth,
  })
}

const normalizeSettingsItems = (settings = {}) => {
  if (Array.isArray(settings.items)) return settings.items
  if (Array.isArray(settings)) return settings
  return Object.entries(settings || {})
    .filter(([, value]) => value !== null && value !== undefined && value !== '')
    .map(([key, value]) => ({
      name: key,
      category: 'other',
      description: formatValue(value),
      detailContent: formatValue(value),
    }))
}

const structuredDetailLines = (detail = {}) => {
  if (!detail || typeof detail !== 'object') return []
  const lines = []
  pushLine(lines, '摘要', detail.intro || detail.summary)

  const facts = Array.isArray(detail.facts) ? detail.facts : []
  facts.forEach(fact => {
    const label = normalizeText(fact?.label || fact?.key || fact?.name)
    const value = formatValue(fact?.value ?? fact?.content ?? fact?.description)
    if (label && value) lines.push(`${label}: ${value}`)
  })

  const relationships = buildRelationshipLines(detail.relationships || [])
  if (relationships.length) {
    lines.push('关系:')
    relationships.forEach(line => lines.push(`- ${line}`))
  }

  const stages = Array.isArray(detail.stages) ? detail.stages : []
  const stageLines = stages.map(stage => {
    const parts = []
    pushLine(parts, '阶段', stage?.name)
    pushLine(parts, '时期', stage?.era)
    pushLine(parts, '描述', stage?.description)
    ;(stage?.fields || []).forEach(field => {
      const label = normalizeText(field?.label || field?.key)
      const value = formatValue(field?.value)
      if (label && value) parts.push(`${label}: ${value}`)
    })
    return parts.filter(Boolean).join('；')
  }).filter(Boolean)
  if (stageLines.length) {
    lines.push('阶段:')
    stageLines.forEach(line => lines.push(`- ${line}`))
  }

  return lines
}

const buildSettingEntry = (setting, options, uid) => {
  const category = normalizeText(setting.category || 'other')
  const aliases = options.includeAliases ? normalizeList(setting.aliases) : []
  const lines = []
  lines.push(`设定: ${normalizeText(setting.name) || '未命名设定'}`)
  pushLine(lines, '分类', CATEGORY_LABELS[category] || category || '其他')
  if (aliases.length) pushLine(lines, '别名', aliases.join('、'))
  pushLine(lines, '简介', setting.description)
  pushLine(lines, '详情', setting.detailContent)
  lines.push(...structuredDetailLines(setting.structuredDetail || {}))

  return createEntry({
    uid,
    keys: [setting.name, ...aliases],
    comment: `${normalizeText(setting.name) || '未命名设定'} · 设定`,
    content: dedupe(lines.filter(Boolean)).join('\n'),
    order: 300,
    depth: options.defaultDepth,
  })
}

export const buildSillyTavernWorldBook = (world = {}, rawOptions = {}) => {
  const options = { ...DEFAULT_EXPORT_OPTIONS, ...rawOptions }
  const entries = {}
  let uid = 0

  const addEntry = (entry) => {
    if (!entry?.content) return
    entries[String(entry.uid)] = entry
  }

  if (options.includeOverview) {
    addEntry(buildOverviewEntry(world, options, uid++))
  }

  if (options.includeEntities) {
    ;(Array.isArray(world.entities) ? world.entities : []).forEach(entity => {
      addEntry(buildEntityEntry(entity, options, uid++))
    })
  }

  if (options.includeEvents) {
    ;(Array.isArray(world.events) ? world.events : []).forEach(event => {
      addEntry(buildEventEntry(event, options, uid++))
    })
  }

  if (options.includeSettings) {
    normalizeSettingsItems(world.settings || {})
      .filter(setting => setting && setting.settingType !== 'collection')
      .forEach(setting => {
        addEntry(buildSettingEntry(setting, options, uid++))
      })
  }

  return {
    name: normalizeText(world.name) || 'WorldFish 世界书',
    entries,
    extensions: {
      worldfish: {
        source: 'WorldFish',
        world_id: normalizeText(world.id),
        world_name: normalizeText(world.name),
        exported_at: new Date().toISOString(),
        format: 'sillytavern-world-info',
      },
    },
  }
}

export const countWorldBookEntries = (worldBook = {}) => Object.keys(worldBook.entries || {}).length

export const createWorldBookFileName = (world = {}) => {
  const baseName = normalizeText(world.name) || normalizeText(world.id) || 'worldfish-world'
  const safeName = baseName
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, '_')
    .slice(0, 80)
  return `${safeName || 'worldfish-world'}-worldbook.json`
}

export { DEFAULT_EXPORT_OPTIONS }
