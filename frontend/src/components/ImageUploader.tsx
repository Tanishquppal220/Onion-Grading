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
  Sparkles,
  ChevronDown,
  ChevronUp
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { CalibrationSettingsModal, type CalibrationConfig } from "@/components/CalibrationSettingsModal"
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
  const [state, setState] = useState<UploadState>("idle")
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string>("")

  // Procurement Lot Details
  const [lotId, setLotId] = useState<string>(() => `DOCA-${Math.floor(1000 + Math.random() * 9000)}`)
  const [farmerName, setFarmerName] = useState<string>("Ramesh Patil")
  const [mandiLocation, setMandiLocation] = useState<string>("Lasalgaon APMC, Nashik")
  const [showLotSetup, setShowLotSetup] = useState<boolean>(true)

  // Calibration Config
  const [isCalibModalOpen, setIsCalibModalOpen] = useState<boolean>(false)
  const [calibConfig, setCalibConfig] = useState<CalibrationConfig>({
    mode: "estimated",
    custom_mm_per_pixel: 0.635,
  })

  const handleAnalyze = async () => {
    if (!file) return
    try {
      await onUpload(file, {
        calibration_mode: calibConfig.mode,
        custom_mm_per_pixel: calibConfig.custom_mm_per_pixel,
        reference_dimension_mm: calibConfig.reference_dimension_mm,
        reference_pixels: calibConfig.reference_pixels,
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

  // Load sample image preset
  const loadSample = async (filename: string) => {
    try {
      const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000"
      const res = await fetch(`${baseUrl}/uploads/${filename}`)
      if (!res.ok) throw new Error("Could not fetch sample")
      const blob = await res.blob()
      const sampleFile = new File([blob], filename, { type: "image/jpeg" })
      acceptFile(sampleFile)
    } catch (err) {
      console.warn("Could not load sample directly, please upload manually:", err)
    }
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

      {/* ── Procurement Inspection Details & Calibration Bar ── */}
      <div className="rounded-xl border border-border bg-muted/20 p-3 text-xs space-y-3">
        <div
          className="flex items-center justify-between cursor-pointer select-none"
          onClick={() => setShowLotSetup(!showLotSetup)}
        >
          <div className="flex items-center gap-2 font-semibold text-foreground">
            <Building2 className="size-3.5 text-primary" />
            <span>Procurement Lot &amp; Calibration Metadata</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Badge variant="outline" className="text-[10px] font-mono">
              {calibConfig.mode === "estimated" ? "Estimated Scale" : "Calibrated"}
            </Badge>
            {showLotSetup ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
          </div>
        </div>

        {showLotSetup && (
          <div className="space-y-3 pt-1 border-t border-border/60 animate-in fade-in duration-200">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <div>
                <label className="text-[10px] text-muted-foreground flex items-center gap-1 mb-1">
                  <Hash className="size-3" /> Lot ID
                </label>
                <Input
                  value={lotId}
                  onChange={(e) => setLotId(e.target.value)}
                  className="h-7 text-xs font-mono"
                  placeholder="e.g. DOCA-4082"
                />
              </div>

              <div>
                <label className="text-[10px] text-muted-foreground flex items-center gap-1 mb-1">
                  <User className="size-3" /> Farmer / Vendor
                </label>
                <Input
                  value={farmerName}
                  onChange={(e) => setFarmerName(e.target.value)}
                  className="h-7 text-xs"
                  placeholder="e.g. Ramesh Patil"
                />
              </div>

              <div>
                <label className="text-[10px] text-muted-foreground flex items-center gap-1 mb-1">
                  <Building2 className="size-3" /> Mandi / APMC Center
                </label>
                <Input
                  value={mandiLocation}
                  onChange={(e) => setMandiLocation(e.target.value)}
                  className="h-7 text-xs"
                  placeholder="e.g. Lasalgaon APMC"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-1 border-t border-border/40 text-[11px]">
              <span className="text-muted-foreground">
                Scale: <span className="font-mono text-foreground font-medium">
                  {calibConfig.mode === "estimated" ? "~0.635 mm/px (Uncalibrated)" : `${calibConfig.custom_mm_per_pixel} mm/px (Calibrated)`}
                </span>
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsCalibModalOpen(true)}
                className="h-6 text-[10px] gap-1"
              >
                <Ruler className="size-3 text-primary" />
                Configure Calibration
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* ── Upload Zone ── */}
      <div
        onClick={openPicker}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "relative flex min-h-56 w-full cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed transition-all duration-200 select-none",
          state === "idle" && "border-border bg-muted/10 hover:border-primary/60 hover:bg-muted/30",
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
                "flex size-12 items-center justify-center rounded-full border border-border transition-colors duration-200",
                state === "dragging"
                  ? "border-primary bg-primary/10 text-primary"
                  : "bg-muted text-muted-foreground"
              )}
            >
              <UploadCloud className="size-6" />
            </div>
            <div className="flex flex-col gap-0.5">
              <p className="text-sm font-medium text-foreground">
                {state === "dragging" ? "Release to upload lot sample" : "Drag & drop sample tray image here"}
              </p>
              <p className="text-xs text-muted-foreground">
                or <span className="font-medium text-primary underline underline-offset-2">browse files</span>
              </p>
            </div>
            <p className="text-[10px] text-muted-foreground">
              Supports single bulb or multi-onion procurement tray (JPG, PNG, WEBP)
            </p>
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
            <div className="relative w-full max-w-sm overflow-hidden rounded-lg border border-border shadow-md">
              <img
                src={preview}
                alt="Selected sample tray"
                className="h-44 w-full object-cover"
              />
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleClear()
                }}
                className="absolute right-2 top-2 flex size-7 items-center justify-center rounded-full bg-background/80 text-foreground backdrop-blur-sm transition-colors hover:bg-background hover:text-destructive"
                aria-label="Remove image"
              >
                <X className="size-4" />
              </button>
            </div>

            <div className="flex w-full max-w-sm items-center gap-3 rounded-lg border border-border bg-muted/30 px-3 py-2">
              <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                <ImageIcon className="size-3.5" />
              </div>
              <div className="flex min-w-0 flex-col gap-0.5">
                <p className="truncate text-xs font-medium text-foreground">{file.name}</p>
                <p className="text-[10px] text-muted-foreground">
                  {formatBytes(file.size)} · {file.type}
                </p>
              </div>
              <Badge variant="secondary" className="ml-auto shrink-0 gap-1 text-[10px]">
                <CheckCircle2 className="size-3 text-green-500" />
                Ready for AI
              </Badge>
            </div>
          </div>
        )}
      </div>

      {/* ── Quick Demo Samples Bar ── */}
      {state === "idle" && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[11px] text-muted-foreground flex items-center gap-1">
            <Sparkles className="size-3 text-primary" /> Test with sample tray:
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => loadSample("images.jpg")}
            className="h-6 text-[10px] px-2"
          >
            Tray 1 (27 Bulbs)
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => loadSample("images1.jpg")}
            className="h-6 text-[10px] px-2"
          >
            Tray 2 (Commercial Crate)
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => loadSample("images3.jpg")}
            className="h-6 text-[10px] px-2"
          >
            Tray 3 (Sprouted Sample)
          </Button>

        </div>
      )}

      {/* ── Analyze CTA ── */}
      <Button
        size="lg"
        disabled={state !== "preview" || isUploading}
        className="w-full gap-2 font-semibold shadow-md"
        onClick={handleAnalyze}
      >
        {isUploading && <Loader2 className="size-4 animate-spin" />}
        {isUploading
          ? "Analyzing & Grading against DoCA Standards..."
          : state === "preview"
          ? "Run AI Lot Assessment & FAQ Grading"
          : "Select or Drop a Sample Image to Begin"}
      </Button>

      {uploadError && (
        <p className="text-center text-xs font-medium text-destructive">
          {uploadError}
        </p>
      )}

      {/* Calibration Modal */}
      <CalibrationSettingsModal
        isOpen={isCalibModalOpen}
        onClose={() => setIsCalibModalOpen(false)}
        currentConfig={calibConfig}
        onSave={(newConfig) => setCalibConfig(newConfig)}
      />
    </div>
  )
}
