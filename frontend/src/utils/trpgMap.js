const normalizeText = (value = '') => String(value ?? '').trim()
const createId = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

export function getWorldStructuredMaps(world = {}) {
  const settings = world.settings || {}
  const mapData = settings.mapData || settings.map_data || {}
  const maps = Array.isArray(mapData.structuredMaps) ? mapData.structuredMaps : []
  return maps.filter(item => item && typeof item === 'object')
}

export function mapTrpgSystem(map = {}) {
  return normalizeText(map.trpg_system || map.trpgSystem || map.custom?.trpg_system || map.custom?.trpgSystem).toLowerCase()
}

export function recommendMapsForSystem(maps = [], system = 'dnd') {
  const normalizedSystem = normalizeText(system).toLowerCase() || 'dnd'
  const normalizedMaps = Array.isArray(maps) ? maps : []
  const typeScores = normalizedSystem === 'coc'
    ? { city: 4, region: 3, country: 2, world: 1, dungeon: 1, battlefield: 0 }
    : { battlefield: 4, dungeon: 4, region: 2, city: 2, country: 1, world: 1 }

  return [...normalizedMaps].sort((a, b) => {
    const aSystem = mapTrpgSystem(a)
    const bSystem = mapTrpgSystem(b)
    const aSystemScore = aSystem === normalizedSystem ? 10 : 0
    const bSystemScore = bSystem === normalizedSystem ? 10 : 0
    const aTypeScore = typeScores[a.type] ?? 0
    const bTypeScore = typeScores[b.type] ?? 0
    const aGridScore = isSquareTrpgMap(a) ? 3 : 0
    const bGridScore = isSquareTrpgMap(b) ? 3 : 0
    const aDefault = a.is_default ? 1 : 0
    const bDefault = b.is_default ? 1 : 0
    return (bSystemScore + bTypeScore + bGridScore + bDefault) - (aSystemScore + aTypeScore + aGridScore + aDefault)
  })
}

export function createTrpgRoomOverlay(system = 'dnd', mapId = '') {
  return {
    system: normalizeText(system).toLowerCase() || 'dnd',
    mapId: normalizeText(mapId),
    tokens: [],
    cellOverlays: {},
    updatedAt: new Date().toISOString(),
  }
}

export function createDndToken(payload = {}) {
  return {
    id: normalizeText(payload.id) || createId('token'),
    name: normalizeText(payload.name) || '未命名 Token',
    type: normalizeText(payload.type) || 'pc',
    cellId: normalizeText(payload.cellId),
    hp: normalizeText(payload.hp),
    ac: normalizeText(payload.ac),
    status: normalizeText(payload.status),
    color: normalizeText(payload.color),
    updatedAt: new Date().toISOString(),
  }
}

export function createCocCellOverlay(payload = {}) {
  const status = normalizeText(payload.status) || 'hidden'
  return {
    cellId: normalizeText(payload.cellId),
    status,
    title: normalizeText(payload.title),
    description: normalizeText(payload.description),
    npc: normalizeText(payload.npc),
    evidence: normalizeText(payload.evidence),
    updatedAt: new Date().toISOString(),
  }
}

export function normalizeTrpgOverlay(overlay = {}) {
  return {
    system: normalizeText(overlay.system).toLowerCase() || 'dnd',
    mapId: normalizeText(overlay.mapId || overlay.map_id),
    tokens: Array.isArray(overlay.tokens) ? overlay.tokens.map(createDndToken) : [],
    cellOverlays: overlay.cellOverlays && typeof overlay.cellOverlays === 'object' ? { ...overlay.cellOverlays } : {},
    updatedAt: overlay.updatedAt || overlay.updated_at || new Date().toISOString(),
  }
}

