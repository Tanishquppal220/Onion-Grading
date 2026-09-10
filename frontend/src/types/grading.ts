export interface QualityBreakdown {
  healthy: number
  rotten: number
  sprouted: number
  damaged: number
}

export interface QualityPercentages {
  healthy: number
  rotten: number
  sprouted: number
  damaged: number
}

export interface SizeBreakdown {
  small: number
  medium: number
  large: number
}

export interface SizePercentages {
  small: number
  medium: number
  large: number
}

export interface ComplianceRule {
  name: string
  category: string
  actual_value: number
  threshold_value: number
  unit: string
  passed: boolean
  status: "pass" | "warning" | "fail"
  description: string
}

export interface DecisionResult {
  grade: string
  status: "accepted" | "conditional" | "rejected"
  recommendation: string
  summary: string
  buffer_stock_fit: boolean
  reasons: string[]
  compliance_rules: ComplianceRule[]
}

export interface CalibrationInfo {
  mode: string
  mm_per_pixel: number
  is_calibrated: boolean
  label: string
  description: string
}

export interface AuditMetrics {
  total_detected: number
  raw_detections: number
  duplicates_suppressed: number
  avg_confidence: number
  nms_mode: string
  iou_threshold: number
  conf_threshold: number
  validation_passed: boolean
  validation_message: string
}

export interface GradingResult {
  onion: number
  double_split: number
  rotten: number
  sprout: number
  small: number
  medium: number
  large: number
  annotated_image_filename?: string

  total_detected: number
  quality_counts: QualityBreakdown
  quality_percentages: QualityPercentages
  size_counts: SizeBreakdown
  size_percentages: SizePercentages

  decision: DecisionResult
  calibration: CalibrationInfo
  audit_metrics: AuditMetrics
}

export interface LotMetadata {
  lot_id: string
  farmer_name: string
  mandi_location: string
  lot_weight_kg: number
  timestamp: string
}

export interface UploadResponse {
  status: string
  filename: string
  message: string
  lot_metadata: LotMetadata
  grading: GradingResult
}
