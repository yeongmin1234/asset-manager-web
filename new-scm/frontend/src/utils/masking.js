export function maskName(value=""){const text=String(value);if(text.length<2)return text?`${text[0]}*`:"";if(text.length===2)return `${text[0]}*`;return `${text[0]}${"*".repeat(Math.max(1,text.length-2))}${text.at(-1)}`}
export function maskPhone(value=""){const text=String(value);return text.replace(/(\d{2,3}-\d{2})\d{2}(-\d{4})/,"$1**$2")}
export function maskEmail(value=""){const[email,domain]=String(value).split("@");if(!domain)return value;return `${email.slice(0,2)}${"*".repeat(Math.max(2,email.length-2))}@${domain}`}
export function maskAddress(value=""){const parts=String(value).trim().split(/\s+/);return parts.length>1?`${parts.slice(0,2).join(" ")} ***`:"***"}
export function maskValue(value,type){if(type==="name")return maskName(value);if(type==="phone")return maskPhone(value);if(type==="email")return maskEmail(value);if(type==="address")return maskAddress(value);return value}
