import assert from 'node:assert/strict'
import test from 'node:test'
import {
  ENTITY_CARD_ROW_LAYOUT_STORAGE_KEY,
  normalizeEntityCardRowLayoutPreference,
  readEntityCardRowLayoutPreference,
  writeEntityCardRowLayoutPreference,
} from './entityCardLayoutPreference.js'

const createMemoryStorage = (initialValue) => {
  const values = new Map()
  if (initialValue !== undefined) {
    values.set(ENTITY_CARD_ROW_LAYOUT_STORAGE_KEY, initialValue)
  }

  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null
    },
    setItem(key, value) {
      values.set(key, String(value))
    },
    removeItem(key) {
      values.delete(key)
    },
    snapshot() {
      return new Map(values)
    },
  }
}

test('normalizeEntityCardRowLayoutPreference parses booleans and common strings', () => {
  assert.equal(normalizeEntityCardRowLayoutPreference(true), true)
  assert.equal(normalizeEntityCardRowLayoutPreference(false), false)
  assert.equal(normalizeEntityCardRowLayoutPreference(1), true)
  assert.equal(normalizeEntityCardRowLayoutPreference(0), false)
  assert.equal(normalizeEntityCardRowLayoutPreference('true'), true)
  assert.equal(normalizeEntityCardRowLayoutPreference('TRUE'), true)
  assert.equal(normalizeEntityCardRowLayoutPreference('yes'), true)
  assert.equal(normalizeEntityCardRowLayoutPreference('on'), true)
  assert.equal(normalizeEntityCardRowLayoutPreference('false'), false)
  assert.equal(normalizeEntityCardRowLayoutPreference('0'), false)
  assert.equal(normalizeEntityCardRowLayoutPreference(''), false)
  assert.equal(normalizeEntityCardRowLayoutPreference('unexpected'), false)
})

test('readEntityCardRowLayoutPreference defaults to false without storage value', () => {
  const storage = createMemoryStorage()
  assert.equal(readEntityCardRowLayoutPreference(storage), false)
})

test('readEntityCardRowLayoutPreference reads stored values safely', () => {
  assert.equal(readEntityCardRowLayoutPreference(createMemoryStorage('true')), true)
  assert.equal(readEntityCardRowLayoutPreference(createMemoryStorage('false')), false)
  assert.equal(readEntityCardRowLayoutPreference(createMemoryStorage('1')), true)
  assert.equal(readEntityCardRowLayoutPreference(createMemoryStorage('0')), false)
})

test('writeEntityCardRowLayoutPreference writes normalized values', () => {
  const storage = createMemoryStorage()

  assert.equal(writeEntityCardRowLayoutPreference(true, storage), true)
  assert.equal(storage.getItem(ENTITY_CARD_ROW_LAYOUT_STORAGE_KEY), 'true')
  assert.equal(readEntityCardRowLayoutPreference(storage), true)

  assert.equal(writeEntityCardRowLayoutPreference(false, storage), true)
  assert.equal(storage.getItem(ENTITY_CARD_ROW_LAYOUT_STORAGE_KEY), 'false')
  assert.equal(readEntityCardRowLayoutPreference(storage), false)
})

test('preference helpers fail closed when storage is unavailable', () => {
  const unavailableStorage = {
    getItem() {
      throw new Error('unavailable')
    },
    setItem() {
      throw new Error('unavailable')
    },
  }

  assert.equal(readEntityCardRowLayoutPreference(unavailableStorage), false)
  assert.equal(writeEntityCardRowLayoutPreference(true, unavailableStorage), false)
})
