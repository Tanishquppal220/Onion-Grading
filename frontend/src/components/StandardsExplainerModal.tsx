import { X, BookOpen, CheckCircle, AlertTriangle, XCircle, ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"


interface StandardsExplainerModalProps {
  isOpen: boolean
  onClose: () => void
}

export function StandardsExplainerModal({ isOpen, onClose }: StandardsExplainerModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200 print:hidden">
      <div className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl border border-border bg-card shadow-2xl text-card-foreground p-6 sm:p-8">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          aria-label="Close standards guide"
        >
          <X className="size-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <BookOpen className="size-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight">DoCA &amp; AGMARK Onion Procurement Specifications</h2>
            <p className="text-xs text-muted-foreground">
              Fair Average Quality (FAQ) standards used by DoCA, NAFED, and NCCF for Price Stabilization Fund buffer procurement
            </p>
          </div>
        </div>

        {/* Standards Table */}
        <div className="overflow-hidden rounded-xl border border-border mb-6">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-muted/60 text-muted-foreground font-semibold border-b border-border">
              <tr>
                <th className="px-4 py-3">Grading Parameter</th>
                <th className="px-4 py-3 text-green-600 font-medium">Grade I (FAQ - Buffer)</th>
                <th className="px-4 py-3 text-amber-600 font-medium">Grade II (Conditional)</th>
                <th className="px-4 py-3 text-red-600 font-medium">URS (Rejection Limit)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              <tr>
                <td className="px-4 py-2.5 font-medium">Sound Bulbs (Grade A)</td>
                <td className="px-4 py-2.5 text-green-600">≥ 85.0% Minimum</td>
                <td className="px-4 py-2.5 text-amber-600">≥ 70.0% Minimum</td>
                <td className="px-4 py-2.5 text-red-600 font-semibold">&lt; 70.0% (Rejected)</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-medium">Rotten / Decayed Bulbs</td>
                <td className="px-4 py-2.5 text-green-600">≤ 2.0% Maximum</td>
                <td className="px-4 py-2.5 text-amber-600">≤ 4.0% Maximum</td>
                <td className="px-4 py-2.5 text-red-600 font-semibold">&gt; 4.0% (Storage Risk)</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-medium">Sprouted Bulbs</td>
                <td className="px-4 py-2.5 text-green-600">≤ 3.0% Maximum</td>
                <td className="px-4 py-2.5 text-amber-600">≤ 7.0% Maximum</td>
                <td className="px-4 py-2.5 text-red-600 font-semibold">&gt; 7.0% (Rapid Decay)</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-medium">Damaged / Double Split</td>
                <td className="px-4 py-2.5 text-green-600">≤ 5.0% Maximum</td>
                <td className="px-4 py-2.5 text-amber-600">≤ 10.0% Maximum</td>
                <td className="px-4 py-2.5 text-red-600 font-semibold">&gt; 10.0% (High Shrinkage)</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-medium">Undersized (&lt; 40 mm)</td>
                <td className="px-4 py-2.5 text-green-600">≤ 5.0% Maximum</td>
                <td className="px-4 py-2.5 text-amber-600">≤ 10.0% Maximum</td>
                <td className="px-4 py-2.5 text-red-600 font-semibold">&gt; 10.0% (Size Deduction)</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-medium">Standard Size Range</td>
                <td className="px-4 py-2.5 text-foreground" colSpan={3}>
                  Medium (40 mm – 70 mm) is the optimal FAQ procurement target for ventilated storage
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Explainability Callouts */}
        <div className="space-y-4 text-xs sm:text-sm">
          <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-2">
            <div className="flex items-center gap-2 font-semibold text-primary">
              <ShieldCheck className="size-4" />
              <span>Classification Mapping: Why "Double Split" counts as "Damaged"</span>
            </div>
            <p className="text-muted-foreground leading-relaxed">
              In official AGMARK / DoCA onion specifications, double split bulbs lack continuous protective outer dry scales (tunic).
              This structural rupture exposes internal fleshy scales to moisture loss and airborne spores of <em>Aspergillus niger</em> (black rot).
              Consequently, double split bulbs cannot survive 3–4 months of buffer stock storage and are classified under the official <strong>Damaged</strong> defect tolerance quota.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-3 space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-green-600 text-xs">
                <CheckCircle className="size-3.5" />
                Grade I (FAQ - Accepted)
              </div>
              <p className="text-xs text-muted-foreground">
                Qualified for long-term Central Buffer Stock storage under Price Stabilization Fund (PSF).
              </p>
            </div>

            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-amber-600 text-xs">
                <AlertTriangle className="size-3.5" />
                Grade II (Conditional)
              </div>
              <p className="text-xs text-muted-foreground">
                Accepted with proportional value deduction. Suitable for immediate retail distribution, not buffer.
              </p>
            </div>

            <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-3 space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-red-600 text-xs">
                <XCircle className="size-3.5" />
                URS (Rejected)
              </div>
              <p className="text-xs text-muted-foreground">
                Under Rejection Standard. Exceeds rot or defect limits; rejected to protect warehouse lots.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 flex justify-end">
          <Button onClick={onClose} variant="outline" size="sm">
            Got it
          </Button>
        </div>

      </div>
    </div>
  )
}
