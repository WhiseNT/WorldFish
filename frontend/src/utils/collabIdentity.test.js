import assert from 'node:assert/strict'
import test from 'node:test'
import {
  COLLAB_DISPLAY_NAME_KEY,
  COLLAB_USER_ID_KEY,
  ensureCollabIdentity,
  readCollabIdentity,
  writeCollabDisplayName,
} from './collabIdentity.js'

const createMemoryStorage = () => {
  const values = new Map()
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null
    },
    setItem(key, value) {
      values.set(key, String(value))
    },
  }
}

test('ensureCollabIdentity creates and persists a LAN user identity', () => {
  const storage = createMemoryStorage()
  const identity = ensureCollabIdentity(storage)

  assert.match(identity.userId, /^lan_/)
  assert.equal(identity.persistent, true)
  assert.equal(storage.getItem(COLLAB_USER_ID_KEY), identity.userId)
  assert.equal(storage.getItem(COLLAB_DISPLAY_NAME_KEY), identity.displayName)
})

test('readCollabIdentity reuses persisted values', () => {
  const storage = createMemoryStorage()
  const created = ensureCollabIdentity(storage)
  const readBack = readCollabIdentity(storage)

  assert.deepEqual(readBack, created)
})

test('writeCollabDisplayName updates only the display name', () => {
  const storage = createMemoryStorage()
  const created = ensureCollabIdentity(storage)
  const updated = writeCollabDisplayName('玩家二号', storage)

  assert.equal(updated.userId, created.userId)
  assert.equal(updated.displayName, '玩家二号')
  assert.equal(storage.getItem(COLLAB_DISPLAY_NAME_KEY), '玩家二号')
})

test('identity helpers fall back safely when storage fails', () => {
  const failingStorage = {
    getItem() {
      throw new Error('unavailable')
    },
    setItem() {
      throw new Error('unavailable')
    },
  }

  const identity = ensureCollabIdentity(failingStorage)
  assert.match(identity.userId, /^lan_/)
  assert.equal(identity.persistent, false)

  const updated = writeCollabDisplayName('临时玩家', failingStorage)
  assert.equal(updated.displayName, '临时玩家')
  assert.equal(updated.persistent, false)
})
