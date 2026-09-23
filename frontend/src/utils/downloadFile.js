// Native downloads keep file bytes out of JavaScript memory. A task covers
// preparation/handoff; completion and transfer failures belong to the browser.
const pending = new Set();
let sequence = 0;
const listeners = new Set();
export const subscribeDownloads = (listener) => { listeners.add(listener); return () => listeners.delete(listener); };
export const downloadsPending = () => pending.size > 0;
const notify = () => listeners.forEach((listener) => listener());

export async function downloadFile(key, prepare, transferUrl) {
  if (pending.has(key)) return;
  pending.add(key);
  notify();
  let target;
  let form;
  try {
    // Must run synchronously in the click gesture, before any await.
    // LAN deployments use HTTP, where crypto.randomUUID is unavailable.
    const name = `download_${Date.now()}_${++sequence}`;
    target = window.open("about:blank", name);
    if (!target) throw new Error("다운로드 창이 차단되었습니다. 이 사이트의 팝업을 허용한 뒤 다시 시도해 주세요.");
    target.opener = null;
    target.document.title = "파일 다운로드";
    target.document.body.textContent = "파일을 준비하고 있습니다…";
    const { ticket } = await prepare();
    if (target.closed) throw new Error("다운로드 창이 닫혔습니다. 다시 시도해 주세요.");
    target.document.body.textContent = "브라우저에 파일 전송을 요청했습니다. 다운로드 목록에서 진행 상태와 실패 여부를 확인해 주세요. 이 안내 창은 닫아도 됩니다.";
    form = target.document.createElement("form");
    form.method = "POST";
    form.action = transferUrl;
    form.target = "_self";
    form.hidden = true;
    const input = target.document.createElement("input");
    input.name = "ticket";
    input.value = ticket;
    form.appendChild(input);
    target.document.body.appendChild(form);
    form.submit();
  } catch (error) {
    if (target && !target.closed) target.close();
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
