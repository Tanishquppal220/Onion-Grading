import { useEffect, useState } from "react"

export type BackendStatusType = "connecting" | "online" | "offline"

const HEALTH_URL =
  (import.meta.env.VITE_API_URL ?? "http://localhost:8000") + "/api/health"

const POLL_INTERVAL_MS = 10_000
const TIMEOUT_MS = 3_000

export function useBackendStatus(): BackendStatusType {
  const [status, setStatus] = useState<BackendStatusType>("connecting")

  useEffect(() => {
    let alive = true

    const check = async () => {
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
      try {
        const res = await fetch(HEALTH_URL, { signal: controller.signal })
        if (alive) setStatus(res.ok ? "online" : "offline")
      } catch {
        if (alive) setStatus("offline")
      } finally {
        clearTimeout(timer)
      }
    }

    check()
    const id = setInterval(check, POLL_INTERVAL_MS)

    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  return status
}
