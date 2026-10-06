import React, { useEffect, useRef, useState } from "react";
import { chatAssistant, homeAssistantApiConfigured } from "./services/homeAssistantService";
import InventoryAnswerCard from "./InventoryAnswerCard";
import ItemSelectionModal from "./ItemSelectionModal";
import SkoomiMascot from "./components/common/SkoomiMascot";
import { getSkoomiState } from "./utils/skoomiStateUtils";

const quick = ["품목명으로 재고 조회", "품목코드로 재고 조회", "창고별 재고 확인"];
const examples = [
  "랜턴블랙 재고 알려줘",
  "품목코드 101006 재고 알려줘",
  "랜턴블랙 파주 재고 알려줘",
  "파주만 보여줘",
  "전체 창고 보여줘",
  "총 몇 개야?",
  "품목코드는?",
  "최신 재고로 다시 조회해줘",
];
const emptyContext = {};

export default function AiAssistantPanel() {
  const [question, setQuestion] = useState(""), [messages, setMessages] = useState([]), [context, setContext] = useState(emptyContext);
  const [loading, setLoading] = useState(false), [error, setError] = useState(null), [composing, setComposing] = useState(false);
  const [modal, setModal] = useState(null), [recent, setRecent] = useState([]), [helpOpen, setHelpOpen] = useState(false);
  const itemButtonRef = useRef(null);
  const questionRef = useRef(null);
  const lastAssistant = [...messages].reverse().find((row) => row.role === "assistant");
  const mascotStatus = getSkoomiState({ isLoading: loading, error, response: lastAssistant, apiConfigured: homeAssistantApiConfigured });
  useEffect(() => {
    if (!helpOpen) return undefined;
    const closeHelp = (event) => event.key === "Escape" && setHelpOpen(false);
    window.addEventListener("keydown", closeHelp);
    return () => window.removeEventListener("keydown", closeHelp);
  }, [helpOpen]);
  const send = async (value = question) => {
    const text = value.trim(); if (!text || loading || composing) return;
    setLoading(true); setError(null); setMessages((rows) => [...rows, { role: "user", text }]); setQuestion("");
    try { const answer = await chatAssistant(text, context); setContext(answer.context || {}); setMessages((rows) => [...rows, { role: "assistant", ...answer }]); }
    catch (reason) { setError(reason); }
    finally { setLoading(false); }
  };
  const selectItem = async (item) => { setModal(null); setRecent((rows) => [item, ...rows.filter((x) => x.item_code !== item.item_code)].slice(0, 5)); await send(`품목코드 ${item.item_code} 재고 조회`); };
  const reset = () => { setMessages([]); setContext(emptyContext); setError(null); setQuestion(""); setHelpOpen(false); };
  const fillQuestion = (value) => { setQuestion(value); setHelpOpen(false); window.requestAnimationFrame(() => questionRef.current?.focus()); };
  return <section className="home-work-panel home-ai-panel"><div className="home-ai-mascot-header"><div><h2>AI 업무 도우미</h2><p className="home-ai-description">이카운트 품목·재고 정보를 질문해보세요.</p></div><SkoomiMascot state={mascotStatus.state} size="medium" message={mascotStatus.message} /></div>
    <div className="home-ai-conversation">{messages.length ? messages.map((row, index) => { const rowStatus = getSkoomiState({ response: row }); return <div key={index} className={`ai-message-row ai-message-row--${row.role}`} aria-label={row.role === "assistant" ? "스쿠미 답변" : "사용자 질문"}>{row.role === "assistant" && <SkoomiMascot state={rowStatus.state} size="avatar" decorative compact showMessage={false} animate={false}/>}<div className={`ai-bubble ai-bubble--${row.role}`}><p>{row.text || row.message}</p>{row.data?.type === "item_candidates" && <div className="ai-candidates">{row.data.items.map((item) => <button type="button" key={item.item_code} onClick={() => selectItem(item)}>{item.item_name}<small>{item.item_code}</small></button>)}</div>}{row.data?.type === "inventory_result" && <InventoryAnswerCard data={row.data} />}</div></div>; }) : <p className="home-ai-empty">품목명이나 품목코드로 재고를 조회해보세요.</p>}</div>
    {error && <p className="home-ai-error" role="alert">{mascotStatus.message}</p>}
    <div className="home-ai-suggestions">{quick.map((item) => <button type="button" key={item} onClick={() => fillQuestion(item)}>{item}</button>)}<button type="button" className="home-ai-help-toggle" aria-expanded={helpOpen} aria-controls="home-ai-help-panel" onClick={() => setHelpOpen((open) => !open)}>질문 예시</button></div>
    {helpOpen && <section id="home-ai-help-panel" className="home-ai-help-panel" aria-label="AI 질문 예시"><SkoomiMascot state="guide" size="small" message="질문 예시를 선택하면 입력창에 채워드려요."/><div>{examples.map((item) => <button type="button" key={item} onClick={() => fillQuestion(item)}>{item}</button>)}</div></section>}
    <form className="home-ai-form" onSubmit={(e) => { e.preventDefault(); send(); }}><input ref={questionRef} value={question} maxLength={500} placeholder="품목명, 품목코드 또는 창고별 재고를 물어보세요." onChange={(e) => setQuestion(e.target.value)} onCompositionStart={() => setComposing(true)} onCompositionEnd={() => setComposing(false)} onKeyDown={(e) => { if (e.key === "Enter" && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } }} /><button type="submit" disabled={loading || !question.trim()}>{loading ? "조회 중" : "전송"}</button></form>
    <footer className="home-ai-actions"><button ref={itemButtonRef} type="button" onClick={() => setModal([])}>품목 선택</button><button type="button" onClick={reset}>대화 초기화</button></footer>
    {modal && <ItemSelectionModal candidates={modal} recent={recent} onSelect={selectItem} onClose={() => setModal(null)} returnFocusRef={itemButtonRef} />}
    {!homeAssistantApiConfigured && <span className="home-ai-config">이카운트 연결 환경 설정 후 조회할 수 있습니다.</span>}
  </section>;
}
