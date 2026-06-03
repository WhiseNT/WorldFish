const ENTITY_CARD_ROW_LAYOUT_STORAGE_KEY = 'worldfish:worldBuilder:entityCardRowLayout'

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

export const normalizeEntityCardRowLayoutPreference = (value) => {
  if (typeof value === 'boolean') {
    return value
  }

  if (typeof value === 'number') {
    return value !== 0
  }

  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    if (!normalized) {
      return false
    }

    if (['1', 'true', 'yes', 'on'].includes(normalized)) {
      return true
    }

    if (['0', 'false', 'no', 'off'].includes(normalized)) {
      return false
    }
  }

  return false
}

export const readEntityCardRowLayoutPreference = (storage) => {
  const resolvedStorage = resolveStorage(storage)
  if (!resolvedStorage) {
    return false
  }

  try {
    return normalizeEntityCardRowLayoutPreference(resolvedStorage.getItem(ENTITY_CARD_ROW_LAYOUT_STORAGE_KEY))
  } catch (error) {
    return false
  }
}

export const writeEntityCardRowLayoutPreference = (value, storage) => {
  const resolvedStorage = resolveStorage(storage)
  if (!resolvedStorage) {
    return false
  }

  try {
    resolvedStorage.setItem(
      ENTITY_CARD_ROW_LAYOUT_STORAGE_KEY,
      normalizeEntityCardRowLayoutPreference(value) ? 'true' : 'false',
    )
    return true
  } catch (error) {
    return false
  }
}

export { ENTITY_CARD_ROW_LAYOUT_STORAGE_KEY }
