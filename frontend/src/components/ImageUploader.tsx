import { useCallback, useEffect, useRef, useState } from "react"
import { UploadCloud, X, ImageIcon, FileWarning, CheckCircle2, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import * as React from "react";

type UploadState = "idle" | "dragging" | "preview" | "error"

interface ImageUploaderProps {
	onUpload: (file: File) => Promise<void>;
	isUploading: boolean;
	uploadError: string | null;
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


	const handleAnalyze = async () => {
		if (!file) return
		try {
			await onUpload(file)
			// Success handling could be added here later (e.g., redirect to results)
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
		// Reset input value so the same file can be re-selected after clearing
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

			{/* Upload zone */}
			<div
				onClick={openPicker}
				onDragOver={handleDragOver}
				onDragLeave={handleDragLeave}
				onDrop={handleDrop}
				className={cn(
					"relative flex min-h-64 w-full cursor-pointer flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed transition-all duration-200 select-none",
					// Idle
					state === "idle" &&
					"border-border bg-muted/20 hover:border-primary/60 hover:bg-muted/40",
					// Dragging over
					state === "dragging" &&
					"scale-[1.01] border-primary bg-primary/5 shadow-lg shadow-primary/10",
					// Error
					state === "error" &&
					"border-destructive bg-destructive/5 cursor-default",
					// Preview — not interactive as a zone
					state === "preview" && "cursor-default border-border/50 bg-muted/10",
				)}
			>
				{/* ── Idle / dragging state ── */}
				{(state === "idle" || state === "dragging") && (
					<div className="flex flex-col items-center gap-3 px-8 py-6 text-center">
						<div
							className={cn(
								"flex size-14 items-center justify-center rounded-full border border-border transition-colors duration-200",
								state === "dragging"
									? "border-primary bg-primary/10 text-primary"
									: "bg-muted text-muted-foreground",
							)}
						>
							<UploadCloud className="size-7" />
						</div>
						<div className="flex flex-col gap-1">
							<p className="text-sm font-medium text-foreground">
								{state === "dragging"
									? "Release to upload"
									: "Drag & drop your image here"}
							</p>
							<p className="text-xs text-muted-foreground">
								or{" "}
								<span className="font-medium text-primary underline underline-offset-2">
                  click to browse files
                </span>
							</p>
						</div>
						<div className="flex flex-wrap justify-center gap-1.5">
							{["JPG", "PNG", "WEBP", "TIFF", "BMP"].map((fmt) => (
								<Badge key={fmt} variant="secondary" className="text-xs font-mono">
									{fmt}
								</Badge>
							))}
						</div>
					</div>
				)}

				{/* ── Error state ── */}
				{state === "error" && (
					<div className="flex flex-col items-center gap-3 px-8 py-6 text-center">
						<div className="flex size-14 items-center justify-center rounded-full border border-destructive/30 bg-destructive/10 text-destructive">
							<FileWarning className="size-7" />
						</div>
						<div className="flex flex-col gap-1">
							<p className="text-sm font-medium text-destructive">
								Invalid file type
							</p>
							<p className="text-xs text-muted-foreground">{errorMsg}</p>
						</div>
					</div>
				)}

				{/* ── Preview state ── */}
				{state === "preview" && file && preview && (
					<div className="flex w-full flex-col items-center gap-4 px-6 py-6">
						{/* Image preview */}
						<div className="relative w-full max-w-sm overflow-hidden rounded-lg border border-border shadow-md">
							<img
								src={preview}
								alt="Selected onion image"
								className="h-48 w-full object-cover"
							/>
							{/* Remove button */}
							<button
								onClick={(e) => { e.stopPropagation(); handleClear() }}
								className="absolute right-2 top-2 flex size-7 items-center justify-center rounded-full bg-background/80 text-foreground backdrop-blur-sm transition-colors hover:bg-background hover:text-destructive"
								aria-label="Remove image"
							>
								<X className="size-4" />
							</button>
						</div>

						{/* File metadata */}
						<div className="flex w-full max-w-sm items-center gap-3 rounded-lg border border-border bg-muted/30 px-3 py-2.5">
							<div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
								<ImageIcon className="size-4" />
							</div>
							<div className="flex min-w-0 flex-col gap-0.5">
								<p className="truncate text-xs font-medium text-foreground">
									{file.name}
								</p>
								<p className="text-xs text-muted-foreground">
									{formatBytes(file.size)} · {file.type}
								</p>
							</div>
							<Badge variant="secondary" className="ml-auto shrink-0 gap-1 text-xs">
								<CheckCircle2 className="size-3 text-green-500" />
								Ready
							</Badge>
						</div>
					</div>
				)}
			</div>

			{/* Analyze CTA */}
			<Button
				size="lg"
				disabled={state !== "preview" || isUploading}
				className="w-full gap-2"
				onClick={handleAnalyze}
			>
				{isUploading && <Loader2 className="size-4 animate-spin" />}
				{!isUploading && state !== "preview" && <Loader2 className="size-4 opacity-0" />}
				{isUploading ? "Uploading..." : state === "preview" ? "Analyse Onion Quality" : "Select an image to continue"}
			</Button>

			{uploadError && (
				<p className="text-center text-sm font-medium text-destructive">
					{uploadError}
				</p>
			)}

			{/* Re-upload link when in preview */}
			{state === "preview" && !isUploading && (
				<button
					onClick={openPicker}
					className="text-center text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
				>
					Choose a different image
				</button>
			)}
		</div>
	)
}