export function applyTrpgMapOverlayEvent(currentOverlay = {}, eventPayload = {}) {
  const current = normalizeTrpgOverlay(currentOverlay)
  const incoming = eventPayload.overlay || eventPayload
  if (!incoming || typeof incoming !== 'object') return current
  const normalizedIncoming = normalizeTrpgOverlay({
    ...current,
    ...incoming,
    tokens: incoming.tokens ?? current.tokens,
    cellOverlays: incoming.cellOverlays ?? current.cellOverlays,
  })
  return normalizedIncoming
}

export function isSquareTrpgMap(map = {}) {
  const gridType = normalizeText(map.grid_type || map.gridType || map.custom?.grid_type || map.custom?.gridType).toLowerCase()
  return gridType === 'square'
}

export function normalizeMapView(view = {}) {
  const numberValue = (value, fallback, min, max) => {
    const number = Number(value)
    if (!Number.isFinite(number)) return fallback
    return Math.max(min, Math.min(max, number))
  }
  return {
    ...(view && typeof view === 'object' ? view : {}),
    grid_size: numberValue(view.grid_size, 48, 16, 160),
    image_scale: numberValue(view.image_scale, 1, 0.1, 5),
    image_offset_x: numberValue(view.image_offset_x, 0, -3000, 3000),
    image_offset_y: numberValue(view.image_offset_y, 0, -3000, 3000),
    grid_opacity: numberValue(view.grid_opacity, 0.55, 0, 1),
    image_opacity: numberValue(view.image_opacity, 1, 0, 1),
  }
}

export function createSquareMapCells(mapId = '', width = 12, height = 12) {
  const safeWidth = Math.max(1, Math.min(80, Number(width || 12)))
  const safeHeight = Math.max(1, Math.min(80, Number(height || 12)))
  const cells = []
  for (let row = 0; row < safeHeight; row += 1) {
    for (let col = 0; col < safeWidth; col += 1) {
      cells.push({
        id: `cell_${col}_${row}`,
        map_id: mapId,
        q: col,
        r: row,
        name: '',
        description: '',
        terrain: 'unset',
        status: 'normal',
        faction: '',
        resources: [],
        locations: [],
        tags: [],
        notes: '',
        color: '',
        custom: {},
        updated_at: new Date().toISOString(),
      })
    }
  }
  return cells
}

export function createSquareTrpgMapPreset(system = 'dnd', options = {}) {
  const normalizedSystem = normalizeText(system).toLowerCase() === 'coc' ? 'coc' : 'dnd'
  const id = normalizeText(options.id) || createId('map')
  const width = Number(options.width || (normalizedSystem === 'coc' ? 16 : 24))
  const height = Number(options.height || (normalizedSystem === 'coc' ? 12 : 18))
  const trpgRole = normalizedSystem === 'coc' ? 'investigation' : 'battle'
  return {
    id,
    world_id: normalizeText(options.world_id || options.worldId),
    name: normalizeText(options.name) || (normalizedSystem === 'coc' ? 'COC 调查地图' : 'DND 战斗地图'),
    description: '',
    type: normalizedSystem === 'coc' ? 'city' : 'battlefield',
    grid_type: 'square',
    width,
    height,
    radius: 0,
    trpg_system: normalizedSystem,
    trpg_role: trpgRole,
    custom: { grid_type: 'square', trpg_system: normalizedSystem, trpg_role: trpgRole },
    background_image: '',
    view: normalizeMapView(options.view || {}),
    layers: ['terrain', 'faction', 'resource', 'event', 'status'].map(type => ({ type, visible: type === 'terrain', rules: {}, field: type })),
    cells: createSquareMapCells(id, width, height),
    change_records: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
}

export function summarizeTrpgOverlay(overlay = {}) {
  const normalized = normalizeTrpgOverlay(overlay)
  const discoveredCells = Object.values(normalized.cellOverlays || {}).filter(item => item?.status && item.status !== 'hidden').length
  return {
    system: normalized.system,
    mapId: normalized.mapId,
    tokenCount: normalized.tokens.length,
    overlayCellCount: Object.keys(normalized.cellOverlays || {}).length,
    discoveredCells,
  }
}
