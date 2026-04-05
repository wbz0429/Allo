export interface PendingThreadMessage {
  threadId: string
  text: string
}

const KEY = "allo:pending-thread-message"

export function savePendingThreadMessage(storage: Storage, value: PendingThreadMessage) {
  storage.setItem(KEY, JSON.stringify(value))
}

export function loadPendingThreadMessage(storage: Storage, threadId: string) {
  const raw = storage.getItem(KEY)
  if (!raw) {
    return null
  }

  storage.removeItem(KEY)

  const value = JSON.parse(raw) as Partial<PendingThreadMessage>
  if (value.threadId !== threadId || typeof value.text !== "string") {
    return null
  }

  return { threadId: value.threadId, text: value.text }
}

export function clearPendingThreadMessage(storage: Storage, threadId: string) {
  const raw = storage.getItem(KEY)
  if (!raw) {
    return
  }

  const value = JSON.parse(raw) as Partial<PendingThreadMessage>
  if (value.threadId === threadId) {
    storage.removeItem(KEY)
  }
}
