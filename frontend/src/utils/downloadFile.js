// Native downloads keep file bytes out of JavaScript memory. The hidden frame
// is a navigation target only; the browser download manager owns the response.
const pending = new Set();
const transfers = new Map();
const listeners = new Set();
let sequence = 0;
let messageWindow;

export const subscribeDownloads = (listener) => { listeners.add(listener); return () => listeners.delete(listener); };
export const downloadsPending = () => pending.size > 0;
const notify = () => listeners.forEach((listener) => listener());

function installMessageListener() {
  if (messageWindow === window) return;
  window.addEventListener("message", (event) => {
    const data = event.data;
    if (data?.type !== "asset-manager-download-error" || !data.downloadId) return;
    const transfer = transfers.get(data.downloadId);
    if (!transfer || event.origin !== transfer.origin || event.source !== transfer.frame.contentWindow) return;
    transfers.delete(data.downloadId);
    transfer.frame.remove();
    transfer.onTransferError?.(data.message || "파일 다운로드에 실패했습니다.");
  });
  messageWindow = window;
}

export async function downloadFile(key, prepare, transferUrl, { onTransferError } = {}) {
  if (pending.has(key)) return;
  pending.add(key);
  notify();
  let frame;
  let form;
  let downloadId;
  try {
    installMessageListener();
    const prepared = await prepare();
    downloadId = prepared.download_id;
    if (!prepared.ticket || !downloadId) throw new Error("다운로드 권한을 준비하지 못했습니다.");

    const frameName = `download_${Date.now()}_${++sequence}`;
    frame = document.createElement("iframe");
    frame.name = frameName;
    frame.hidden = true;
    frame.setAttribute("aria-hidden", "true");
    frame.setAttribute("title", "");
    document.body.appendChild(frame);
    transfers.set(downloadId, {
      frame,
      onTransferError,
      origin: new URL(transferUrl, window.location.href).origin,
    });

    form = document.createElement("form");
    form.method = "POST";
    form.action = transferUrl;
    form.target = frameName;
    form.hidden = true;
    for (const [name, value] of Object.entries({ ticket: prepared.ticket, download_id: downloadId })) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = value;
      form.appendChild(input);
    }
    document.body.appendChild(form);
    form.submit();
  } catch (error) {
    if (downloadId) transfers.delete(downloadId);
    frame?.remove();
    throw error;
  } finally {
    try {
      form?.remove();
    } finally {
      pending.delete(key);
      notify();
    }
  }
}
