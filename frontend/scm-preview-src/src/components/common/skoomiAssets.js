const imageModules = import.meta.glob(
  "../../assets/skoomi/skoomi-{default,searching,success,guide,empty,error,avatar}.png",
  { eager: true, import: "default" },
);

export const SKOOMI_STATES = Object.freeze(["default", "searching", "success", "guide", "empty", "error"]);
const defaultImage = imageModules["../../assets/skoomi/skoomi-default.png"];

// 상태 파일이 존재하면 자동 사용하고, 없으면 default를 공유합니다.
export const skoomiImages = Object.freeze(Object.fromEntries(
  SKOOMI_STATES.map((state) => [
    state,
    imageModules[`../../assets/skoomi/skoomi-${state}.png`] || defaultImage,
  ]),
));

const avatarImage = imageModules["../../assets/skoomi/skoomi-avatar.png"];
export const getSkoomiImage = (state, size) => size === "avatar" && avatarImage
  ? avatarImage
  : skoomiImages[state] || skoomiImages.default;
