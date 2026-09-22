import { useState, useRef } from "react"
import {
  X,
  Ruler,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  UploadCloud,
  RotateCcw,
  ShieldCheck,
  Info,
  Smartphone
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import api from "@/api/axiosInstance"

export interface DeviceCalibrationProfile {
  pixels_per_mm: number
  ppi: number
  tilt_degrees: number
  camera_distance_mm?: number
  timestamp: string
}

interface BurnerCalibrationResponse {
  success: boolean
  message: string
  pixels_per_mm?: number
  ppi?: number
  marker_size_px?: number
  tilt_degrees?: number
  camera_distance_mm?: number
  annotated_preview_base64?: string
  annotated_marker_base64?: string
}

interface BurnerCalibrationModalProps {
  isOpen: boolean
  onClose: () => void
  currentProfile: DeviceCalibrationProfile | null
  onSaveProfile: (profile: DeviceCalibrationProfile | null) => void
}

export function BurnerCalibrationModal({
  isOpen,
  onClose,
  currentProfile,
  onSaveProfile,
}: BurnerCalibrationModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isCalibrating, setIsCalibrating] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [calibResult, setCalibResult] = useState<BurnerCalibrationResponse | null>(null)

  if (!isOpen) return null

  const processCalibrationFile = async (file: File) => {
    setIsCalibrating(true)
    setErrorMsg(null)
    setCalibResult(null)

    try {
      const formData = new FormData()
      formData.append("file", file)
      formData.append("marker_size_mm", "50.0")

      const res = await api.post<BurnerCalibrationResponse>("/api/calibrate/burner", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })

      if (res.data.success) {
        setCalibResult(res.data)
      } else {
        setErrorMsg(res.data.message || "Failed to locate 50mm ArUco marker in image.")
      }
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } }; message?: string }
      setErrorMsg(errorObj.response?.data?.detail || errorObj.message || "Network error during calibration.")
    } finally {
      setIsCalibrating(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = e.target.files?.[0]
    if (picked) processCalibrationFile(picked)
    e.target.value = ""
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) processCalibrationFile(dropped)
  }

  const loadDemoBurnerPreset = async () => {
    try {
      let res = await fetch("/samples/demo_burner_card_shot.jpg")
      if (!res.ok) {
        const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000"
        res = await fetch(`${baseUrl}/uploads/demo_burner_card_shot.jpg`)
      }
      if (!res.ok) throw new Error("Could not fetch demo burner sample")
      const blob = await res.blob()
      const sampleFile = new File([blob], "demo_burner_card_shot.jpg", { type: "image/jpeg" })
      await processCalibrationFile(sampleFile)
    } catch (err) {
      console.error("Failed to load demo burner shot", err)
      setErrorMsg("Failed to load demo burner sample. Please upload manually.")
    }
  }

  const handleSaveAndLock = () => {
    if (!calibResult || !calibResult.pixels_per_mm || !calibResult.ppi) return

    const profile: DeviceCalibrationProfile = {
      pixels_per_mm: calibResult.pixels_per_mm,
      ppi: calibResult.ppi,
      tilt_degrees: calibResult.tilt_degrees ?? 0.0,
      camera_distance_mm: calibResult.camera_distance_mm,
      timestamp: new Date().toISOString(),
    }

    onSaveProfile(profile)
    onClose()
  }

  const handleClearProfile = () => {
    onSaveProfile(null)
    setCalibResult(null)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-2xl border border-border bg-card shadow-2xl text-card-foreground p-6 max-h-[90vh] overflow-y-auto">
        
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          aria-label="Close calibration modal"
        >
          <X className="size-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex size-10 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
            <Smartphone className="size-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold tracking-tight">Device Scale &amp; PPI Calibration</h2>
              <Badge variant="outline" className="text-[10px] font-mono border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
                Burner Mode
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Calibrate camera scale once, then grade subsequent onion lots without requiring the card in every frame
            </p>
          </div>
        </div>

        {/* Informative Explanation */}
        <div className="rounded-xl border border-border bg-muted/30 p-3 flex gap-2.5 text-xs text-muted-foreground mb-4">
          <Info className="size-4 shrink-0 text-cyan-600 dark:text-cyan-400 mt-0.5" />
          <p>
            Place the <strong>50mm ArUco Reference Card</strong> on your grading surface at standard inspection height. 
            The system detects the optical scale (pixels/mm, device PPI) and camera tilt angle. Once locked, all future 
            tray scans will automatically use this verified scale.
          </p>
        </div>

        {/* Existing Profile Status */}
        {currentProfile && !calibResult && (
          <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-3.5 mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="size-5 text-cyan-500 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-foreground">Active Device Profile Locked</p>
                <p className="text-[11px] text-muted-foreground font-mono">
                  Scale: {currentProfile.pixels_per_mm.toFixed(2)} px/mm • {currentProfile.ppi.toFixed(1)} PPI • Tilt: {currentProfile.tilt_degrees.toFixed(1)}°
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearProfile}
              className="h-7 text-xs text-destructive hover:bg-destructive/10"
            >
              <RotateCcw className="size-3.5 mr-1" /> Clear
            </Button>
          </div>
        )}

        {/* Upload Zone / Preset */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleFileChange}
        />

        <div
          onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="relative flex flex-col items-center justify-center p-6 border-2 border-dashed border-border rounded-xl bg-muted/10 hover:border-cyan-500/60 hover:bg-muted/20 cursor-pointer transition-all duration-200 text-center mb-3"
        >
          {isCalibrating ? (
            <div className="flex flex-col items-center gap-2 py-4">
              <Loader2 className="size-8 animate-spin text-cyan-600 dark:text-cyan-400" />
              <p className="text-xs font-medium">Detecting ArUco Marker &amp; Computing Optical Scale...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <div className="size-10 rounded-full bg-cyan-500/10 flex items-center justify-center text-cyan-600 dark:text-cyan-400">
                <UploadCloud className="size-5" />
              </div>
              <div>
                <p className="text-xs font-medium text-foreground">
                  Drop initial ArUco card photo here, or <span className="text-cyan-600 dark:text-cyan-400 underline">browse</span>
                </p>
                <p className="text-[10px] text-muted-foreground">
                  Supports JPG, PNG, WEBP containing a 50mm ArUco marker
                </p>
              </div>
            </div>
          )}
        </div>

        {/* 1-Click Demo Burner Shot Preset */}
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] text-muted-foreground">Quick viva testing:</span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={(e) => { e.stopPropagation(); loadDemoBurnerPreset(); }}
            disabled={isCalibrating}
            className="h-7 text-xs border-cyan-500/30 hover:bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 font-medium"
          >
            <Sparkles className="size-3.5 mr-1.5 text-cyan-500" />
            1-Click Demo Burner Card Shot
          </Button>
        </div>

        {/* Error Callout */}
        {errorMsg && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2 mb-4">
            <AlertCircle className="size-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Calibration Success & Preview */}
        {calibResult && calibResult.success && (
          <div className="space-y-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4 animate-in fade-in duration-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold text-xs">
                <CheckCircle2 className="size-4" />
                <span>Optical Scale Calibrated Successfully</span>
              </div>
              <Badge className="bg-emerald-600 hover:bg-emerald-600 text-[10px]">
                Valid 50mm Marker
              </Badge>
            </div>

            {/* Preview with overlay */}
            {(calibResult.annotated_preview_base64 || calibResult.annotated_marker_base64) && (
              <div className="relative rounded-lg overflow-hidden border border-border shadow-sm max-h-48 flex justify-center bg-black/20">
                <img
                  src={
                    (calibResult.annotated_preview_base64 || calibResult.annotated_marker_base64)!.startsWith("data:")
                      ? (calibResult.annotated_preview_base64 || calibResult.annotated_marker_base64)!
                      : `data:image/jpeg;base64,${calibResult.annotated_preview_base64 || calibResult.annotated_marker_base64}`
                  }
                  alt="Calibration overlay"
                  className="max-h-48 object-contain"
                />
              </div>
            )}

            {/* Metrics HUD */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="p-2.5 rounded-lg border border-border bg-card/60 text-center">
                <p className="text-[10px] text-muted-foreground uppercase font-semibold">Scale</p>
                <p className="text-sm font-bold font-mono text-cyan-600 dark:text-cyan-400">
                  {calibResult.pixels_per_mm?.toFixed(2)} <span className="text-[10px]">px/mm</span>
                </p>
              </div>

              <div className="p-2.5 rounded-lg border border-border bg-card/60 text-center">
                <p className="text-[10px] text-muted-foreground uppercase font-semibold">Device PPI</p>
                <p className="text-sm font-bold font-mono text-foreground">
                  {calibResult.ppi?.toFixed(1)} <span className="text-[10px]">PPI</span>
                </p>
              </div>

              <div className="p-2.5 rounded-lg border border-border bg-card/60 text-center">
                <p className="text-[10px] text-muted-foreground uppercase font-semibold">Tilt Angle</p>
                <p className="text-sm font-bold font-mono text-foreground">
                  {calibResult.tilt_degrees?.toFixed(1)}°
                </p>
              </div>

              <div className="p-2.5 rounded-lg border border-border bg-card/60 text-center">
                <p className="text-[10px] text-muted-foreground uppercase font-semibold">Distance</p>
                <p className="text-sm font-bold font-mono text-foreground">
                  {calibResult.camera_distance_mm ? `${calibResult.camera_distance_mm.toFixed(0)} mm` : "Normal"}
                </p>
              </div>
            </div>

            {/* Save & Lock CTA */}
            <Button
              className="w-full bg-cyan-600 hover:bg-cyan-700 text-white font-semibold text-xs shadow-md"
              onClick={handleSaveAndLock}
            >
              <ShieldCheck className="size-4 mr-1.5" />
              Save &amp; Lock Device Calibration
            </Button>
          </div>
        )}

        {/* Footer info / Close */}
        <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
          <span>Target Standard: 50.0mm DICT_4X4_50 Card</span>
          <Button variant="outline" size="sm" onClick={onClose} className="h-8">
            Cancel
          </Button>
        </div>

      </div>
    </div>
  )
}
