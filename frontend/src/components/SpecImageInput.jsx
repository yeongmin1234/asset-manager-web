import React, { useEffect, useState } from "react";
import { usePrivateImageUrl } from "./PrivateImage.jsx";

const ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];
const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024;

function SpecImageInput({
  initialUrl = "",
  onChange,
  compact = false,
}) {
  const privateImageUrl = usePrivateImageUrl(initialUrl);
  const [previewUrl, setPreviewUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [isRemoved, setIsRemoved] = useState(false);
  const [error, setError] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    setPreviewUrl("");
    setSelectedFile(null);
    setIsRemoved(false);
    setError("");
  }, [initialUrl]);

  useEffect(() => {
    if (!selectedFile) {
      return undefined;
    }

    const objectUrl = window.URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);
    return () => window.URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  const handleFile = (file) => {
    const validationError = validateImageFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setSelectedFile(file);
    setIsRemoved(false);
    setError("");
    onChange?.(file, false);
  };

  const handleRemove = () => {
    setSelectedFile(null);
    setIsRemoved(true);
    setPreviewUrl("");
    setError("");
    onChange?.(null, Boolean(initialUrl));
  };

  const handlePaste = (event) => {
    const items = Array.from(event.clipboardData?.items || []);
    const imageItem = items.find((item) => item.type.startsWith("image/"));
    if (!imageItem) {
      return;
    }

    const file = imageItem.getAsFile();
    if (file) {
      event.preventDefault();
      handleFile(normalizeClipboardFile(file));
    }
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      handleFile(file);
    }
  };

  const fieldClassName = [
    "spec-image-field",
    compact ? "spec-image-field-compact" : "",
    isDragging ? "dragging" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={fieldClassName}>
      <span>사양 이미지 첨부</span>
      <div
        className="spec-image-dropzone"
        tabIndex="0"
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onPaste={handlePaste}
      >
        {previewUrl || (initialUrl && privateImageUrl && !selectedFile && !isRemoved) ? (
          <div className="spec-image-preview">
            <img src={previewUrl || privateImageUrl} alt="사양 이미지 미리보기" />
            <button
              type="button"
              className="secondary-button"
              onClick={(event) => {
                event.stopPropagation();
                handleRemove();
              }}
            >
              이미지 제거
            </button>
          </div>
        ) : (
          <div className="spec-image-placeholder">
            <strong>이미지 붙여넣기(Ctrl+V) 또는 드래그 앤 드롭</strong>
            <small>jpg, jpeg, png, webp · 최대 10MB</small>
          </div>
        )}
      </div>
      {error && <small className="spec-image-error">{error}</small>}
    </div>
  );
}

function validateImageFile(file) {
  if (!file) {
    return "이미지 파일을 선택해주세요.";
  }
  if (file.size > MAX_IMAGE_SIZE_BYTES) {
    return "이미지 파일은 10MB 이하만 업로드할 수 있습니다.";
  }

  const fileName = file.name || "";
  const extension = fileName.slice(fileName.lastIndexOf(".")).toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return "jpg, jpeg, png, webp 이미지만 업로드할 수 있습니다.";
  }
  return "";
}

function normalizeClipboardFile(file) {
  if (file.name) {
    return file;
  }

  const extension = file.type === "image/webp" ? "webp" : file.type === "image/jpeg" ? "jpg" : "png";
  return new File([file], `spec-image.${extension}`, { type: file.type || "image/png" });
}

export default SpecImageInput;
