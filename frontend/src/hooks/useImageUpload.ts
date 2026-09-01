import { useState } from "react";
import api from "@/api/axiosInstance";

export function useImageUpload() {
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<any>(null);

    const uploadImage = async (file: File) => {
        setIsUploading(true);
        setError(null);
        try {
            const formData = new FormData();
            formData.append("file", file);
            
            const response = await api.post("/api/upload", formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });
            setResult(response.data);
            return response.data;
        } catch (err: any) {
            const errorMessage = err.response?.data?.detail || err.message || "Upload failed";
            setError(errorMessage);
            throw err;
        } finally {
            setIsUploading(false);
        }
    };

    return { uploadImage, isUploading, error, result };
}
