import { useState } from "react"
import { X, Ruler, Check, Info } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export interface CalibrationConfig {
  mode: "estimated" | "coin_25mm" | "tray_300mm" | "custom"
  custom_mm_per_pixel?: number
  reference_dimension_mm?: number
  reference_pixels?: number
}

interface CalibrationSettingsModalProps {
  isOpen: boolean
  onClose: () => void
  currentConfig: CalibrationConfig
  onSave: (config: CalibrationConfig) => void
}

export function CalibrationSettingsModal({
  isOpen,
  onClose,
  currentConfig,
  onSave,
}: CalibrationSettingsModalProps) {
  const [mode, setMode] = useState<CalibrationConfig["mode"]>(currentConfig.mode)
  const [customScale, setCustomScale] = useState<string>(
    currentConfig.custom_mm_per_pixel ? currentConfig.custom_mm_per_pixel.toString() : "0.635"
  )
  const [trayWidthMm, setTrayWidthMm] = useState<string>("300")
  const [trayPixels, setTrayPixels] = useState<string>("472")

  if (!isOpen) return null

  const handleSave = () => {
    if (mode === "custom") {
      const val = parseFloat(customScale)
      onSave({
        mode: "custom",
        custom_mm_per_pixel: !isNaN(val) && val > 0 ? val : 0.635,
      })
    } else if (mode === "tray_300mm") {
      const dim = parseFloat(trayWidthMm)
      const px = parseFloat(trayPixels)
      onSave({
        mode: "tray_300mm",
        reference_dimension_mm: !isNaN(dim) ? dim : 300,
        reference_pixels: !isNaN(px) ? px : 472,
        custom_mm_per_pixel: !isNaN(dim) && !isNaN(px) && px > 0 ? dim / px : 0.635,
      })
    } else if (mode === "coin_25mm") {
      onSave({
        mode: "coin_25mm",
        reference_dimension_mm: 25.0,
        reference_pixels: 40.0,
        custom_mm_per_pixel: 25.0 / 40.0,
      })
    } else {
      onSave({
        mode: "estimated",
      })
    }
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg rounded-2xl border border-border bg-card shadow-2xl text-card-foreground p-6">
        
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          aria-label="Close calibration modal"
        >
          <X className="size-5" />
        </button>

        <div className="flex items-center gap-3 mb-5">
          <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Ruler className="size-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold tracking-tight">Camera &amp; Size Scale Calibration</h2>
            <p className="text-xs text-muted-foreground">
              Define scale calibration to convert bounding box pixel dimensions into exact millimetres
            </p>
          </div>
        </div>

        {/* Informative callout */}
        <div className="rounded-xl border border-border bg-muted/30 p-3.5 flex gap-2.5 text-xs text-muted-foreground mb-4">
          <Info className="size-4 shrink-0 text-primary mt-0.5" />
          <p>
            Standard phone photos cannot guarantee physical millimetres without a reference scale or fixed distance.
            For certified mandi grading, calibrate against a standard tray or coin marker.
          </p>
        </div>

        {/* Options */}
        <div className="space-y-2.5 mb-6">
          {/* Estimated */}
          <label
            className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
              mode === "estimated"
                ? "border-primary bg-primary/5 text-foreground"
                : "border-border hover:bg-muted/30 text-muted-foreground"
            }`}
          >
            <input
              type="radio"
              name="calib_mode"
              checked={mode === "estimated"}
              onChange={() => setMode("estimated")}
              className="mt-0.5 text-primary"
            />
            <div className="text-xs space-y-0.5">
              <div className="font-semibold text-foreground flex items-center gap-1.5">
                Estimated Scale (Uncalibrated)
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">Default</span>
              </div>
              <p className="text-muted-foreground">
                Uses standard 40 PPI sensor estimation (~0.635 mm/px at ~60 cm camera distance).
              </p>
            </div>
          </label>

          {/* Reference Coin */}
          <label
            className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
              mode === "coin_25mm"
                ? "border-primary bg-primary/5 text-foreground"
                : "border-border hover:bg-muted/30 text-muted-foreground"
            }`}
          >
            <input
              type="radio"
              name="calib_mode"
              checked={mode === "coin_25mm"}
              onChange={() => setMode("coin_25mm")}
              className="mt-0.5 text-primary"
            />
            <div className="text-xs space-y-0.5">
              <div className="font-semibold text-foreground">
                ₹10 Reference Coin Marker (25 mm)
              </div>
              <p className="text-muted-foreground">
                Standard ₹10 coin placed on the sample tray as a known physical reference marker.
              </p>
            </div>
          </label>

          {/* Standard Tray */}
          <label
            className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
              mode === "tray_300mm"
                ? "border-primary bg-primary/5 text-foreground"
                : "border-border hover:bg-muted/30 text-muted-foreground"
            }`}
          >
            <input
              type="radio"
              name="calib_mode"
              checked={mode === "tray_300mm"}
              onChange={() => setMode("tray_300mm")}
              className="mt-0.5 text-primary"
            />
            <div className="text-xs space-y-1 w-full">
              <div className="font-semibold text-foreground">
                Standard Procurement Inspection Tray (300 mm)
              </div>
              <p className="text-muted-foreground">
                Calibrated against a standard 300 mm wide stainless steel grading tray.
              </p>
              {mode === "tray_300mm" && (
                <div className="grid grid-cols-2 gap-2 pt-2">
                  <div>
                    <label className="text-[10px] text-muted-foreground">Tray Width (mm)</label>
                    <Input
                      value={trayWidthMm}
                      onChange={(e) => setTrayWidthMm(e.target.value)}
                      className="h-8 text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground">Pixel Width in Frame</label>
                    <Input
                      value={trayPixels}
                      onChange={(e) => setTrayPixels(e.target.value)}
                      className="h-8 text-xs font-mono"
                    />
                  </div>
                </div>
              )}
            </div>
          </label>

          {/* Custom mm/px */}
          <label
            className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
              mode === "custom"
                ? "border-primary bg-primary/5 text-foreground"
                : "border-border hover:bg-muted/30 text-muted-foreground"
            }`}
          >
            <input
              type="radio"
              name="calib_mode"
              checked={mode === "custom"}
              onChange={() => setMode("custom")}
              className="mt-0.5 text-primary"
            />
            <div className="text-xs space-y-1 w-full">
              <div className="font-semibold text-foreground">
                Custom Calibration Factor
              </div>
              <p className="text-muted-foreground">
                Enter known millimetres per pixel for fixed camera mount rig.
              </p>
              {mode === "custom" && (
                <div className="pt-2">
                  <label className="text-[10px] text-muted-foreground">Scale (mm / pixel)</label>
                  <Input
                    value={customScale}
                    onChange={(e) => setCustomScale(e.target.value)}
                    className="h-8 text-xs font-mono w-40"
                    placeholder="e.g. 0.635"
                  />
                </div>
              )}
            </div>
          </label>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" onClick={handleSave} className="gap-1.5">
            <Check className="size-4" />
            Apply Calibration
          </Button>
        </div>

      </div>
    </div>
  )
}
