"use client"

import { CldUploadWidget } from "next-cloudinary"
import Image from "next/image"
import React, { useCallback } from "react"
// Nếu chưa cài lucide-react, có thể dùng SVG hoặc icon khác
// import { ImagePlus, Trash } from "lucide-react"

interface ImageUploadProps {
  onChange: (value: string) => void
  value: string
}

type CloudinaryUploadResult = {
  event?: string;
  info?: unknown; // next-cloudinary may pass string or object; we'll narrow
};

const ImageUpload: React.FC<ImageUploadProps> = ({ onChange, value }) => {
  const handleUpload = useCallback(
    (result: CloudinaryUploadResult) => {
      if (!result.info) return;
      if (typeof result.info === 'string') {
        // If the library returns just a URL string
        onChange(result.info);
        return;
      }
      // Attempt to read secure_url property if it exists
      const infoObj = result.info as { secure_url?: string };
      if (infoObj.secure_url) {
        onChange(infoObj.secure_url);
      }
    },
    [onChange]
  )

  return (
    <CldUploadWidget
      onSuccess={handleUpload}
      uploadPreset="YOUR_UPLOAD_PRESET" // <-- Thay bằng preset thực tế
      options={{
        maxFiles: 1,
        resourceType: "image",
      }}
    >
      {({ open }) => (
        <div
          onClick={() => open?.()}
          className="relative cursor-pointer hover:opacity-70 transition border-dashed border-2 p-10 border-gray-300 flex flex-col justify-center items-center gap-4 text-gray-600 h-64"
        >
          {value ? (
            <div className="absolute inset-0 w-full h-full">
              <Image
                alt="Uploaded Image"
                fill
                src={value}
                style={{ objectFit: "cover" }}
              />
            </div>
          ) : (
            <>
              {/* Nếu chưa cài icon, dùng SVG */}
              <svg width="50" height="50" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 5v14m7-7H5"/></svg>
              <div className="font-semibold text-lg">Nhấn để tải ảnh lên</div>
            </>
          )}
        </div>
      )}
    </CldUploadWidget>
  )
}

export default ImageUpload;
