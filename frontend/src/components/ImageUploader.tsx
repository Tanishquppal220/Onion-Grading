import { useCallback, useEffect, useRef, useState } from "react"
import {
  UploadCloud,
  X,
  ImageIcon,
  FileWarning,
  CheckCircle2,
  Loader2,
  Ruler,
  Building2,
  User,
  Hash,
  ChevronDown,
  ChevronUp,
  Camera,
  Smartphone
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { LiveCameraModal } from "@/components/LiveCameraModal"
import type { UploadOptions } from "@/hooks/useImageUpload"

type UploadState = "idle" | "dragging" | "preview" | "error"

interface ImageUploaderProps {
  onUpload: (file: File, options?: UploadOptions) => Promise<unknown>
  isUploading: boolean
  uploadError: string | null
}


function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export function ImageUploader({ onUpload, isUploading, uploadError }: ImageUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)
  const [state, setState] = useState<UploadState>("idle")
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string>("")
  const [isLiveCameraOpen, setIsLiveCameraOpen] = useState<boolean>(false)

  // Procurement Lot Details
  const [lotId, setLotId] = useState<string>(() => `LOT-${Math.floor(1000 + Math.random() * 9000)}`)
  const [farmerName, setFarmerName] = useState<string>("Ramesh Patil")
  const [mandiLocation, setMandiLocation] = useState<string>("Lasalgaon APMC, Nashik")
  const [showLotSetup, setShowLotSetup] = useState<boolean>(false)

  const handleAnalyze = async () => {
    if (!file) return
    try {
      await onUpload(file, {
        calibration_mode: "aruco_50mm",
        lot_id: lotId,
        farmer_name: farmerName,
        mandi_location: mandiLocation,
      })
    } catch (e) {
      console.error("Failed to upload image", e)
    }
  }

  // Revoke object URL on cleanup to prevent memory leaks
  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  }, [preview])

  const acceptFile = useCallback((incoming: File) => {
    if (!incoming.type.startsWith("image/")) {
      setErrorMsg("Only image files are accepted (JPG, PNG, WEBP, etc.)")
      setState("error")
      setTimeout(() => setState("idle"), 3500)
      return
    }
    if (preview) URL.revokeObjectURL(preview)
    const url = URL.createObjectURL(incoming)
    setFile(incoming)
    setPreview(url)
    setState("preview")
  }, [preview])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = e.target.files?.[0]
    if (picked) acceptFile(picked)
    e.target.value = ""
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (state !== "preview") setState("dragging")
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (state === "dragging") setState("idle")
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) acceptFile(dropped)
    else setState("idle")
  }

  const handleClear = () => {
    if (preview) URL.revokeObjectURL(preview)
    setFile(null)
    setPreview(null)
    setState("idle")
  }

  const openPicker = () => {
    if (state !== "preview") inputRef.current?.click()
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleInputChange}
      />

      {/* Hidden camera capture input for direct rear phone camera */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleInputChange}
      />

      {/* ── Procurement Inspection Details & Calibration Bar ── */}
      <div className="rounded-xl border border-border/80 bg-muted/20 p-3 text-xs space-y-2.5 transition-all">
        <div
          className="flex items-center justify-between cursor-pointer select-none"
          onClick={() => setShowLotSetup(!showLotSetup)}
        >
          <div className="flex items-center gap-2 font-medium text-foreground">
            <Building2 className="size-3.5 text-primary shrink-0" />
            <span className="font-semibold">Lot &amp; Mandi Context</span>
            <span className="text-muted-foreground text-[11px] hidden sm:inline">
              ({lotId} • {mandiLocation.split(",")[0]})
            </span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Badge variant="outline" className="text-[10px] font-mono">
              Optical Metrology
            </Badge>
            <span className="text-[11px] text-primary hover:underline flex items-center gap-0.5">
              {showLotSetup ? "Hide Details" : "Edit Details"}
              {showLotSetup ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
            </span>
          </div>
        </div>

        {showLotSetup && (
          <div className="space-y-3 pt-2 border-t border-border/60 animate-in fade-in duration-200">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <div>
                <label className="text-[11px] text-muted-foreground flex items-center gap-1 mb-1 font-medium">
                  <Hash className="size-3 text-primary" /> Lot Identifier
                </label>
                <Input
                  value={lotId}
                  onChange={(e) => setLotId(e.target.value)}
                  className="h-8 text-xs font-mono"
                  placeholder="e.g. LOT-4082"
                />
              </div>

              <div>
                <label className="text-[11px] text-muted-foreground flex items-center gap-1 mb-1 font-medium">
                  <User className="size-3 text-primary" /> Farmer / Vendor
                </label>
                <Input
                  value={farmerName}
                  onChange={(e) => setFarmerName(e.target.value)}
                  className="h-8 text-xs"
                  placeholder="e.g. Ramesh Patil"
                />
              </div>

              <div>
                <label className="text-[11px] text-muted-foreground flex items-center gap-1 mb-1 font-medium">
                  <Building2 className="size-3 text-primary" /> Mandi / APMC Center
                </label>
                <Input
                  value={mandiLocation}
                  onChange={(e) => setMandiLocation(e.target.value)}
                  className="h-8 text-xs"
                  placeholder="e.g. Lasalgaon APMC"
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-border/40 text-[11px]">
              <span className="text-muted-foreground">
                Metrology System: <span className="font-mono text-foreground font-semibold">50mm ArUco Marker (In-Frame) or 55mm Median Prior</span>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* ── Optical Metrology Guidance Bar ── */}
      <div className="flex items-center justify-between rounded-xl border border-border/80 bg-muted/20 px-3.5 py-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <Ruler className="size-3.5 text-primary shrink-0" />
          <span>
            <strong className="text-foreground font-semibold">Standard Metrology:</strong> Include 50mm ArUco card in frame for certified millimeter sizing, or scan directly for 55mm fallback scale.
          </span>
        </div>
        <a
          href="/aruco_marker_50mm.png"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[11px] font-medium text-primary hover:underline shrink-0 hidden sm:inline"
        >
          Print Marker &rarr;
        </a>
      </div>

      {/* ── Mobile Field Action Bar (1-Tap Live Camera & Native Camera) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        <Button
          type="button"
          onClick={() => setIsLiveCameraOpen(true)}
          className="h-11 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold text-xs sm:text-sm gap-2 rounded-xl shadow-sm active:scale-[0.99] transition-all cursor-pointer"
        >
          <Camera className="size-4" />
          <span>Open Live Viewfinder HUD</span>
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => cameraInputRef.current?.click()}
          className="h-11 text-xs sm:text-sm gap-2 border-border/80 font-medium hover:bg-muted rounded-xl active:scale-[0.99] transition-all cursor-pointer"
        >
          <Smartphone className="size-4 text-primary" />
          <span>Snap Photo (Phone Camera)</span>
        </Button>
      </div>

      {/* ── Upload Zone ── */}
      <div
        onClick={openPicker}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "relative flex min-h-52 w-full cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed transition-all duration-200 select-none",
          state === "idle" && "border-border/80 bg-muted/10 hover:border-primary/60 hover:bg-muted/30",
          state === "dragging" && "scale-[1.01] border-primary bg-primary/5 shadow-lg shadow-primary/10",
          state === "error" && "border-destructive bg-destructive/5 cursor-default",
          state === "preview" && "cursor-default border-border/50 bg-muted/10"
        )}
      >
        {/* Idle / dragging state */}
        {(state === "idle" || state === "dragging") && (
          <div className="flex flex-col items-center gap-2.5 px-6 py-6 text-center">
            <div
              className={cn(
                "flex size-14 items-center justify-center rounded-2xl border border-border/80 transition-colors duration-200",
                state === "dragging"
                  ? "border-primary bg-primary/10 text-primary"
                  : "bg-muted/40 text-primary"
              )}
            >
              <UploadCloud className="size-7" />
            </div>
            <div className="flex flex-col gap-1">
              <p className="text-sm font-semibold text-foreground">
                {state === "dragging" ? "Release to drop sample tray photo" : "Drop sample tray image here or click to browse"}
              </p>
              <p className="text-xs text-muted-foreground">
                Supports single bulbs or multi-onion procurement trays (JPG, PNG, WEBP)
              </p>
            </div>
            <div className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground bg-muted/40 px-2.5 py-1 rounded-full border border-border/40">
              <Ruler className="size-3 text-primary" />
              Tip: Include a 50mm ArUco card in frame for automatic millimeter calibration
            </div>
          </div>
        )}

        {/* Error state */}
        {state === "error" && (
          <div className="flex flex-col items-center gap-2.5 px-6 py-6 text-center">
            <div className="flex size-12 items-center justify-center rounded-full border border-destructive/30 bg-destructive/10 text-destructive">
              <FileWarning className="size-6" />
            </div>
            <div className="flex flex-col gap-0.5">
              <p className="text-sm font-medium text-destructive">Invalid file type</p>
              <p className="text-xs text-muted-foreground">{errorMsg}</p>
            </div>
          </div>
        )}

        {/* Preview state */}
        {state === "preview" && file && preview && (
          <div className="flex w-full flex-col items-center gap-3 px-4 py-4">
            <div className="relative w-full max-w-md overflow-hidden rounded-xl border border-border/80 shadow-md">
              <img
                src={preview}
                alt="Selected sample tray"
                className="h-48 w-full object-cover"
              />
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleClear()
                }}
                className="absolute right-2 top-2 flex size-7 items-center justify-center rounded-full bg-background/80 text-foreground backdrop-blur-sm transition-colors hover:bg-background hover:text-destructive cursor-pointer"
                aria-label="Remove image"
              >
                <X className="size-4" />
              </button>
            </div>

            <div className="flex w-full max-w-md items-center gap-3 rounded-xl border border-border/80 bg-card px-3.5 py-2.5 shadow-xs">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <ImageIcon className="size-4" />
              </div>
              <div className="flex min-w-0 flex-col gap-0.5">
                <p className="truncate text-xs font-semibold text-foreground">{file.name}</p>
                <p className="text-[10px] text-muted-foreground">
                  {formatBytes(file.size)} • {file.type.split("/")[1]?.toUpperCase() || "IMAGE"}
                </p>
              </div>
              <Badge variant="secondary" className="ml-auto shrink-0 gap-1 text-[11px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30">
                <CheckCircle2 className="size-3" />
                Ready to Scan
              </Badge>
            </div>
          </div>
        )}
      </div>

      {/* ── Analyze CTA ── */}
      <Button
        size="lg"
        disabled={state !== "preview" || isUploading}
        className={cn(
          "w-full h-12 gap-2 text-sm font-bold shadow-md rounded-xl transition-all active:scale-[0.99]",
          state === "preview"
            ? "bg-primary hover:bg-primary/90 text-primary-foreground shadow-primary/20 cursor-pointer"
            : "cursor-not-allowed opacity-60"
        )}
        onClick={handleAnalyze}
      >
        {isUploading && <Loader2 className="size-5 animate-spin" />}
        {isUploading
          ? "Analyzing Produce Quality & Metrology..."
          : state === "preview"
          ? "Run AI Lot Assessment & FAQ Grading"
          : "Select or Drop a Sample Image to Begin"}
      </Button>

      {uploadError && (
        <p className="text-center text-xs font-medium text-destructive">
          {uploadError}
        </p>
      )}

      {/* Live Camera Viewfinder Modal with Sampling Tray HUD */}
      <LiveCameraModal
        isOpen={isLiveCameraOpen}
        onClose={() => setIsLiveCameraOpen(false)}
        onCapture={(capturedFile) => acceptFile(capturedFile)}
      />
    </div>
  )
}
