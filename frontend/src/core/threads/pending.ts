import type { FileUIPart } from "ai"

export interface PendingThreadMessage {
  threadId: string
  text: string
  files?: FileUIPart[]
  knowledgeBases?: { id: string; name: string }[]
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

  return {
    threadId: value.threadId,
    text: value.text,
    files: Array.isArray(value.files)
      ? value.files.filter(
          (file): file is FileUIPart =>
            typeof file?.type === "string" && typeof file?.mediaType === "string",
        )
      : undefined,
    knowledgeBases: Array.isArray(value.knowledgeBases)
      ? value.knowledgeBases.filter(
          (kb): kb is { id: string; name: string } =>
            typeof kb?.id === "string" && typeof kb?.name === "string",
        )
      : undefined,
  }
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
