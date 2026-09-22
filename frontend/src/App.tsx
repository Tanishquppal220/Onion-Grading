import { useState } from "react"
import { ScanSearch, ShieldCheck, ArrowLeft, BookOpen, Sparkles } from "lucide-react"
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ImageUploader } from "@/components/ImageUploader"
import { BackendStatus } from "@/components/BackendStatus"
import { ResultsPane } from "@/components/ResultsPane"
import { StandardsExplainerModal } from "@/components/StandardsExplainerModal"
import { useImageUpload } from "@/hooks/useImageUpload"

function App() {
	const { uploadImage, isUploading, result, error, clearResult } = useImageUpload()
	const [isStandardsModalOpen, setIsStandardsModalOpen] = useState(false)

	return (
		<div className="min-h-screen bg-background text-foreground overflow-x-hidden selection:bg-primary/20">
			{/* ── Top Navigation Bar ── */}
			<header className="sticky top-0 z-40 w-full border-b border-border/80 bg-background/90 backdrop-blur-md transition-all">
				<div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
					{/* Left: Brand Identity */}
					<div className="flex items-center gap-3">
						<div className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-md shadow-primary/20">
							<ScanSearch className="size-5" />
						</div>
						<div className="flex flex-col">
							<div className="flex items-center gap-2">
								<span className="font-heading text-lg font-bold tracking-tight text-foreground">
									OnionGrade AI
								</span>
								<Badge variant="outline" className="text-[10px] font-mono border-primary/40 text-primary bg-primary/5">
									DoCA 45–65mm FAQ
								</Badge>
							</div>
							<span className="text-[11px] text-muted-foreground hidden sm:inline">
								Automated Mandi Quality Assessment &amp; Buffer-Stock Clearance
							</span>
						</div>
					</div>

					{/* Right: Actions & Status */}
					<div className="flex items-center gap-2.5">
						<Button
							variant="outline"
							size="sm"
							onClick={() => setIsStandardsModalOpen(true)}
							className="h-9 gap-1.5 text-xs font-medium border-border/80 hover:bg-muted"
						>
							<BookOpen className="size-3.5 text-primary" />
							<span className="hidden sm:inline">DoCA &amp; AGMARK Standards</span>
							<span className="sm:hidden">Standards</span>
						</Button>

						{result && (
							<Button
								variant="default"
								size="sm"
								onClick={clearResult}
								className="h-9 gap-1.5 text-xs font-semibold bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm"
							>
								<ArrowLeft className="size-3.5" />
								<span>New Inspection</span>
							</Button>
						)}

						<BackendStatus />
					</div>
				</div>
			</header>

			{/* ── Main Container ── */}
			<main className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl flex-col px-4 py-8 sm:px-6">
				{!result ? (
					/* ═══════════════════════════════════════════════════════
					   STATE 1: CLEAN, WELCOMING UPLOAD VIEW
					   ═══════════════════════════════════════════════════════ */
					<div className="mx-auto flex w-full max-w-3xl flex-col items-center gap-8 py-2">
						{/* Trust & Ministry Header */}
						<div className="flex flex-col items-center gap-2.5 text-center">
							<div className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
								<ShieldCheck className="size-3.5" />
								Government of India • Central Buffer Stock Quality Protocol
							</div>
							<h1 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
								Onion Quality Grading &amp; Sizing
							</h1>
							<p className="max-w-xl text-sm sm:text-base text-muted-foreground">
								Fast, non-contact quality evaluation for APMC mandis. Detects equatorial diameter (mm), flags spoilage defects, and generates official tamper-resistant PDF certificates.
							</p>
						</div>

						{/* 3-Step Interactive Process Banner */}
						<div className="grid w-full grid-cols-1 sm:grid-cols-3 gap-3 rounded-2xl border border-border/80 bg-card p-3.5 shadow-sm text-xs">
							<div className="flex items-center gap-3 rounded-xl bg-muted/40 p-2.5">
								<div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 font-bold text-primary">
									1
								</div>
								<div>
									<p className="font-semibold text-foreground">Capture Tray</p>
									<p className="text-[11px] text-muted-foreground">Photo with ArUco 50mm card</p>
								</div>
							</div>
							<div className="flex items-center gap-3 rounded-xl bg-muted/40 p-2.5">
								<div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 font-bold text-primary">
									2
								</div>
								<div>
									<p className="font-semibold text-foreground">AI Auto-Inspection</p>
									<p className="text-[11px] text-muted-foreground">Sub-mm sizing &amp; defect scan</p>
								</div>
							</div>
							<div className="flex items-center gap-3 rounded-xl bg-muted/40 p-2.5">
								<div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 font-bold text-primary">
									3
								</div>
								<div>
									<p className="font-semibold text-foreground">Audit Certificate</p>
									<p className="text-[11px] text-muted-foreground">Instant A4 PDF report</p>
								</div>
							</div>
						</div>

						{/* Main Upload Card */}
						<Card className="w-full border-border/80 shadow-lg rounded-2xl overflow-hidden">
							<CardHeader className="pb-4">
								<div className="flex items-center justify-between">
									<CardTitle className="text-xl font-bold flex items-center gap-2">
										<Sparkles className="size-5 text-primary" />
										<span>Start New Lot Inspection</span>
									</CardTitle>
									<Badge variant="secondary" className="text-xs">
										v2.1 Precision Engine
									</Badge>
								</div>
								<CardDescription className="text-xs sm:text-sm">
									Take a live camera photo of your inspection tray or drag &amp; drop an existing image.
								</CardDescription>
							</CardHeader>

							<CardContent className="space-y-4">
								<ImageUploader onUpload={uploadImage} isUploading={isUploading} uploadError={error} />
							</CardContent>

							<CardFooter className="flex flex-col items-start gap-2.5 pt-3 border-t border-border/60 bg-muted/20 text-xs">
								<div className="flex flex-wrap items-center gap-1.5">
									<span className="font-medium text-foreground text-[11px]">
										Statutory Classes Inspected:
									</span>
									{[
										{ label: "Grade A (Sound 45-65mm)", color: "bg-emerald-500" },
										{ label: "Rotten / Decay (Max 2%)", color: "bg-rose-500" },
										{ label: "Sprouted (Max 3%)", color: "bg-amber-500" },
										{ label: "Damaged / Double Split", color: "bg-purple-500" },
										{ label: "Undersized (<45mm)", color: "bg-blue-500" },
									].map(({ label, color }) => (
										<Badge key={label} variant="outline" className="gap-1.5 text-[11px] font-normal border-border/60">
											<span className={`size-1.5 rounded-full ${color}`} />
											{label}
										</Badge>
									))}
								</div>
								<p className="text-[10px] text-muted-foreground leading-relaxed">
									* In accordance with Government of India DoCA FAQ standards, double-split bulbs with ruptured outer tunics are graded under the official damaged quota due to accelerated decay risk during cold storage.
								</p>
							</CardFooter>
						</Card>
					</div>
				) : (
					/* ═══════════════════════════════════════════════════════
					   STATE 2: IMMERSIVE, INTUITIVE INSPECTION DASHBOARD
					   ═══════════════════════════════════════════════════════ */
					<div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
						{/* Active Inspection Sub-Bar */}
						<div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-primary/20 bg-primary/5 p-4 shadow-sm">
							<div className="flex items-center gap-3">
								<Button
									variant="outline"
									size="sm"
									onClick={clearResult}
									className="gap-1.5 text-xs font-semibold bg-background hover:bg-muted shadow-sm"
								>
									<ArrowLeft className="size-3.5" />
									<span>Back to Upload</span>
								</Button>
								<div>
									<div className="flex items-center gap-2">
										<span className="font-bold text-sm text-foreground">
											Lot Inspection: {result.lot_metadata?.lot_id || "LOT-001"}
										</span>
										<Badge variant="outline" className="text-[10px] font-mono border-primary/40 text-primary">
											Analyzed in {result.grading?.inference_time_ms ? `${result.grading.inference_time_ms.toFixed(0)}ms` : "Instant"}
										</Badge>
									</div>
									<p className="text-[11px] text-muted-foreground">
										{result.lot_metadata?.mandi_location || "APMC Center"} • Grower: {result.lot_metadata?.farmer_name || "Mandi Lot"}
									</p>
								</div>
							</div>

							<div className="flex items-center gap-2">
								<Button
									variant="outline"
									size="sm"
									onClick={() => setIsStandardsModalOpen(true)}
									className="h-8 text-xs gap-1.5 border-border/80"
								>
									<BookOpen className="size-3.5 text-primary" />
									<span>View FAQ Rules</span>
								</Button>
							</div>
						</div>

						{/* Full-Fidelity Results Pane */}
						<ResultsPane
							data={result.grading}
							lotMetadata={result.lot_metadata}
							rawImageFilename={result.filename}
						/>
					</div>
				)}
			</main>

			{/* ── Footer ── */}
			<footer className="border-t border-border/60 bg-muted/20 py-6 text-center text-xs text-muted-foreground">
				<div className="mx-auto flex max-w-6xl flex-col sm:flex-row items-center justify-between gap-2 px-4">
					<span>Problem Statement #26031 • Department of Consumer Affairs (DoCA) &amp; NAFED</span>
					<span>AI Vision Pipeline v2.1 • Sub-Millimeter ArUco Metrology</span>
				</div>
			</footer>

			{/* Standards Explainer Modal (Accessible from anywhere) */}
			<StandardsExplainerModal
				isOpen={isStandardsModalOpen}
				onClose={() => setIsStandardsModalOpen(false)}
			/>
		</div>
	)
}

export default App

