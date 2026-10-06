import React, { useEffect, useState } from "react";
import { fetchPrivateImage } from "../api/client.js";

export function usePrivateImageUrl(path) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    let active = true;
    let objectUrl = "";
    setUrl("");
    if (path) {
      fetchPrivateImage(path).then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      }).catch(() => {});
    }
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);
  return url;
}

export default function PrivateImage({ path, alt, onClick, ...props }) {
  const url = usePrivateImageUrl(path);
  return url ? <img src={url} alt={alt} onClick={onClick ? () => onClick(url) : undefined} {...props} /> : null;
}
