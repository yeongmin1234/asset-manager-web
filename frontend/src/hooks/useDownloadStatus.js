import { useSyncExternalStore } from "react";
import { subscribeDownloads, downloadsPending } from "../utils/downloadFile.js";

export default function useDownloadStatus() {
  return useSyncExternalStore(subscribeDownloads, downloadsPending, () => false);
}
