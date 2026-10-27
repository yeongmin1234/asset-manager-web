import React,{useState}from"react";
import{useAuth}from"../../contexts/AuthContext";
import{maskValue}from"../../utils/masking";

export default function MaskedText({value,type="name",allowReveal=false}){
  const{currentUser}=useAuth(),[revealed,setRevealed]=useState(false);
  const permitted=allowReveal&&currentUser.status==="active";
  return <span className="masked-text" title={revealed?String(value):undefined}>{revealed?value:maskValue(value,type)}{permitted&&<button type="button" onClick={e=>{e.stopPropagation();setRevealed(x=>!x)}}>{revealed?"숨기기":"전체 보기"}</button>}</span>
}
