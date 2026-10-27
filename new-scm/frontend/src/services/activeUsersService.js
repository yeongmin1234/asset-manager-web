import { ACTIVE_USERS_MOCK } from "../mocks/activeUsersMockData";

// TODO: 백엔드 권한·세션 API가 준비되면 이 인터페이스의 내부 구현만 교체합니다.
// 현재 숫자와 목록은 고정된 frontend mock이며 네트워크 요청을 수행하지 않습니다.
export function getActiveUsers() {
  return ACTIVE_USERS_MOCK.map((user) => ({ ...user }));
}

export function getActiveUserCount() {
  return ACTIVE_USERS_MOCK.length;
}
