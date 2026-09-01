import { Wifi, WifiOff, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { useBackendStatus } from "@/hooks/useBackendStatus"

const config = {
  connecting: {
    label: "Connecting…",
    icon: Loader2,
    iconClass: "animate-spin text-amber-500",
    dotClass: "bg-amber-500 animate-pulse",
    wrapperClass: "text-amber-500/80",
  },
  online: {
    label: "API Online",
    icon: Wifi,
    iconClass: "text-green-500",
    dotClass: "bg-green-500",
    wrapperClass: "text-green-500/90",
  },
  offline: {
    label: "API Offline",
    icon: WifiOff,
    iconClass: "text-destructive",
    dotClass: "bg-destructive animate-pulse",
    wrapperClass: "text-destructive/90",
  },
} as const

export function BackendStatus() {
  const status = useBackendStatus()
  const { label, icon: Icon, iconClass, dotClass, wrapperClass } = config[status]

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/40 px-2.5 py-1 text-xs font-medium backdrop-blur-sm transition-colors duration-500",
        wrapperClass,
      )}
      role="status"
      aria-label={`Backend status: ${label}`}
    >
      {/* Animated status dot */}
      <span className={cn("size-1.5 rounded-full shrink-0", dotClass)} />

      {/* Icon */}
      <Icon className={cn("size-3 shrink-0", iconClass)} />

      {/* Label */}
      <span>{label}</span>
    </div>
  )
}
