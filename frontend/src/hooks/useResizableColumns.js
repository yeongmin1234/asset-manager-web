import { useMemo, useRef, useState } from "react";

function useResizableColumns(columns, storageKey, resizeClassName = "table-column-resizing") {
  const [columnWidths, setColumnWidths] = useState(() =>
    getInitialColumnWidths(columns, storageKey),
  );
  const resizeStateRef = useRef(null);

  const tableWidth = useMemo(
    () => columns.reduce((total, column) => total + columnWidths[column.key], 0),
    [columnWidths, columns],
  );

  const resetColumnWidths = () => {
    const nextWidths = columns.reduce(
      (widths, column) => ({ ...widths, [column.key]: column.initialWidth }),
      {},
    );
    setColumnWidths(nextWidths);
    saveColumnWidths(storageKey, nextWidths);
  };

  const handleColumnResizeStart = (event, column) => {
    event.preventDefault();
    event.stopPropagation();
    resizeStateRef.current = {
      key: column.key,
      minWidth: column.minWidth || 80,
      startX: event.clientX,
      startWidth: columnWidths[column.key],
    };
    document.body.classList.add(resizeClassName);

    const handleMouseMove = (moveEvent) => {
      const resizeState = resizeStateRef.current;
      if (!resizeState) {
        return;
      }
      const nextWidth = Math.max(
        resizeState.minWidth,
        resizeState.startWidth + moveEvent.clientX - resizeState.startX,
      );
      setColumnWidths((currentWidths) => {
        const nextWidths = { ...currentWidths, [resizeState.key]: nextWidth };
        saveColumnWidths(storageKey, nextWidths);
        return nextWidths;
      });
    };

    const handleMouseUp = () => {
      resizeStateRef.current = null;
      document.body.classList.remove(resizeClassName);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  };

  return {
    columnWidths,
    handleColumnResizeStart,
    resetColumnWidths,
    tableWidth,
  };
}

function getInitialColumnWidths(columns, storageKey) {
  const defaultWidths = columns.reduce(
    (widths, column) => ({ ...widths, [column.key]: column.initialWidth }),
    {},
  );

  if (typeof window === "undefined") {
    return defaultWidths;
  }

  try {
    const savedWidths = JSON.parse(window.localStorage.getItem(storageKey) || "{}");
    return columns.reduce((widths, column) => {
      const savedWidth = Number(savedWidths[column.key]);
      return {
        ...widths,
        [column.key]: Number.isFinite(savedWidth)
          ? Math.max(column.minWidth || 80, savedWidth)
          : column.initialWidth,
      };
    }, {});
  } catch {
    return defaultWidths;
  }
}

function saveColumnWidths(storageKey, widths) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(storageKey, JSON.stringify(widths));
  } catch {
    // Ignore storage failures; resizing still works for the current page state.
  }
}

export default useResizableColumns;
