import { ApiError, postAiChat } from "../api/client.js";

export async function sendAiAssistantMessage(message) {
  try {
    return await postAiChat(message);
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 401) throw new Error("로그인이 만료되었습니다.");
      if (error.status === 403) throw new Error("업무 도우미를 사용할 권한이 없습니다.");
      if (error.status >= 500) throw new Error("질문 처리 중 오류가 발생했습니다.");
      if (!error.status) throw new Error("업무 도우미 서버에 연결할 수 없습니다.");
      throw new Error(error.message || "질문을 처리할 수 없습니다.");
    }
    throw new Error("업무 도우미 서버에 연결할 수 없습니다.");
  }
}
