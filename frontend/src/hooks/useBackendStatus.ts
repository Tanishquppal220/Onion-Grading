import { useEffect, useSyncExternalStore } from "react"

export type BackendStatusType = "connecting" | "online" | "offline"

const HEALTH_URL =
  (import.meta.env.VITE_API_URL ?? "http://localhost:8000") + "/api/health"

const POLL_INTERVAL_MS = 10_000
const TIMEOUT_MS = 3_000

let currentStatus: BackendStatusType = "connecting"
let pollTimer: ReturnType<typeof setInterval> | null = null
let isChecking = false
let hasInitialized = false
const listeners = new Set<() => void>()

function emitChange() {
  listeners.forEach((listener) => listener())
}

function setStatus(nextStatus: BackendStatusType) {
  if (currentStatus !== nextStatus) {
    currentStatus = nextStatus
    emitChange()
  }
}

function startPolling() {
  if (pollTimer === null) {
    pollTimer = setInterval(() => {
      checkBackendHealth()
    }, POLL_INTERVAL_MS)
  }
}

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

export async function checkBackendHealth(): Promise<boolean> {
  if (isChecking) {
    return currentStatus === "online"
  }

  isChecking = true
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)

  try {
    const res = await fetch(HEALTH_URL, { signal: controller.signal })
    if (res.ok) {
      setStatus("online")
      // Once online, stop checking/polling until another request fails
      stopPolling()
      return true
    } else {
      setStatus("offline")
      // If offline, poll so that when the API comes back up, it will be detected
      startPolling()
      return false
    }
  } catch {
    setStatus("offline")
    startPolling()
    return false
  } finally {
    clearTimeout(timer)
    isChecking = false
  }
}

export function notifyRequestSuccess() {
  // If an API request succeeds, the backend is definitely online
  if (currentStatus !== "online") {
    setStatus("online")
    stopPolling()
  }
}

export function notifyRequestFailed(error?: unknown) {
  // Another request has failed!
  // If there is no response (network error / connection refused / timeout),
  // immediately mark offline for instant UI feedback.
  const hasResponse =
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    Boolean((error as { response?: unknown }).response)

  if (!hasResponse) {
    setStatus("offline")
    startPolling()
  }

  // Immediately run a health check to verify backend status
  checkBackendHealth()
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function getSnapshot() {
  return currentStatus
}

function getServerSnapshot() {
  return "connecting" as BackendStatusType
}

export function useBackendStatus(): BackendStatusType {
  useEffect(() => {
    if (!hasInitialized) {
      hasInitialized = true
      checkBackendHealth()
    }
  }, [])

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}

