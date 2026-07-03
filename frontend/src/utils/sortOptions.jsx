import React from "react";

export const SORT_VALUES = {
  latest: "latest",
  oldest: "oldest",
  name: "name",
  title: "title",
  recentlyUpdated: "recently_updated",
  expiryNearest: "expiry_nearest",
};

export const SORT_LABELS = {
  [SORT_VALUES.latest]: "최신순",
  [SORT_VALUES.oldest]: "오래된순",
  [SORT_VALUES.name]: "이름순",
  [SORT_VALUES.title]: "제목순",
  [SORT_VALUES.recentlyUpdated]: "최근 수정순",
  [SORT_VALUES.expiryNearest]: "만료일 가까운순",
};

export const BOARD_SORT_OPTIONS = [
  SORT_VALUES.latest,
  SORT_VALUES.oldest,
  SORT_VALUES.title,
  SORT_VALUES.recentlyUpdated,
];

export const ASSET_SORT_OPTIONS = [
  SORT_VALUES.latest,
  SORT_VALUES.oldest,
  SORT_VALUES.name,
  SORT_VALUES.recentlyUpdated,
];

export const INFO_EXPIRY_SORT_OPTIONS = [
  SORT_VALUES.latest,
  SORT_VALUES.oldest,
  SORT_VALUES.name,
  SORT_VALUES.recentlyUpdated,
  SORT_VALUES.expiryNearest,
];

export const VEHICLE_SORT_OPTIONS = [
  SORT_VALUES.latest,
  SORT_VALUES.oldest,
  SORT_VALUES.name,
  SORT_VALUES.recentlyUpdated,
  SORT_VALUES.expiryNearest,
];

export const HISTORY_SORT_OPTIONS = [
  SORT_VALUES.latest,
  SORT_VALUES.oldest,
];

export function SortSelect({ value, options, onChange, label = "정렬" }) {
  const safeOptions = Array.isArray(options) ? options : [];
  return (
    <label className="field sort-control">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange?.(event.target.value)}>
        {safeOptions.map((option) => (
          <option key={option} value={option}>
            {SORT_LABELS[option] || option}
          </option>
        ))}
      </select>
    </label>
  );
}

export function sortItems(items, sortValue, fields) {
  const safeItems = Array.isArray(items) ? items : [];
  const safeFields = fields || {};
  const value = sortValue || SORT_VALUES.latest;
  return [...safeItems].sort((left, right) => compareItems(left, right, value, safeFields));
}

function compareItems(left, right, sortValue, fields) {
  if (sortValue === SORT_VALUES.name) {
    return compareText(getFirstFieldValue(left, fields.name), getFirstFieldValue(right, fields.name));
  }
  if (sortValue === SORT_VALUES.title) {
    return compareText(getFirstFieldValue(left, fields.title), getFirstFieldValue(right, fields.title));
  }
  if (sortValue === SORT_VALUES.oldest) {
    return compareDate(getFirstFieldValue(left, fields.created), getFirstFieldValue(right, fields.created), "asc");
  }
  if (sortValue === SORT_VALUES.recentlyUpdated) {
    return compareDate(getFirstFieldValue(left, fields.updated), getFirstFieldValue(right, fields.updated), "desc");
  }
  if (sortValue === SORT_VALUES.expiryNearest) {
    return compareDate(getFirstFieldValue(left, fields.expiry), getFirstFieldValue(right, fields.expiry), "asc");
  }
  return compareDate(getFirstFieldValue(left, fields.created), getFirstFieldValue(right, fields.created), "desc");
}

function getFirstFieldValue(item, fieldNames) {
  const names = Array.isArray(fieldNames) ? fieldNames : [fieldNames];
  for (const name of names) {
    if (name && item?.[name] !== undefined && item?.[name] !== null && item?.[name] !== "") {
      return item[name];
    }
  }
  return "";
}

function compareText(leftValue, rightValue) {
  const leftText = String(leftValue || "").trim();
  const rightText = String(rightValue || "").trim();
  if (!leftText && !rightText) {
    return 0;
  }
  if (!leftText) {
    return 1;
  }
  if (!rightText) {
    return -1;
  }
  return leftText.localeCompare(rightText, "ko-KR", { numeric: true, sensitivity: "base" });
}

function compareDate(leftValue, rightValue, direction) {
  const leftTime = getDateTime(leftValue);
  const rightTime = getDateTime(rightValue);
  if (leftTime === null && rightTime === null) {
    return 0;
  }
  if (leftTime === null) {
    return 1;
  }
  if (rightTime === null) {
    return -1;
  }
  return direction === "asc" ? leftTime - rightTime : rightTime - leftTime;
}

function getDateTime(value) {
  if (!value) {
    return null;
  }
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? null : timestamp;
}
