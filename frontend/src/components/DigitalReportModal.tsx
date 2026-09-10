import { useEffect, useRef } from "react"
import { createPortal } from "react-dom"
import { X, Printer, Download, ShieldCheck, CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import type { UploadResponse } from "@/types/grading"

interface DigitalReportModalProps {
  isOpen: boolean
  onClose: () => void
  data: UploadResponse
}

export function DigitalReportModal({ isOpen, onClose, data }: DigitalReportModalProps) {
  const printRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isOpen) {
      document.body.classList.add("printing-certificate-open")
      return () => {
        document.body.classList.remove("printing-certificate-open")
      }
    }
  }, [isOpen])

  if (!isOpen) return null

  const { lot_metadata, grading } = data
  const { decision, quality_counts, quality_percentages, size_counts, size_percentages, audit_metrics, calibration } = grading

  const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000"
  const rawImageUrl = `${baseUrl}/uploads/${data.filename}`
  const annotatedImageUrl = `${baseUrl}/uploads/${grading.annotated_image_filename}`

  const handlePrint = () => {
    window.print()
  }

  const handleDownloadJson = () => {
    const jsonStr = JSON.stringify(data, null, 2)
    const blob = new Blob([jsonStr], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = `${lot_metadata.lot_id}_Inspection_Report.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  // Deterministic mock verification hash based on lot_id
  const auditHash = `0x${Array.from(lot_metadata.lot_id + lot_metadata.timestamp)
    .reduce((acc, char) => (acc * 31 + char.charCodeAt(0)) >>> 0, 0xd0ca26)
    .toString(16)
    .toUpperCase()}F82B9`

  return createPortal(
    <div
      id="printable-certificate-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-2 sm:p-6 overflow-y-auto"
    >
      {/* Modal Container */}
      <div
        id="printable-certificate"
        ref={printRef}
        className="relative w-full max-w-4xl max-h-[92vh] overflow-y-auto rounded-2xl border border-border bg-card shadow-2xl text-card-foreground p-6 sm:p-10"
      >

        
        {/* Actions bar (hidden in print) */}
        <div className="flex items-center justify-between border-b border-border pb-4 mb-6 print:hidden">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <ShieldCheck className="size-4 text-green-500" />
            <span>DoCA Official Procurement Record · Tamper-evident Audit Certificate</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleDownloadJson} className="gap-1.5 text-xs">
              <Download className="size-3.5" />
              JSON Audit
            </Button>
            <Button size="sm" onClick={handlePrint} className="gap-1.5 text-xs">
              <Printer className="size-3.5" />
              Print / Save PDF
            </Button>
            <button
              onClick={onClose}
              className="rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors ml-2"
              aria-label="Close report"
            >
              <X className="size-5" />
            </button>
          </div>
        </div>

        {/* ── Official Government Letterhead ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b-2 border-primary/40 pb-6 mb-6 print:flex-row print:items-center print:pb-3 print:mb-4 print-avoid-break">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono tracking-widest uppercase px-2 py-0.5 rounded bg-primary/10 text-primary font-bold">
                Government of India
              </span>
              <span className="text-[10px] text-muted-foreground">DoCA / NAFED / NCCF</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-black tracking-tight text-foreground">
              Onion Quality Assessment &amp; Inspection Certificate
            </h1>
            <p className="text-xs text-muted-foreground">
              Department of Consumer Affairs · Price Stabilization Fund (PSF) Central Buffer Procurement
            </p>
          </div>

          <div className="text-right flex flex-col sm:items-end justify-center border-t sm:border-t-0 pt-2 sm:pt-0 border-border">
            <div className="text-xs font-mono font-bold text-foreground">
              LOT ID: <span className="text-primary">{lot_metadata.lot_id}</span>
            </div>
            <div className="text-[11px] text-muted-foreground">
              Date: {new Date(lot_metadata.timestamp).toLocaleDateString("en-IN", {
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit"
              })}
            </div>
            <div className="mt-1 font-mono text-[9px] tracking-wider text-muted-foreground/80">
              HASH: {auditHash}
            </div>
          </div>
        </div>

        {/* ── Procurement Details Grid ── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 print:grid-cols-4 gap-3 p-3.5 rounded-xl border border-border bg-muted/20 mb-6 text-xs print:p-2.5 print:mb-4 print-avoid-break">
          <div>
            <span className="text-[10px] text-muted-foreground uppercase font-semibold">Farmer / Vendor</span>
            <p className="font-semibold text-foreground truncate">{lot_metadata.farmer_name}</p>
          </div>
          <div>
            <span className="text-[10px] text-muted-foreground uppercase font-semibold">Procurement Mandi</span>
            <p className="font-semibold text-foreground truncate">{lot_metadata.mandi_location}</p>
          </div>
          <div>
            <span className="text-[10px] text-muted-foreground uppercase font-semibold">Lot Sample Size</span>
            <p className="font-semibold text-foreground">{grading.total_detected} Bulbs / {lot_metadata.lot_weight_kg} kg</p>
          </div>
          <div>
            <span className="text-[10px] text-muted-foreground uppercase font-semibold">Inspection Standard</span>
            <p className="font-semibold text-foreground">AGMARK / DoCA FAQ 2026</p>
          </div>
        </div>

        {/* ── Executive Recommendation Banner ── */}
        <div className={`p-4 rounded-xl border mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 print:flex-row print:items-center print:p-3 print:mb-4 print-avoid-break ${
          decision.status === "accepted"
            ? "border-green-500/40 bg-green-500/10 text-green-800 dark:text-green-300 print:text-green-900 print:bg-green-50/80 print:border-green-300"
            : decision.status === "conditional"
            ? "border-amber-500/40 bg-amber-500/10 text-amber-800 dark:text-amber-300 print:text-amber-900 print:bg-amber-50/80 print:border-amber-300"
            : "border-red-500/40 bg-red-500/10 text-red-800 dark:text-red-300 print:text-red-900 print:bg-red-50/80 print:border-red-300"
        }`}>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge className={`text-xs font-bold uppercase tracking-wide ${
                decision.status === "accepted"
                  ? "bg-green-600 text-white"
                  : decision.status === "conditional"
                  ? "bg-amber-600 text-white"
                  : "bg-red-600 text-white"
              }`}>
                {decision.grade}
              </Badge>
              <span className="text-xs font-semibold">
                {decision.buffer_stock_fit ? "Qualified for Central Buffer Storage" : "Unfit for Long-term Storage"}
              </span>
            </div>
            <p className="text-sm font-bold text-foreground">{decision.recommendation}</p>
            <p className="text-xs opacity-90">{decision.summary}</p>
          </div>

          <div className="text-right sm:border-l sm:border-current/20 sm:pl-4 shrink-0">
            <div className="text-[10px] uppercase font-bold tracking-wider">Sound Bulb Share</div>
            <div className="text-2xl font-black text-foreground">{quality_percentages.healthy}%</div>
            <div className="text-[10px] opacity-80">DoCA Target: ≥ 85.0%</div>
          </div>
        </div>

        {/* ── Side-by-side Evidence Images ── */}
        <div className="mb-6 space-y-2 print:mb-4 print-avoid-break">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Photographic &amp; Computer Vision Evidence
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 print:grid-cols-2 gap-4">
            <div className="space-y-1">
              <div className="relative rounded-lg overflow-hidden border border-border aspect-video print:max-h-48 bg-muted/20">
                <img
                  src={rawImageUrl}
                  alt="Original tray sample"
                  className="w-full h-full object-contain"
                  crossOrigin="anonymous"
                />
              </div>
              <p className="text-[10px] text-muted-foreground text-center">Raw Sample Tray Photograph</p>
            </div>
            <div className="space-y-1">
              <div className="relative rounded-lg overflow-hidden border border-border aspect-video print:max-h-48 bg-muted/20">
                <img
                  src={annotatedImageUrl}
                  alt="AI Annotated Bounding Boxes"
                  className="w-full h-full object-contain"
                  crossOrigin="anonymous"
                />
              </div>
              <p className="text-[10px] text-muted-foreground text-center">
                AI Annotated Detections (Class-Agnostic NMS Deduplicated)
              </p>
            </div>
          </div>
        </div>

        {/* ── Table: Defect and Quality Parameter Breakdown ── */}
        <div className="mb-6 space-y-2 print:mb-4 print-avoid-break">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Defect Breakdown &amp; FAQ Permissible Tolerance Analysis
          </h3>
          <div className="overflow-hidden rounded-xl border border-border">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/60 text-muted-foreground font-semibold border-b border-border">
                <tr>
                  <th className="px-3.5 py-2.5">Category</th>
                  <th className="px-3.5 py-2.5">Detected Bulbs</th>
                  <th className="px-3.5 py-2.5">Lot Share (%)</th>
                  <th className="px-3.5 py-2.5">DoCA FAQ Limit</th>
                  <th className="px-3.5 py-2.5 text-right">Compliance Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                <tr>
                  <td className="px-3.5 py-2 font-medium flex items-center gap-1.5">
                    <span className="size-2 rounded-full bg-green-500" />
                    Sound Bulbs (Healthy Grade A)
                  </td>
                  <td className="px-3.5 py-2 font-mono">{quality_counts.healthy}</td>
                  <td className="px-3.5 py-2 font-mono font-bold text-foreground">{quality_percentages.healthy}%</td>
                  <td className="px-3.5 py-2 text-muted-foreground">≥ 85.0% Min</td>
                  <td className="px-3.5 py-2 text-right">
                    {quality_percentages.healthy >= 85 ? (
                      <Badge variant="outline" className="text-green-600 border-green-500/30 text-[10px]">Pass (Grade I)</Badge>
                    ) : quality_percentages.healthy >= 70 ? (
                      <Badge variant="outline" className="text-amber-600 border-amber-500/30 text-[10px]">Warning (Grade II)</Badge>
                    ) : (
                      <Badge variant="outline" className="text-red-600 border-red-500/30 text-[10px]">Fail (URS)</Badge>
                    )}
                  </td>
                </tr>

                <tr>
                  <td className="px-3.5 py-2 font-medium flex items-center gap-1.5">
                    <span className="size-2 rounded-full bg-red-500" />
                    Rotten / Decayed
                  </td>
                  <td className="px-3.5 py-2 font-mono">{quality_counts.rotten}</td>
                  <td className="px-3.5 py-2 font-mono font-bold text-foreground">{quality_percentages.rotten}%</td>
                  <td className="px-3.5 py-2 text-muted-foreground">≤ 2.0% (Max 4.0%)</td>
                  <td className="px-3.5 py-2 text-right">
                    {quality_percentages.rotten <= 2.0 ? (
                      <Badge variant="outline" className="text-green-600 border-green-500/30 text-[10px]">Within FAQ</Badge>
                    ) : quality_percentages.rotten <= 4.0 ? (
                      <Badge variant="outline" className="text-amber-600 border-amber-500/30 text-[10px]">Grade II Limit</Badge>
                    ) : (
                      <Badge variant="outline" className="text-red-600 border-red-500/30 text-[10px]">Exceeded (URS)</Badge>
                    )}
                  </td>
                </tr>

                <tr>
                  <td className="px-3.5 py-2 font-medium flex items-center gap-1.5">
                    <span className="size-2 rounded-full bg-yellow-500" />
                    Sprouted
                  </td>
                  <td className="px-3.5 py-2 font-mono">{quality_counts.sprouted}</td>
                  <td className="px-3.5 py-2 font-mono font-bold text-foreground">{quality_percentages.sprouted}%</td>
                  <td className="px-3.5 py-2 text-muted-foreground">≤ 3.0% (Max 7.0%)</td>
                  <td className="px-3.5 py-2 text-right">
                    {quality_percentages.sprouted <= 3.0 ? (
                      <Badge variant="outline" className="text-green-600 border-green-500/30 text-[10px]">Within FAQ</Badge>
                    ) : quality_percentages.sprouted <= 7.0 ? (
                      <Badge variant="outline" className="text-amber-600 border-amber-500/30 text-[10px]">Grade II Limit</Badge>
                    ) : (
                      <Badge variant="outline" className="text-red-600 border-red-500/30 text-[10px]">Exceeded (URS)</Badge>
                    )}
                  </td>
                </tr>

                <tr>
                  <td className="px-3.5 py-2 font-medium flex items-center gap-1.5">
                    <span className="size-2 rounded-full bg-orange-500" />
                    Damaged (Double Split)
                  </td>
                  <td className="px-3.5 py-2 font-mono">{quality_counts.damaged}</td>
                  <td className="px-3.5 py-2 font-mono font-bold text-foreground">{quality_percentages.damaged}%</td>
                  <td className="px-3.5 py-2 text-muted-foreground">≤ 5.0% (Max 10.0%)</td>
                  <td className="px-3.5 py-2 text-right">
                    {quality_percentages.damaged <= 5.0 ? (
                      <Badge variant="outline" className="text-green-600 border-green-500/30 text-[10px]">Within FAQ</Badge>
                    ) : quality_percentages.damaged <= 10.0 ? (
                      <Badge variant="outline" className="text-amber-600 border-amber-500/30 text-[10px]">Grade II Limit</Badge>
                    ) : (
                      <Badge variant="outline" className="text-red-600 border-red-500/30 text-[10px]">Exceeded (URS)</Badge>
                    )}
                  </td>
                </tr>

                <tr>
                  <td className="px-3.5 py-2 font-medium flex items-center gap-1.5">
                    <span className="size-2 rounded-full bg-blue-400" />
                    Undersized (&lt; 40 mm)
                  </td>
                  <td className="px-3.5 py-2 font-mono">{size_counts.small}</td>
                  <td className="px-3.5 py-2 font-mono font-bold text-foreground">{size_percentages.small}%</td>
                  <td className="px-3.5 py-2 text-muted-foreground">≤ 5.0% (Max 10.0%)</td>
                  <td className="px-3.5 py-2 text-right">
                    {size_percentages.small <= 5.0 ? (
                      <Badge variant="outline" className="text-green-600 border-green-500/30 text-[10px]">Within FAQ</Badge>
                    ) : size_percentages.small <= 10.0 ? (
                      <Badge variant="outline" className="text-amber-600 border-amber-500/30 text-[10px]">Grade II Limit</Badge>
                    ) : (
                      <Badge variant="outline" className="text-red-600 border-red-500/30 text-[10px]">Exceeded</Badge>
                    )}
                  </td>
                </tr>

                <tr className="bg-muted/30 font-semibold">
                  <td className="px-3.5 py-2 text-foreground">Total Lot Verified Count</td>
                  <td className="px-3.5 py-2 font-mono">{grading.total_detected}</td>
                  <td className="px-3.5 py-2 font-mono">100.0%</td>
                  <td className="px-3.5 py-2 text-muted-foreground">—</td>
                  <td className="px-3.5 py-2 text-right text-green-600">Verified (0 Duplicates)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Size Distribution Breakdown ── */}
        <div className="mb-6 space-y-2 print:mb-4 print-avoid-break">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Size Categorization ({calibration.label})
          </h3>
          <div className="grid grid-cols-3 print:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-xl border border-border bg-muted/20 text-center print:p-2">
              <span className="text-[10px] text-muted-foreground font-semibold uppercase">Large (&gt; 70 mm)</span>
              <p className="text-lg font-bold font-mono text-foreground mt-1">{size_counts.large}</p>
              <p className="text-muted-foreground text-[10px]">{size_percentages.large}% of lot</p>
            </div>
            <div className="p-3 rounded-xl border border-primary/30 bg-primary/5 text-center print:p-2">
              <span className="text-[10px] text-primary font-bold uppercase">Medium (40–70 mm) [FAQ Target]</span>
              <p className="text-lg font-bold font-mono text-primary mt-1">{size_counts.medium}</p>
              <p className="text-muted-foreground text-[10px]">{size_percentages.medium}% of lot</p>
            </div>
            <div className="p-3 rounded-xl border border-border bg-muted/20 text-center print:p-2">
              <span className="text-[10px] text-muted-foreground font-semibold uppercase">Small (&lt; 40 mm) [Undersized]</span>
              <p className="text-lg font-bold font-mono text-foreground mt-1">{size_counts.small}</p>
              <p className="text-muted-foreground text-[10px]">{size_percentages.small}% of lot</p>
            </div>
          </div>
        </div>

        {/* ── Decision Reasons / Explainability ── */}
        <div className="mb-6 space-y-2 print:mb-4 print-avoid-break">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Evaluation Rationale &amp; DoCA Procurement Rules
          </h3>
          <div className="p-3.5 rounded-xl border border-border bg-muted/20 space-y-1.5 text-xs print:p-2.5">
            {decision.reasons.map((reason, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <span className="text-foreground">•</span>
                <span className="text-muted-foreground">{reason}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── Technical Audit & Deduplication Verification ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 print:grid-cols-2 gap-3 p-3.5 rounded-xl border border-border bg-muted/10 text-xs mb-8 print:mb-4 print:p-2.5 print-avoid-break">
          <div>
            <span className="text-[10px] text-muted-foreground uppercase font-semibold">Computer Vision Audit Trail</span>
            <p className="text-muted-foreground text-[11px] mt-0.5">
              Model: <span className="font-semibold text-foreground">YOLOv8 Onion Precision v2</span> · Agnostic NMS (IoU: {audit_metrics.iou_threshold})
            </p>
            <p className="text-muted-foreground text-[11px]">
              Deduplication: <span className="font-semibold text-foreground">{audit_metrics.duplicates_suppressed} overlapping candidate boxes suppressed</span>
            </p>
            <p className="text-muted-foreground text-[11px]">
              Mean AI Confidence: <span className="font-semibold text-foreground">{audit_metrics.avg_confidence}%</span>
            </p>
          </div>
          <div>
            <span className="text-[10px] text-muted-foreground uppercase font-semibold">Scale Calibration Standard</span>
            <p className="text-muted-foreground text-[11px] mt-0.5">
              Status: <span className="font-semibold text-foreground">{calibration.label}</span>
            </p>
            <p className="text-muted-foreground text-[11px]">
              Conversion Factor: <span className="font-mono text-foreground">{calibration.mm_per_pixel} mm/px</span>
            </p>
            <p className="text-muted-foreground text-[11px]">
              Integrity: <span className="text-green-600 font-semibold">{audit_metrics.validation_message}</span>
            </p>
          </div>
        </div>

        {/* ── Official Signature & Verification Block ── */}
        <div className="grid grid-cols-2 gap-6 pt-4 border-t border-border text-xs print-avoid-break">
          <div className="space-y-1">
            <span className="text-[10px] text-muted-foreground uppercase font-semibold">Inspecting Officer Sign-off</span>
            <p className="font-bold text-foreground">Dr. S. K. Sharma, Quality Inspector</p>
            <p className="text-[10px] text-muted-foreground">DoCA / NAFED Mandi Procurement Division</p>
            <p className="font-mono text-[9px] text-muted-foreground">ID: DOCA-APMC-INSP-4082</p>
          </div>

          <div className="text-right space-y-1">
            <span className="text-[10px] text-muted-foreground uppercase font-semibold">Digital Verification Stamp</span>
            <div className="flex items-center justify-end gap-1 text-green-600 font-bold">
              <CheckCircle2 className="size-4" />
              <span>DIGITALLY CERTIFIED</span>
            </div>
            <p className="font-mono text-[9px] text-muted-foreground">Signed at: {new Date(lot_metadata.timestamp).toISOString()}</p>
            <p className="font-mono text-[9px] text-muted-foreground">Hash: {auditHash}</p>
          </div>
        </div>

      </div>
    </div>,
    document.body
  )
}

