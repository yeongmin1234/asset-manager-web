export const formatDateTime=value=>value?String(value).replace("T"," ").slice(0,19):"-";
export const formatMoney=value=>Number(value||0).toLocaleString("ko-KR");
export const formatPhone=value=>String(value||"").replace(/[^0-9-]/g,"");
