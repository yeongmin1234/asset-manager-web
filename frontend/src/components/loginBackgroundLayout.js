export const LOGIN_BACKGROUND_SIZE = { width: 1779, height: 884 };

export function imagePointToScreen(point, width, height) {
  const scale = Math.max(width / LOGIN_BACKGROUND_SIZE.width, height / LOGIN_BACKGROUND_SIZE.height);
  return {
    x: (width - LOGIN_BACKGROUND_SIZE.width * scale) / 2 + point.x * LOGIN_BACKGROUND_SIZE.width * scale,
    y: (height - LOGIN_BACKGROUND_SIZE.height * scale) / 2 + point.y * LOGIN_BACKGROUND_SIZE.height * scale,
    scale,
  };
}
