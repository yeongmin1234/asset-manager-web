import React, { useEffect, useRef, useState } from "react";
import {
  fetchInventoryForAi,
  fetchInventoryAnalysisForAi,
  fetchInventoryChangeForAi,
  fetchInventoryAlertsForAi,
  fetchRecommendedInventoryItem,
  buildConversationContext,
  buildInventoryCardData,
  filterInventoryForWarehouse,
  isInventoryAnalysisIntent,
  isInventoryChangeIntent,
  isInventoryAlertIntent,
  isInventoryContextIntent,
  isInventoryIntent,
  isInventoryRecommendationIntent,
  rememberInventoryContext,
  sendAiAssistantMessage,
} from "../../services/aiAssistantService.js";
import InventoryAnswerCard from "./InventoryAnswerCard.jsx";
import WarehouseInventoryResultCard from "./WarehouseInventoryResultCard.jsx";
import WarehousePickerModal from "./WarehousePickerModal.jsx";
import { getWarehouseInventory } from "../../api/client.js";
import { compareInventoryQuantities } from "../../utils/inventoryDisplayUtils.js";
import RecommendedInventoryItems from "./RecommendedInventoryItems.jsx";
import ProductPickerModal from "./ProductPickerModal.jsx";

const EXAMPLE_QUESTIONS = [
  "품목명으로 재고 조회",
  "품목코드로 재고 조회",
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
  const [isWarehousePickerOpen, setIsWarehousePickerOpen] = useState(false);
  const [inputPlaceholder, setInputPlaceholder] = useState("질문을 입력하세요");
  const [conversationContext, setConversationContext] = useState(null);
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
    if (handleWarehouseContextFollowup(trimmedQuestion)) return;
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
      const response = await sendAiAssistantMessage(trimmedQuestion, conversationContext);
      if (response.context) setConversationContext(response.context);
      else if (response.intent === "context_clear") setConversationContext(null);
      let answer = response.message;
      let recommendations = null;
      let inventoryCard = null;
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
          inventoryCard = buildInventoryCardData({
            inventoryResponse, context: response.context || conversationContext,
            responseData: response.data, intent: response.intent, queriedAt: new Date().toISOString(),
          });
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
        inventoryCard = buildInventoryCardData({
          inventoryResponse: inventory.inventoryResponse, context: response.context || conversationContext,
          responseData: response.data, intent: response.intent, queriedAt: new Date().toISOString(),
        });
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
          analysis: response.data?.type === "inventory_warehouse_result" ? {
            type: "inventory_warehouse_filter",
            label: `창고 필터: ${response.data.warehouse_keyword}`,
            warehouse_keyword: response.data.warehouse_keyword,
            match_count: response.data.warehouse_match_count,
            filtered_quantity: response.data.filtered_quantity,
            total_quantity: response.data.total_quantity,
          } : null,
        });
      }
      setMessages((current) => current.map((message) => (
        message.id === pendingId
          ? {
            id: `assistant-${requestId}`, role: "assistant", content: answer,
            recommendations, selectedItemCode: null, inventoryCard,
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

  const handleWarehouseContextFollowup = (question) => {
    const source = conversationContext?.warehouse_inventory_result;
    if (!source) return false;
    const normalized = question.trim().toLocaleLowerCase();
    if (normalized.includes("다른 창고")) {
      setMessages((current) => [...current, { id: `user-${Date.now()}`, role: "user", content: question }, { id: `assistant-${Date.now()}-warehouse`, role: "assistant", content: "다른 창고 또는 백화점을 선택해주세요." }]);
      setIsWarehousePickerOpen(true); setInput(""); return true;
    }
    const isSupported = ["재고 있는 품목", "0재고", "검색", "보여", "재고 많은 순", "재고 적은 순"].some((phrase) => normalized.includes(phrase));
    if (!isSupported) return false;
    let items = [...(source.items || [])];
    if (normalized.includes("재고 있는 품목")) items = items.filter((item) => compareInventoryQuantities(item.quantity, 0) > 0);
    else if (normalized.includes("0재고")) items = [...(source.items || [])];
    else {
      const keywordMatch = normalized.match(/(.+?)(?:만\s*)?(?:검색|보여)/);
      if (keywordMatch && !normalized.includes("재고 많은") && !normalized.includes("재고 적은")) {
        const keyword = keywordMatch[1].replace(/품목|재고/g, "").trim();
        if (keyword) items = items.filter((item) => `${item.item_name || ""} ${item.item_code || ""}`.toLocaleLowerCase().includes(keyword));
      }
    }
    if (normalized.includes("재고 많은 순")) items.sort((a, b) => compareInventoryQuantities(b.quantity, a.quantity));
    if (normalized.includes("재고 적은 순")) items.sort((a, b) => compareInventoryQuantities(a.quantity, b.quantity));
    const result = { ...source, items, total: items.length };
    const requestId = Date.now();
    setMessages((current) => [...current, { id: `user-${requestId}`, role: "user", content: question }, { id: `assistant-${requestId}`, role: "assistant", content: `${source.warehouse_name}의 기존 조회 결과에서 조건을 적용했습니다.`, warehouseInventoryResult: result }]);
    setInput(""); return true;
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
      const pendingWarehouse = conversationContext?.pending_warehouse_expression
        || conversationContext?.pending_warehouse_keyword;
      const filtered = pendingWarehouse
        ? filterInventoryForWarehouse(inventory.inventoryResponse, pendingWarehouse)
        : null;
      const displayedResponse = filtered?.inventoryResponse || inventory.inventoryResponse;
      const items = Array.isArray(displayedResponse?.items) ? displayedResponse.items : [];
      setConversationContext(filtered?.context || buildConversationContext(inventory.inventoryResponse));
      const inventoryCard = buildInventoryCardData({
        inventoryResponse: displayedResponse,
        context: filtered?.context || buildConversationContext(inventory.inventoryResponse),
        responseData: filtered ? {
          type: "inventory_warehouse_result", warehouse_keyword: pendingWarehouse,
          total_quantity: inventory.inventoryResponse?.items?.[0]?.total_quantity,
          all_warehouses: inventory.inventoryResponse?.items?.[0]?.warehouses || [],
        } : null,
        intent: filtered ? "inventory_item_warehouse_search" : "inventory_search",
        queriedAt: new Date().toISOString(),
      });
      await rememberInventoryContext({
        aiResponse: { intent: "inventory_search", data: { item_code: item.item_code } },
        query: item.item_name || item.item_code,
        inventoryResponse: inventory.inventoryResponse,
      }).catch(() => {});
      onInventoryStateChange?.({
        status: items.length ? "success" : "empty", query: item.item_name || item.item_code,
        items, selectedItemCode: item.item_code, searchedAt: new Date().toISOString(),
        errorMessage: null, analysis: filtered?.analysis || null,
      });
      setMessages((current) => current.map((message) => (
        message.id === pendingId
          ? { id: `assistant-selection-${requestId}`, role: "assistant", content: filtered?.answer || inventory.answer, inventoryCard }
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
    setIsWarehousePickerOpen(false);
    await handleRecommendationSelect("product-picker", item);
  };

  const handleWarehouseSelect = async (warehouse) => {
    if (isSending || requestLockRef.current) return;
    setIsWarehousePickerOpen(false); requestLockRef.current = true; setIsSending(true);
    const requestId = Date.now(); const pendingId = `pending-warehouse-${requestId}`;
    setMessages((current) => [...current, { id: `user-warehouse-${requestId}`, role: "user", content: `${warehouse.warehouse_name} 선택` }, { id: pendingId, role: "assistant", content: "선택한 장소의 품목 재고를 조회하고 있습니다...", pending: true }]);
    onInventoryStateChange?.({ status: "loading", query: warehouse.warehouse_name, items: [], selectedItemCode: null, searchedAt: null, errorMessage: null, analysis: null });
    try {
      const result = await getWarehouseInventory(warehouse.warehouse_code, { includeZero: true, limit: 50 });
      const panelItems = (result.items || []).filter((item) => compareInventoryQuantities(item.quantity, 0) !== 0).map((item) => ({
        item_code: item.item_code, item_name: item.item_name, size: item.size, unit: item.unit,
        total_quantity: item.quantity, warehouses: [{ warehouse_code: result.warehouse_code, warehouse_name: result.warehouse_name, quantity: item.quantity }],
      }));
      setConversationContext({
        selected_warehouse_code: result.warehouse_code, selected_warehouse_name: result.warehouse_name,
        warehouse_inventory_result: result, last_intent: "warehouse_inventory_search",
      });
      onInventoryStateChange?.({ status: panelItems.length ? "success" : "empty", query: result.warehouse_name, items: panelItems, selectedItemCode: panelItems[0]?.item_code || null, searchedAt: new Date().toISOString(), errorMessage: null, analysis: { type: "warehouse_inventory", label: `${result.warehouse_name} 품목 재고` } });
      setMessages((current) => current.map((message) => message.id === pendingId ? { id: `assistant-warehouse-${requestId}`, role: "assistant", content: `${result.warehouse_name}의 품목 재고입니다.`, warehouseInventoryResult: result } : message));
    } catch (error) {
      onInventoryStateChange?.((current) => ({ ...current, status: "error", errorMessage: error.message }));
      setMessages((current) => current.map((message) => message.id === pendingId ? { id: `error-warehouse-${requestId}`, role: "assistant", content: error.message } : message));
    } finally { requestLockRef.current = false; setIsSending(false); }
  };

  const handleQuickQuestion = (question) => {
    if (question === "품목코드로 재고 조회") {
      setInputPlaceholder("품목코드를 입력하세요");
      inputRef.current?.focus();
      return;
    }
    setIsProductPickerOpen(true);
  };

  const handleWarehouseLoadMore = async (messageId, result) => {
    if (requestLockRef.current || isSending) return;
    requestLockRef.current = true; setIsSending(true);
    try {
      const next = await getWarehouseInventory(result.warehouse_code, { includeZero: true, limit: 50, offset: result.items?.length || 0 });
      setMessages((current) => current.map((message) => message.id === messageId ? { ...message, warehouseInventoryResult: { ...result, items: [...(result.items || []), ...(next.items || [])], total: next.total, cache_hit: next.cache_hit } } : message));
    } finally { requestLockRef.current = false; setIsSending(false); }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const handleInventoryCardClearFilter = (messageId, cardData) => {
    const fullItem = { ...cardData.item, total_quantity: cardData.totalQuantity, warehouses: cardData.allWarehouses };
    const fullResponse = { success: true, authenticated: true, total: 1, items: [fullItem], message: "기존 재고 조회 결과입니다.", response_time_ms: 0 };
    const nextCard = buildInventoryCardData({ inventoryResponse: fullResponse, context: buildConversationContext(fullResponse), intent: "inventory_show_all_warehouses", queriedAt: cardData.queriedAt });
    setMessages((current) => current.map((message) => message.id === messageId ? { ...message, inventoryCard: nextCard } : message));
    setConversationContext(buildConversationContext(fullResponse, "inventory_show_all_warehouses"));
    onInventoryStateChange?.({ status: "success", query: cardData.item.item_name || cardData.item.item_code, items: [fullItem], selectedItemCode: fullItem.item_code, searchedAt: new Date().toISOString(), errorMessage: null, analysis: null });
  };

  const handleConversationReset = () => {
    if (isSending) return;
    setConversationContext(null);
    setMessages(INITIAL_MESSAGES);
    setInput("");
    setInputPlaceholder("질문을 입력하세요");
    setIsProductPickerOpen(false);
    recommendationLocksRef.current.clear();
  };

  return (
    <section className="dashboard-panel ai-assistant-card" aria-labelledby="ai-assistant-title">
      <div className="ai-assistant-heading">
        <div>
          <h3 id="ai-assistant-title">AI 업무 도우미</h3>
          <p>재고 및 사내 업무 정보를 질문해보세요.</p>
        </div>
        <button type="button" className="ai-assistant-reset" onClick={handleConversationReset} disabled={isSending}>
          대화 초기화
        </button>
      </div>

      <div className="ai-assistant-conversation" ref={conversationRef} aria-live="polite">
        {messages.map((message) => (
          <div
            className={`ai-assistant-message ai-assistant-message-${message.role}${message.pending ? " ai-assistant-message-pending" : ""}`}
            key={message.id}
          >
            <span>{message.role === "user" ? "나" : "AI"}</span>
            <div className="ai-assistant-message-body">
              {message.inventoryCard ? null : <p>{message.content}</p>}
              {message.inventoryCard ? <InventoryAnswerCard data={message.inventoryCard} onClearFilter={(data) => handleInventoryCardClearFilter(message.id, data)} /> : null}
              {message.warehouseInventoryResult ? <WarehouseInventoryResultCard result={message.warehouseInventoryResult} onLoadMore={() => handleWarehouseLoadMore(message.id, message.warehouseInventoryResult)} /> : null}
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
      <WarehousePickerModal isOpen={isWarehousePickerOpen} onClose={() => setIsWarehousePickerOpen(false)} onSelect={handleWarehouseSelect} />
    </section>
  );
}

export default AiAssistantCard;
