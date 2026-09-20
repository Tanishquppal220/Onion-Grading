import { useState } from "react";
import api from "@/api/axiosInstance";
import type { UploadResponse } from "@/types/grading";

export interface UploadOptions {
  calibration_mode?: string;
  custom_mm_per_pixel?: number;
  reference_dimension_mm?: number;
  reference_pixels?: number;
  lot_id?: string;
  farmer_name?: string;
  mandi_location?: string;
  lot_weight_kg?: number;
}

export function useImageUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);

  const uploadImage = async (file: File, options?: UploadOptions) => {
    setIsUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);

      if (options?.calibration_mode) {
        formData.append("calibration_mode", options.calibration_mode);
      }
      if (options?.custom_mm_per_pixel !== undefined && options.custom_mm_per_pixel > 0) {
        formData.append("custom_mm_per_pixel", options.custom_mm_per_pixel.toString());
      }
      if (options?.reference_dimension_mm !== undefined && options.reference_dimension_mm > 0) {
        formData.append("reference_dimension_mm", options.reference_dimension_mm.toString());
      }
      if (options?.reference_pixels !== undefined && options.reference_pixels > 0) {
        formData.append("reference_pixels", options.reference_pixels.toString());
      }
      if (options?.lot_id) {
        formData.append("lot_id", options.lot_id);
      }
      if (options?.farmer_name) {
        formData.append("farmer_name", options.farmer_name);
      }
      if (options?.mandi_location) {
        formData.append("mandi_location", options.mandi_location);
      }
      if (options?.lot_weight_kg !== undefined && options.lot_weight_kg > 0) {
        formData.append("lot_weight_kg", options.lot_weight_kg.toString());
      }

      const response = await api.post<UploadResponse>("/api/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(response.data);
      return response.data;
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } }; message?: string };
      const errorMessage =
        errorObj.response?.data?.detail || errorObj.message || "Upload failed";
      setError(errorMessage);
      throw err;
    }
 finally {
      setIsUploading(false);
    }
  };

  const clearResult = () => {
    setResult(null);
    setError(null);
  };

  return { uploadImage, isUploading, error, result, clearResult };
}

