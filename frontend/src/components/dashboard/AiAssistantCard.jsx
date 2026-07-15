import React, { useEffect, useRef, useState } from "react";
import {
  fetchInventoryForAi,
  isInventoryIntent,
  sendAiAssistantMessage,
} from "../../services/aiAssistantService.js";

const EXAMPLE_QUESTIONS = [
  "벤틀리 재고 알려줘",
  "재고 10개 이하 품목 보여줘",
  "품목코드로 재고 조회",
];

const INITIAL_MESSAGES = [
  {
    id: "initial",
    role: "assistant",
    content: "안녕하세요.\n현재는 재고 조회 기능을 준비하고 있습니다.",
  },
];

function AiAssistantCard({ onInventoryStateChange }) {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const conversationRef = useRef(null);

  useEffect(() => {
    const conversation = conversationRef.current;
    if (conversation) conversation.scrollTop = conversation.scrollHeight;
  }, [messages]);

  const sendMessage = async (question = input) => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isSending) return;

    const requestId = Date.now();
    const pendingId = `pending-${requestId}`;
    setMessages((current) => [
      ...current,
      { id: `user-${requestId}`, role: "user", content: trimmedQuestion },
      { id: pendingId, role: "assistant", content: "질문을 확인하고 있습니다...", pending: true },
    ]);
    setInput("");
    setIsSending(true);

    try {
      const response = await sendAiAssistantMessage(trimmedQuestion);
      let answer = response.message;
      if (isInventoryIntent(response.intent)) {
        setMessages((current) => current.map((message) => (
          message.id === pendingId ? { ...message, content: "재고 정보를 조회하고 있습니다." } : message
        )));
        onInventoryStateChange?.({
          status: "loading", query: trimmedQuestion, items: [], searchedAt: null, errorMessage: null,
        });
        const inventory = await fetchInventoryForAi(response, trimmedQuestion);
        answer = inventory.answer;
        const items = Array.isArray(inventory.inventoryResponse?.items) ? inventory.inventoryResponse.items : [];
        onInventoryStateChange?.({
          status: items.length ? "success" : "empty",
          query: trimmedQuestion,
          items,
          searchedAt: new Date().toISOString(),
          errorMessage: null,
        });
      }
      setMessages((current) => current.map((message) => (
        message.id === pendingId
          ? { id: `assistant-${requestId}`, role: "assistant", content: answer }
          : message
      )));
    } catch (error) {
      onInventoryStateChange?.((current) => current.status === "loading" ? {
        ...current,
        status: "error",
        items: [],
        searchedAt: new Date().toISOString(),
        errorMessage: "재고 정보를 불러오지 못했습니다. 잠시 후 다시 조회해 주세요.",
      } : current);
      setMessages((current) => current.map((message) => (
        message.id === pendingId
          ? { id: `error-${requestId}`, role: "assistant", content: error.message }
          : message
      )));
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <section className="dashboard-panel ai-assistant-card" aria-labelledby="ai-assistant-title">
      <div className="ai-assistant-heading">
        <div>
          <h3 id="ai-assistant-title">AI 업무 도우미</h3>
          <p>재고 및 사내 업무 정보를 질문해보세요.</p>
        </div>
        <span>규칙 기반</span>
      </div>

      <div className="ai-assistant-conversation" ref={conversationRef} aria-live="polite">
        {messages.map((message) => (
          <div
            className={`ai-assistant-message ai-assistant-message-${message.role}${message.pending ? " ai-assistant-message-pending" : ""}`}
            key={message.id}
          >
            <span>{message.role === "user" ? "나" : "AI"}</span>
            <p>{message.content}</p>
          </div>
        ))}
      </div>

      <div className="ai-assistant-examples" aria-label="예시 질문">
        {EXAMPLE_QUESTIONS.map((question) => (
          <button type="button" key={question} onClick={() => sendMessage(question)} disabled={isSending}>
            {question}
          </button>
        ))}
      </div>

      <div className="ai-assistant-input-row">
        <textarea
          rows="1"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSending}
          placeholder="질문을 입력하세요"
          aria-label="AI 업무 도우미 질문"
        />
        <button type="button" onClick={() => sendMessage()} disabled={!input.trim() || isSending}>
          {isSending ? "전송 중" : "전송"}
        </button>
      </div>
    </section>
  );
}

export default AiAssistantCard;
