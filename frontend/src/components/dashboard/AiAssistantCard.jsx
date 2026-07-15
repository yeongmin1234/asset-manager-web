import React, { useEffect, useRef, useState } from "react";
import {
  fetchInventoryForAi,
  fetchInventoryAnalysisForAi,
  fetchInventoryChangeForAi,
  fetchInventoryAlertsForAi,
  fetchRecommendedInventoryItem,
  isInventoryAnalysisIntent,
  isInventoryChangeIntent,
  isInventoryAlertIntent,
  isInventoryContextIntent,
  isInventoryIntent,
  isInventoryRecommendationIntent,
  rememberInventoryContext,
  sendAiAssistantMessage,
} from "../../services/aiAssistantService.js";
import RecommendedInventoryItems from "./RecommendedInventoryItems.jsx";
import ProductPickerModal from "./ProductPickerModal.jsx";

const EXAMPLE_QUESTIONS = [
  "품목명으로 재고 조회",
  "품목코드로 재고 조회",
  "창고별 재고 조회",
];

const INITIAL_MESSAGES = [
  {
    id: "initial",
    role: "assistant",
    content: "안녕하세요.\n품목명 또는 품목코드로 현재 재고를 조회할 수 있습니다.",
  },
];

function AiAssistantCard({ onInventoryStateChange }) {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isProductPickerOpen, setIsProductPickerOpen] = useState(false);
  const [inputPlaceholder, setInputPlaceholder] = useState("질문을 입력하세요");
  const conversationRef = useRef(null);
  const inputRef = useRef(null);
  const requestLockRef = useRef(false);
  const recommendationLocksRef = useRef(new Set());

  useEffect(() => {
    const conversation = conversationRef.current;
    if (conversation) conversation.scrollTop = conversation.scrollHeight;
  }, [messages]);

  useEffect(() => {
    const textarea = inputRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const nextHeight = Math.min(textarea.scrollHeight, 120);
    textarea.style.height = `${Math.max(nextHeight, 40)}px`;
    textarea.style.overflowY = textarea.scrollHeight > 120 ? "auto" : "hidden";
  }, [input]);

  const sendMessage = async (question = input) => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isSending || requestLockRef.current) return;
    requestLockRef.current = true;

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
      let recommendations = null;
      const responseType = response.data?.type;
      if (responseType === "product_candidates") {
        recommendations = Array.isArray(response.data?.items) ? response.data.items : [];
      } else if (responseType === "product_not_found") {
        onInventoryStateChange?.({
          status: "empty", query: response.data?.query || trimmedQuestion, items: [],
          selectedItemCode: null, searchedAt: new Date().toISOString(),
          errorMessage: null, analysis: null,
        });
      } else if (responseType === "feature_disabled") {
        // Keep the current inventory panel unchanged for temporarily disabled features.
      } else if (isInventoryRecommendationIntent(response.intent)) {
        recommendations = Array.isArray(response.data?.items) ? response.data.items : [];
        if (!recommendations.length) {
          onInventoryStateChange?.({
            status: "empty", query: response.data?.query || trimmedQuestion, items: [],
            selectedItemCode: null, searchedAt: new Date().toISOString(),
            errorMessage: null, analysis: null,
          });
        }
      } else if (isInventoryContextIntent(response.intent)) {
        const inventoryResponse = response.data?.inventory_response;
        const items = Array.isArray(inventoryResponse?.items) ? inventoryResponse.items : [];
        if (items.length) {
          onInventoryStateChange?.({
            status: "success",
            query: trimmedQuestion,
            items,
            selectedItemCode: response.data?.selected_item_code || items[0]?.item_code || null,
            searchedAt: new Date().toISOString(),
            errorMessage: null,
          });
        }
      } else if (isInventoryAlertIntent(response.intent)) {
        onInventoryStateChange?.({ status: "loading", query: trimmedQuestion, items: [], selectedItemCode: null, searchedAt: null, errorMessage: null, analysis: null });
        const inventory = await fetchInventoryAlertsForAi(response);
        answer = inventory.answer;
        const items = Array.isArray(inventory.inventoryResponse?.items) ? inventory.inventoryResponse.items : [];
        onInventoryStateChange?.({ status: items.length ? "success" : "empty", query: trimmedQuestion, items, selectedItemCode: items[0]?.item_code || null, searchedAt: new Date().toISOString(), errorMessage: null, analysis: { type: "inventory_alert", label: "재고 경고" } });
      } else if (isInventoryChangeIntent(response.intent)) {
        setMessages((current) => current.map((message) => (
          message.id === pendingId ? { ...message, content: "저장된 재고 변화를 분석하고 있습니다." } : message
        )));
        onInventoryStateChange?.({
          status: "loading", query: trimmedQuestion, items: [], selectedItemCode: null,
          searchedAt: null, errorMessage: null, analysis: null,
        });
        const inventory = await fetchInventoryChangeForAi(response);
        answer = inventory.answer;
        const items = Array.isArray(inventory.inventoryResponse?.items) ? inventory.inventoryResponse.items : [];
        onInventoryStateChange?.({
          status: items.length ? "success" : "empty",
          query: trimmedQuestion,
          items,
          selectedItemCode: items[0]?.item_code || null,
          searchedAt: new Date().toISOString(),
          errorMessage: null,
          analysis: inventory.inventoryResponse?.analysis || null,
        });
      } else if (isInventoryAnalysisIntent(response.intent)) {
        setMessages((current) => current.map((message) => (
          message.id === pendingId ? { ...message, content: "재고 조건을 분석하고 있습니다." } : message
        )));
        onInventoryStateChange?.({
          status: "loading", query: trimmedQuestion, items: [], selectedItemCode: null,
          searchedAt: null, errorMessage: null, analysis: null,
        });
        const inventory = await fetchInventoryAnalysisForAi(response);
        answer = inventory.answer;
        const items = Array.isArray(inventory.inventoryResponse?.items) ? inventory.inventoryResponse.items : [];
        await rememberInventoryContext({
          aiResponse: response,
          query: trimmedQuestion,
          inventoryResponse: inventory.inventoryResponse,
        }).catch(() => {});
        onInventoryStateChange?.({
          status: items.length ? "success" : "empty",
          query: trimmedQuestion,
          items,
          selectedItemCode: items[0]?.item_code || null,
          searchedAt: new Date().toISOString(),
          errorMessage: null,
          analysis: inventory.inventoryResponse?.analysis || null,
        });
      } else if (isInventoryIntent(response.intent)) {
        setMessages((current) => current.map((message) => (
          message.id === pendingId ? { ...message, content: "재고 정보를 조회하고 있습니다." } : message
        )));
        onInventoryStateChange?.({
          status: "loading", query: trimmedQuestion, items: [], selectedItemCode: null, searchedAt: null, errorMessage: null,
        });
        const inventory = await fetchInventoryForAi(response, trimmedQuestion);
        answer = inventory.answer;
        const items = Array.isArray(inventory.inventoryResponse?.items) ? inventory.inventoryResponse.items : [];
        await rememberInventoryContext({
          aiResponse: response,
          query: trimmedQuestion,
          inventoryResponse: inventory.inventoryResponse,
        }).catch(() => {});
        onInventoryStateChange?.({
          status: items.length ? "success" : "empty",
          query: trimmedQuestion,
          items,
          selectedItemCode: items[0]?.item_code || null,
          searchedAt: new Date().toISOString(),
          errorMessage: null,
          analysis: null,
        });
      }
      setMessages((current) => current.map((message) => (
        message.id === pendingId
          ? {
            id: `assistant-${requestId}`, role: "assistant", content: answer,
            recommendations, selectedItemCode: null,
          }
          : message
      )));
    } catch (error) {
      onInventoryStateChange?.((current) => current.status === "loading" ? {
        ...current,
        status: "error",
        items: [],
        selectedItemCode: null,
        searchedAt: new Date().toISOString(),
        errorMessage: error.message || "재고 정보를 불러오지 못했습니다. 잠시 후 다시 조회해 주세요.",
      } : current);
      setMessages((current) => current.map((message) => (
        message.id === pendingId
          ? { id: `error-${requestId}`, role: "assistant", content: error.message }
          : message
      )));
    } finally {
      requestLockRef.current = false;
      setIsSending(false);
    }
  };

  const handleRecommendationSelect = async (messageId, item) => {
    const lockKey = `${messageId}:${item.item_code}`;
    if (isSending || requestLockRef.current || recommendationLocksRef.current.has(lockKey)) return;
    requestLockRef.current = true;
    recommendationLocksRef.current.add(lockKey);
    setIsSending(true);
    setMessages((current) => current.map((message) => (
      message.id === messageId ? { ...message, selectedItemCode: item.item_code } : message
    )));
    const requestId = Date.now();
    const pendingId = `pending-selection-${requestId}`;
    setMessages((current) => [
      ...current,
      { id: `user-selection-${requestId}`, role: "user", content: `${item.item_name || item.item_code} 선택` },
      { id: pendingId, role: "assistant", content: "선택한 품목의 재고를 조회하고 있습니다...", pending: true },
    ]);
    onInventoryStateChange?.({
      status: "loading", query: item.item_name || item.item_code, items: [],
      selectedItemCode: item.item_code, searchedAt: null, errorMessage: null, analysis: null,
    });
    try {
      const inventory = await fetchRecommendedInventoryItem(item);
      const items = Array.isArray(inventory.inventoryResponse?.items) ? inventory.inventoryResponse.items : [];
      await rememberInventoryContext({
        aiResponse: { intent: "inventory_search", data: { item_code: item.item_code } },
        query: item.item_name || item.item_code,
        inventoryResponse: inventory.inventoryResponse,
      }).catch(() => {});
      onInventoryStateChange?.({
        status: items.length ? "success" : "empty", query: item.item_name || item.item_code,
        items, selectedItemCode: item.item_code, searchedAt: new Date().toISOString(),
        errorMessage: null, analysis: null,
      });
      setMessages((current) => current.map((message) => (
        message.id === pendingId
          ? { id: `assistant-selection-${requestId}`, role: "assistant", content: inventory.answer }
          : message
      )));
    } catch (error) {
      setMessages((current) => current.map((message) => {
        if (message.id === messageId) return { ...message, selectedItemCode: null };
        if (message.id === pendingId) return { id: `error-selection-${requestId}`, role: "assistant", content: error.message };
        return message;
      }));
      onInventoryStateChange?.((current) => ({
        ...current, status: "error", items: [], selectedItemCode: null,
        searchedAt: new Date().toISOString(), errorMessage: error.message,
      }));
    } finally {
      recommendationLocksRef.current.delete(lockKey);
      requestLockRef.current = false;
      setIsSending(false);
    }
  };

  const handleProductPickerSelect = async (item) => {
    setIsProductPickerOpen(false);
    await handleRecommendationSelect("product-picker", item);
  };

  const handleQuickQuestion = (question) => {
    if (question === "품목코드로 재고 조회") {
      setInputPlaceholder("품목코드를 입력하세요");
      inputRef.current?.focus();
      return;
    }
    setIsProductPickerOpen(true);
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
      </div>

      <div className="ai-assistant-conversation" ref={conversationRef} aria-live="polite">
        {messages.map((message) => (
          <div
            className={`ai-assistant-message ai-assistant-message-${message.role}${message.pending ? " ai-assistant-message-pending" : ""}`}
            key={message.id}
          >
            <span>{message.role === "user" ? "나" : "AI"}</span>
            <div className="ai-assistant-message-body">
              <p>{message.content}</p>
              {message.recommendations ? (
                <RecommendedInventoryItems
                  items={message.recommendations}
                disabled={isSending}
                  selectedItemCode={message.selectedItemCode}
                  onSelect={(item) => handleRecommendationSelect(message.id, item)}
                />
              ) : null}
            </div>
          </div>
        ))}
      </div>

      <div className="ai-assistant-input-area">
        <div className="ai-assistant-examples" aria-label="예시 질문">
          {EXAMPLE_QUESTIONS.map((question) => (
            <button type="button" key={question} onClick={() => handleQuickQuestion(question)} disabled={isSending}>
              {question}
            </button>
          ))}
        </div>

        <div className="ai-assistant-input-row">
          <textarea
            ref={inputRef}
            rows="1"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSending}
            placeholder={inputPlaceholder}
            aria-label="AI 업무 도우미 질문"
          />
          <button type="button" onClick={() => sendMessage()} disabled={!input.trim() || isSending}>
            {isSending ? "전송 중" : "전송"}
          </button>
        </div>
      </div>
      <ProductPickerModal
        isOpen={isProductPickerOpen}
        onClose={() => setIsProductPickerOpen(false)}
        onSelect={handleProductPickerSelect}
      />
    </section>
  );
}

export default AiAssistantCard;
