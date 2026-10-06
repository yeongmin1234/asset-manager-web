import React,{useState}from"react";
import{EmptyState,PageHeader,Toolbar}from"../components/common/CommonUI";
import SkoomiMascot from "../components/common/SkoomiMascot";
function Workspace({title,description,conditionLabel,placeholder}){const[input,setInput]=useState(""),[keyword,setKeyword]=useState("");return <section className="ui-workspace-page"><PageHeader title={title} description={description}/><Toolbar><label><span>{conditionLabel}</span><input value={input} placeholder={placeholder} onChange={e=>setInput(e.target.value)}/></label><button type="button" className="primary" onClick={()=>setKeyword(input.trim())}>검색</button><button type="button" onClick={()=>{setInput("");setKeyword("")}}>초기화</button></Toolbar><EmptyState message={keyword?"검색 결과가 없습니다.":"등록된 데이터가 없습니다."}/></section>}
export const CustomerManagementPage=()=> <Workspace title="고객관리" description="고객 기본정보를 검색하고 관리하는 업무 화면입니다." conditionLabel="고객 검색" placeholder="고객명 또는 연락처"/>;
export const OrderSupportPage=()=> <Workspace title="발주지원센터" description="발주 지원 요청과 처리 상태를 확인하는 업무 화면입니다." conditionLabel="발주 검색" placeholder="요청번호 또는 상품명"/>;
export const MemoSearchPage=()=> <Workspace title="메모검색" description="업무 화면에 등록된 메모를 통합 검색합니다." conditionLabel="메모 검색" placeholder="검색할 메모 내용"/>;
export function NotFoundPage({onHome}){return <section className="ui-not-found"><strong>404</strong><h1>요청하신 페이지를 찾지 못했어요.</h1><SkoomiMascot state="error" size="large" message="주소를 확인하거나 HOME으로 이동해주세요."/><button type="button" className="primary" onClick={onHome}>HOME으로 이동</button></section>}
