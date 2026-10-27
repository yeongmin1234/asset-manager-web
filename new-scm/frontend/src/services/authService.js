// The copied preview uses a fixed local identity. Remote authentication is disabled.
export const isFrontendDevMode = () => true;
export const login = async () => { throw new Error("신규 SCM 인증 API는 다음 단계에서 연결합니다."); };
export const devLogin = login;
export const restoreSession = async () => null;
export const logout = () => {};
