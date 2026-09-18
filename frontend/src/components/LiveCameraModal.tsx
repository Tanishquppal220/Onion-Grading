import { useEffect, useRef, useState } from "react"
import { Camera, X, RefreshCw, Zap, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"

interface LiveCameraModalProps {
  isOpen: boolean
  onClose: () => void
  onCapture: (file: File) => void
}

export function LiveCameraModal({ isOpen, onClose, onCapture }: LiveCameraModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [cameras, setCameras] = useState<MediaDeviceInfo[]>([])
  const [selectedCameraId, setSelectedCameraId] = useState<string>("")
  const [hasTorch, setHasTorch] = useState<boolean>(false)
  const [torchOn, setTorchOn] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [isInitializing, setIsInitializing] = useState<boolean>(true)
  const [retryCount, setRetryCount] = useState<number>(0)

  // Stop camera tracks cleanly
  const stopStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        track.stop()
      })
      streamRef.current = null
    }
  }

  useEffect(() => {
    if (!isOpen) {
      stopStream()
      return
    }

    let active = true

    async function mountCamera() {
      try {
        const constraints: MediaStreamConstraints = {
          video: selectedCameraId
            ? { deviceId: { exact: selectedCameraId } }
            : {
                facingMode: { ideal: "environment" },
                width: { ideal: 1920, min: 1280 },
                height: { ideal: 1080, min: 720 },
              },
          audio: false,
        }

        const stream = await navigator.mediaDevices.getUserMedia(constraints)
        if (!active) {
          stream.getTracks().forEach((t) => t.stop())
          return
        }

        stopStream()
        streamRef.current = stream

        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
        }

        const devices = await navigator.mediaDevices.enumerateDevices()
        const videoDevices = devices.filter((d) => d.kind === "videoinput")
        if (active) {
          setCameras(videoDevices)
          const track = stream.getVideoTracks()[0]
          const capabilities = track.getCapabilities ? (track.getCapabilities() as { torch?: boolean }) : {}
          setHasTorch(Boolean(capabilities?.torch))
          setIsInitializing(false)
          setError(null)
        }
      } catch (err: unknown) {
        if (active) {
          const message =
            err instanceof Error
              ? err.message
              : "Unable to access device camera. Please grant camera permissions or use the system camera picker."
          setError(message)
          setIsInitializing(false)
        }
      }
    }

    mountCamera()

    return () => {
      active = false
      stopStream()
    }
  }, [isOpen, selectedCameraId, retryCount])

  // Toggle flashlight / torch
  const toggleTorch = async () => {
    if (!streamRef.current) return
    const track = streamRef.current.getVideoTracks()[0]
    try {
      const nextTorch = !torchOn
      await (track as MediaStreamTrack & { applyConstraints: (c: MediaTrackConstraints) => Promise<void> }).applyConstraints({
        advanced: [{ torch: nextTorch } as MediaTrackConstraintSet],
      })
      setTorchOn(nextTorch)
    } catch (e) {
      console.warn("Torch control failed:", e)
    }
  }

  // Flip camera between front and back
  const handleSwitchCamera = () => {
    if (cameras.length <= 1) return
    const currentIndex = cameras.findIndex((c) => c.deviceId === selectedCameraId)
    const nextIndex = (currentIndex + 1) % cameras.length
    setSelectedCameraId(cameras[nextIndex].deviceId)
  }

  // Capture frame from video to Canvas and create File
  const handleSnap = () => {
    const video = videoRef.current
    if (!video || video.readyState < 2) return

    const canvas = document.createElement("canvas")
    canvas.width = video.videoWidth || 1280
    canvas.height = video.videoHeight || 720
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Draw the current video frame
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    canvas.toBlob(
      (blob) => {
        if (!blob) return
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-")
        const capturedFile = new File([blob], `mandi_sample_tray_${timestamp}.jpg`, {
          type: "image/jpeg",
        })
        stopStream()
        onCapture(capturedFile)
        onClose()
      },
      "image/jpeg",
      0.95
    )
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-2 sm:p-4 backdrop-blur-md">
      <div className="relative w-full max-w-2xl bg-card rounded-2xl overflow-hidden border border-border shadow-2xl flex flex-col max-h-[95vh]">
        {/* Header bar */}
        <div className="flex items-center justify-between p-3.5 border-b border-border bg-card/80">
          <div className="flex items-center gap-2">
            <span className="flex size-2 rounded-full bg-green-500 animate-ping" />
            <span className="font-semibold text-xs tracking-tight text-foreground">
              Mandi Live Viewfinder · Tray Alignment
            </span>
          </div>
          <div className="flex items-center gap-2">
            {hasTorch && (
              <Button
                variant={torchOn ? "default" : "outline"}
                size="sm"
                onClick={toggleTorch}
                className="size-7 p-0 rounded-full"
                title="Toggle Torch"
              >
                <Zap className="size-3.5" />
              </Button>
            )}
            {cameras.length > 1 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleSwitchCamera}
                className="size-7 p-0 rounded-full"
                title="Flip Camera"
              >
                <RefreshCw className="size-3.5" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="size-7 p-0 rounded-full text-muted-foreground hover:text-foreground"
            >
              <X className="size-4" />
            </Button>
          </div>
        </div>

        {/* Video Viewport with HUD overlay */}
        <div className="relative flex-1 bg-black min-h-[360px] sm:min-h-[460px] flex items-center justify-center overflow-hidden">
          {error ? (
            <div className="p-6 text-center max-w-md space-y-3">
              <AlertCircle className="size-10 text-destructive mx-auto" />
              <p className="text-sm font-semibold text-foreground">Camera Access Required</p>
              <p className="text-xs text-muted-foreground">{error}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setRetryCount((k) => k + 1)}
                className="text-xs"
              >
                Retry Permissions
              </Button>
            </div>
          ) : (
            <>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />

              {/* Holographic Sampling Tray Frame Overlay */}
              <div className="absolute inset-6 sm:inset-10 border-2 border-dashed border-primary/70 rounded-xl pointer-events-none flex flex-col justify-between p-3">
                {/* Corner reticles */}
                <div className="flex justify-between">
                  <div className="size-5 border-t-2 border-l-2 border-primary" />
                  <div className="size-5 border-t-2 border-r-2 border-primary" />
                </div>

                {/* Center Tray Guide */}
                <div className="text-center py-2 px-3 rounded-md bg-black/60 backdrop-blur-sm self-center border border-white/10">
                  <p className="text-[11px] font-bold tracking-wide text-white uppercase">
                    Sampling Tray Alignment (50–100 Bulbs)
                  </p>
                  <p className="text-[10px] text-zinc-300">
                    Hold phone flat ~45cm directly above tray · Avoid shadows
                  </p>
                </div>

                <div className="flex justify-between">
                  <div className="size-5 border-b-2 border-l-2 border-primary" />
                  <div className="size-5 border-b-2 border-r-2 border-primary" />
                </div>
              </div>

              {isInitializing && (
                <div className="absolute inset-0 bg-black/60 flex items-center justify-center text-xs text-white">
                  Initializing camera sensor...
                </div>
              )}
            </>
          )}
        </div>

        {/* Shutter bar */}
        <div className="p-4 bg-card/90 border-t border-border flex items-center justify-around">
          <div className="text-[11px] text-muted-foreground hidden sm:block">
            Top-down parallel shot yields highest grading accuracy
          </div>

          <button
            type="button"
            onClick={handleSnap}
            disabled={Boolean(error) || isInitializing}
            className="flex items-center justify-center size-16 rounded-full bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/30 border-4 border-background transition-transform active:scale-95 disabled:opacity-50 cursor-pointer"
            aria-label="Capture Tray Photo"
          >
            <Camera className="size-7" />
          </button>

          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            className="text-xs sm:hidden"
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  )
}
