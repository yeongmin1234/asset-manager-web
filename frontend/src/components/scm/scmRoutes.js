export const SCM_BASE_PATH = "/scm-app";

export function isScmAppPath(path) {
  return path === SCM_BASE_PATH || path.startsWith(`${SCM_BASE_PATH}/`);
}

export function toScmInnerPath(path) {
  if (path === SCM_BASE_PATH || path === `${SCM_BASE_PATH}/home`) return "/";
  if (path === `${SCM_BASE_PATH}/stores`) return "/store-management/stores";
  if (path === `${SCM_BASE_PATH}/stores/staff`) return "/store-management/staff";
  if (path.startsWith(`${SCM_BASE_PATH}/stores/`)) {
    return `/store-management/${path.slice(`${SCM_BASE_PATH}/stores/`.length)}`;
  }
  return path.slice(SCM_BASE_PATH.length) || "/";
}

export function toScmSitePath(innerPath) {
  if (innerPath === "/") return `${SCM_BASE_PATH}/home`;
  if (innerPath === "/store-management/stores") return `${SCM_BASE_PATH}/stores`;
  if (innerPath.startsWith("/store-management/")) {
    return `${SCM_BASE_PATH}/stores/${innerPath.slice("/store-management/".length)}`;
  }
  return `${SCM_BASE_PATH}${innerPath}`;
}
