import { ScanSearch, ShieldCheck } from "lucide-react"
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ImageUploader } from "@/components/ImageUploader"
import { BackendStatus } from "@/components/BackendStatus"




function App() {

	return (
		<div className="min-h-screen bg-background">
			{/* ── Page wrapper ── */}
			<div className="mx-auto flex min-h-screen max-w-2xl flex-col px-4 py-12">

				{/* ── Header ── */}
				<header className="relative mb-10 flex flex-col items-center gap-3 text-center">
					{/* Backend status indicator — top right */}
					<div className="absolute right-0 top-0">
						<BackendStatus />
					</div>

					{/* Logo mark */}
					<div className="flex size-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg">
						<ScanSearch className="size-7" />
					</div>

					{/* Title */}
					<div className="flex flex-col gap-1">
						<div className="flex items-center justify-center gap-2">
							<h1 className="font-heading text-2xl font-semibold tracking-tight text-foreground">
								Onion Quality Assessment
							</h1>
							<Badge variant="secondary" className="text-xs">
								DoCA
							</Badge>
						</div>
						<p className="text-sm text-muted-foreground">
							AI-powered grading against AGMARK / FAQ procurement standards
						</p>
					</div>

					{/* Trust badge */}
					<div className="flex items-center gap-1.5 text-xs text-muted-foreground">
						<ShieldCheck className="size-3.5 text-green-500" />
						Ministry of Consumer Affairs, Food &amp; Public Distribution
					</div>
				</header>

				{/* ── Upload Card ── */}
				<Card className="w-full">
					<CardHeader>
						<CardTitle>Upload Onion Image</CardTitle>
						<CardDescription>
							Upload a photo of a single bulb or a full sample tray. The AI
							will detect each bulb, measure its size, and classify defects
							(Rotten, Sprouted, Damaged, Undersized) against DoCA standards.
						</CardDescription>
					</CardHeader>

					<CardContent>
						<ImageUploader />
					</CardContent>

					<CardFooter className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">
              Supported defect classes:
            </span>
						{[
							{ label: "Grade A", color: "text-green-500" },
							{ label: "Rotten", color: "text-red-500" },
							{ label: "Sprouted", color: "text-yellow-500" },
							{ label: "Damaged", color: "text-orange-500" },
							{ label: "Undersized", color: "text-blue-400" },
						].map(({ label, color }) => (
							<Badge key={label} variant="outline" className="gap-1 text-xs">
								<span className={`size-1.5 rounded-full bg-current ${color}`} />
								{label}
							</Badge>
						))}
					</CardFooter>
				</Card>

				{/* ── Footer ── */}
				<footer className="mt-8 text-center text-xs text-muted-foreground">
					Problem Statement #26031 · Department of Consumer Affairs (DoCA)
				</footer>
			</div>
		</div>
	)
}

export default App
