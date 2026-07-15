const PREVIEW_RESPONSE = "재고 조회 API 연결 후 사용할 수 있습니다.";

// 실제 연동 시 이 함수 내부에서 POST /ai/chat 또는
// POST /inventory/ai-query 요청을 수행하도록 교체합니다.
export async function sendAiAssistantMessage(_message) {
  return Promise.resolve({ message: PREVIEW_RESPONSE });
}
