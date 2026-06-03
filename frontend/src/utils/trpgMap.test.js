import assert from 'node:assert/strict'
import test from 'node:test'
import {
  applyTrpgMapOverlayEvent,
  createCocCellOverlay,
  createDndToken,
  createSquareMapCells,
  createSquareTrpgMapPreset,
  createTrpgRoomOverlay,
  getWorldStructuredMaps,
  isSquareTrpgMap,
  normalizeMapView,
  recommendMapsForSystem,
  summarizeTrpgOverlay,
} from './trpgMap.js'

const maps = [
  { id: 'world', name: '世界地图', type: 'world', is_default: true },
  { id: 'battle', name: '战斗地图', type: 'battlefield', trpg_system: 'dnd' },
  { id: 'city', name: '调查地图', type: 'city', trpg_system: 'coc' },
]

test('getWorldStructuredMaps reads maps from world settings', () => {
  const world = { settings: { mapData: { structuredMaps: maps } } }
  assert.equal(getWorldStructuredMaps(world).length, 3)
})

test('recommendMapsForSystem prioritizes DND battlefield maps', () => {
  const recommended = recommendMapsForSystem(maps, 'dnd')
  assert.equal(recommended[0].id, 'battle')
})

test('recommendMapsForSystem prioritizes COC investigation maps', () => {
  const recommended = recommendMapsForSystem(maps, 'coc')
  assert.equal(recommended[0].id, 'city')
})

test('createDndToken creates token payload', () => {
  const token = createDndToken({ name: '哥布林', type: 'monster', cellId: 'cell_1', hp: '7', ac: '15' })
  assert.equal(token.name, '哥布林')
  assert.equal(token.type, 'monster')
  assert.equal(token.cellId, 'cell_1')
})

test('createCocCellOverlay creates investigation cell status', () => {
  const overlay = createCocCellOverlay({ cellId: 'cell_2', status: 'discovered', title: '旧宅线索' })
  assert.equal(overlay.cellId, 'cell_2')
  assert.equal(overlay.status, 'discovered')
})

test('applyTrpgMapOverlayEvent replaces room overlay from event payload', () => {
  const current = createTrpgRoomOverlay('dnd', 'battle')
  const next = applyTrpgMapOverlayEvent(current, {
    overlay: {
      ...current,
      tokens: [createDndToken({ name: '战士', cellId: 'cell_0' })],
    },
  })
  assert.equal(next.tokens.length, 1)
  assert.equal(summarizeTrpgOverlay(next).tokenCount, 1)
})

test('createSquareMapCells creates rectangular square cells', () => {
  const cells = createSquareMapCells('map_a', 3, 2)
  assert.equal(cells.length, 6)
  assert.deepEqual(cells.map(cell => cell.id), ['cell_0_0', 'cell_1_0', 'cell_2_0', 'cell_0_1', 'cell_1_1', 'cell_2_1'])
})

test('createSquareTrpgMapPreset creates DND square battle map', () => {
  const map = createSquareTrpgMapPreset('dnd', { id: 'battle_map' })
  assert.equal(map.grid_type, 'square')
  assert.equal(map.type, 'battlefield')
  assert.equal(map.width, 24)
  assert.equal(map.height, 18)
  assert.equal(isSquareTrpgMap(map), true)
})

test('createSquareTrpgMapPreset creates COC square investigation map', () => {
  const map = createSquareTrpgMapPreset('coc', { id: 'coc_map' })
  assert.equal(map.grid_type, 'square')
  assert.equal(map.type, 'city')
  assert.equal(map.width, 16)
  assert.equal(map.height, 12)
  assert.equal(map.trpg_system, 'coc')
})

test('normalizeMapView clamps alignment values', () => {
  const view = normalizeMapView({ grid_size: 999, image_scale: 0, grid_opacity: 2 })
  assert.equal(view.grid_size, 160)
  assert.equal(view.image_scale, 0.1)
  assert.equal(view.grid_opacity, 1)
})
