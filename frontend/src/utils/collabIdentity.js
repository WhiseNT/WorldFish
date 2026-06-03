const COLLAB_USER_ID_KEY = 'worldfish:collab:userId'
const COLLAB_DISPLAY_NAME_KEY = 'worldfish:collab:displayName'

const USER_ID_PATTERN = /^[A-Za-z0-9_\-:.]{1,128}$/

let fallbackIdentity = null

const isStorageLike = (storage) => (
  storage
  && typeof storage.getItem === 'function'
  && typeof storage.setItem === 'function'
)

const resolveStorage = (storage) => {
  if (isStorageLike(storage)) {
    return storage
  }

  try {
    const candidate = globalThis?.localStorage
    return isStorageLike(candidate) ? candidate : null
  } catch (error) {
    return null
  }
}

const createIdentitySuffix = () => {
  try {
    if (globalThis?.crypto?.randomUUID) {
      return globalThis.crypto.randomUUID().replace(/-/g, '').slice(0, 10)
    }
  } catch (error) {
    // ignore and fall back
  }

  return Math.random().toString(36).slice(2, 10)
}

const createUserId = () => `lan_${Date.now()}_${createIdentitySuffix()}`

const normalizeUserId = (value) => {
  const text = String(value || '').trim()
  return USER_ID_PATTERN.test(text) ? text : ''
}

const createDefaultDisplayName = (userId) => {
  const suffix = String(userId || '').replace(/^lan_/, '').slice(-4).toUpperCase() || createIdentitySuffix().slice(-4).toUpperCase()
  return `局域网成员 ${suffix}`
}

const createFallbackIdentity = () => {
  if (!fallbackIdentity) {
    const userId = createUserId()
    fallbackIdentity = {
      userId,
      displayName: createDefaultDisplayName(userId),
      persistent: false,
    }
  }
  return { ...fallbackIdentity }
}

export const readCollabIdentity = (storage) => {
  const resolvedStorage = resolveStorage(storage)
  if (!resolvedStorage) {
    return createFallbackIdentity()
  }

  try {
    const userId = normalizeUserId(resolvedStorage.getItem(COLLAB_USER_ID_KEY))
    const displayName = String(resolvedStorage.getItem(COLLAB_DISPLAY_NAME_KEY) || '').trim()
    if (!userId) {
      return createFallbackIdentity()
    }
    return {
      userId,
      displayName: displayName || createDefaultDisplayName(userId),
      persistent: true,
    }
  } catch (error) {
    return createFallbackIdentity()
  }
}

export const ensureCollabIdentity = (storage) => {
  const resolvedStorage = resolveStorage(storage)
  if (!resolvedStorage) {
    return createFallbackIdentity()
  }

  try {
    let userId = normalizeUserId(resolvedStorage.getItem(COLLAB_USER_ID_KEY))
    if (!userId) {
      userId = createUserId()
      resolvedStorage.setItem(COLLAB_USER_ID_KEY, userId)
    }

    let displayName = String(resolvedStorage.getItem(COLLAB_DISPLAY_NAME_KEY) || '').trim()
    if (!displayName) {
      displayName = createDefaultDisplayName(userId)
      resolvedStorage.setItem(COLLAB_DISPLAY_NAME_KEY, displayName)
    }

    return { userId, displayName, persistent: true }
  } catch (error) {
    return createFallbackIdentity()
  }
}

export const writeCollabDisplayName = (displayName, storage) => {
  const resolvedStorage = resolveStorage(storage)
  const current = ensureCollabIdentity(storage)
  const nextDisplayName = String(displayName || '').trim() || current.displayName

  if (!resolvedStorage) {
    fallbackIdentity = {
      ...current,
      displayName: nextDisplayName,
      persistent: false,
    }
    return { ...fallbackIdentity }
  }

  try {
    resolvedStorage.setItem(COLLAB_DISPLAY_NAME_KEY, nextDisplayName)
    return {
      userId: current.userId,
      displayName: nextDisplayName,
      persistent: true,
    }
  } catch (error) {
    fallbackIdentity = {
      ...current,
      displayName: nextDisplayName,
      persistent: false,
    }
    return { ...fallbackIdentity }
  }
}

export { COLLAB_DISPLAY_NAME_KEY, COLLAB_USER_ID_KEY }
