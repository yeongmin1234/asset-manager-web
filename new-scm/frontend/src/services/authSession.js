const TOKEN_KEY = "access_token";
export const AUTH_EXPIRED_EVENT = "scm:auth-expired";

export function getAccessToken() {
  return window.localStorage.getItem(TOKEN_KEY) || window.sessionStorage.getItem(TOKEN_KEY);
}

export function storeAccessToken(token, remember) {
  clearAccessToken();
  const storage = remember ? window.localStorage : window.sessionStorage;
  storage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.sessionStorage.removeItem(TOKEN_KEY);
}

export function notifyAuthExpired() {
  clearAccessToken();
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
}
