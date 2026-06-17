import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  createVehicleInsuranceHistory,
  deleteVehicleInsuranceHistory,
  getVehicleInsuranceHistories,
  updateVehicleInsuranceHistory,
} from "../api/client.js";

const INITIAL_FORM = {
  start_date: "",
  end_date: "",
  insurance_type: "",
  driver_name: "",
  amount: "",
  payment_method: "",
  note: "",
};

function VehicleInsuranceHistory({ vehicles }) {
  const safeVehicles = Array.isArray(vehicles) ? vehicles : [];
  const [selectedVehicleId, setSelectedVehicleId] = useState("");
  const [items, setItems] = useState([]);
  const [state, setState] = useState({ isLoading: false, error: "" });
  const [form, setForm] = useState(INITIAL_FORM);
  const [editingItem, setEditingItem] = useState(null);
  const [actionError, setActionError] = useState("");

  const selectedVehicle = useMemo(
    () => safeVehicles.find((vehicle) => String(vehicle.id) === String(selectedVehicleId)) || null,
    [safeVehicles, selectedVehicleId],
  );

  const loadItems = useCallback(async () => {
    if (!selectedVehicleId) {
      setItems([]);
      setState({ isLoading: false, error: "" });
      return;
    }
    setState({ isLoading: true, error: "" });
    try {
      setItems(await getVehicleInsuranceHistories(selectedVehicleId));
      setState({ isLoading: false, error: "" });
    } catch (error) {
      setItems([]);
      setState({ isLoading: false, error: error.message });
    }
  }, [selectedVehicleId]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  const handleVehicleChange = (event) => {
    setSelectedVehicleId(event.target.value);
    setEditingItem(null);
    setForm(INITIAL_FORM);
    setActionError("");
  };

  const handleChange = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
    setActionError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!selectedVehicleId) {
      setActionError("차량을 선택해주세요.");
      return;
    }

    const payload = {
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      insurance_type: textOrNull(form.insurance_type),
      driver_name: textOrNull(form.driver_name),
      amount: form.amount === "" ? null : Number(form.amount),
      payment_method: textOrNull(form.payment_method),
      note: textOrNull(form.note),
    };

    try {
      if (editingItem) {
        await updateVehicleInsuranceHistory(editingItem.id, payload);
      } else {
        await createVehicleInsuranceHistory(selectedVehicleId, payload);
      }
      setEditingItem(null);
      setForm(INITIAL_FORM);
      await loadItems();
    } catch (error) {
      setActionError(error.message);
    }
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setForm({
      start_date: item.start_date || "",
      end_date: item.end_date || "",
      insurance_type: item.insurance_type || "",
      driver_name: item.driver_name || "",
      amount: String(item.amount ?? ""),
      payment_method: item.payment_method || "",
      note: item.note || "",
    });
    setActionError("");
  };

  const handleCancelEdit = () => {
    setEditingItem(null);
    setForm(INITIAL_FORM);
    setActionError("");
  };

  const handleDelete = async (item) => {
    const confirmed = window.confirm("선택한 보험 이력을 삭제할까요?");
    if (!confirmed) {
      return;
    }
    try {
      await deleteVehicleInsuranceHistory(item.id);
      if (editingItem?.id === item.id) {
        handleCancelEdit();
      }
      await loadItems();
    } catch (error) {
      setActionError(error.message);
    }
  };

  return (
    <div className="vehicle-history-panel">
      <label className="field vehicle-history-selector">
        <span>차량 선택</span>
        <select value={selectedVehicleId} onChange={handleVehicleChange}>
          <option value="">차량을 선택해주세요.</option>
          {safeVehicles.map((vehicle) => (
            <option key={vehicle.id} value={vehicle.id}>
              {formatVehicleOption(vehicle)}
            </option>
          ))}
        </select>
      </label>

      {!selectedVehicle ? (
        <div className="state-panel">차량을 선택해주세요.</div>
      ) : (
        <>
          <div className="vehicle-history-selected">
            <strong>{formatText(selectedVehicle.vehicle_number)}</strong>
            <span>{formatText(selectedVehicle.vehicle_name)}</span>
            <span>{formatText(selectedVehicle.driver_name)}</span>
          </div>

          <div className="asset-table-wrap">
            <table className="asset-table vehicle-history-table">
              <thead>
                <tr>
                  <th>기간</th>
                  <th>보험 유형</th>
                  <th>대상자/운전자</th>
                  <th>금액</th>
                  <th>결제/처리 방식</th>
                  <th>비고</th>
                  <th>관리</th>
                </tr>
              </thead>
              <tbody>
                {state.isLoading ? (
                  <tr>
                    <td colSpan="7">보험 이력을 불러오는 중입니다.</td>
                  </tr>
                ) : state.error ? (
                  <tr>
                    <td colSpan="7">보험 이력을 불러오지 못했습니다. {state.error}</td>
                  </tr>
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan="7">등록된 보험 이력이 없습니다.</td>
                  </tr>
                ) : (
                  items.map((item) => (
                    <tr key={item.id}>
                      <td>{formatPeriod(item.start_date, item.end_date)}</td>
                      <td>{formatText(item.insurance_type)}</td>
                      <td>{formatText(item.driver_name)}</td>
                      <td>{formatCurrency(item.amount)}</td>
                      <td>{formatText(item.payment_method)}</td>
                      <td className="vehicle-history-note-cell">{formatText(item.note)}</td>
                      <td>
                        <div className="software-row-actions">
                          <button
                            type="button"
                            className="secondary-button software-action-button"
                            onClick={() => handleEdit(item)}
                          >
                            수정
                          </button>
                          <button
                            type="button"
                            className="danger-button software-action-button"
                            onClick={() => handleDelete(item)}
                          >
                            삭제
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <form className="vehicle-history-form" onSubmit={handleSubmit}>
            <Field name="start_date" label="시작일" type="date" value={form.start_date} onChange={handleChange} />
            <Field name="end_date" label="종료일" type="date" value={form.end_date} onChange={handleChange} />
            <label className="field">
              <span>보험 유형</span>
              <select name="insurance_type" value={form.insurance_type} onChange={handleChange}>
                <option value="">선택 안 함</option>
                <option value="누구나">누구나</option>
                <option value="임직원">임직원</option>
                <option value="단기 누구나">단기 누구나</option>
                <option value="기타">기타</option>
              </select>
            </label>
            <Field name="driver_name" label="대상자/운전자" value={form.driver_name} onChange={handleChange} />
            <Field name="amount" label="금액" type="number" min="0" value={form.amount} onChange={handleChange} />
            <Field name="payment_method" label="결제/처리 방식" value={form.payment_method} onChange={handleChange} />
            <label className="field vehicle-history-note-field">
              <span>비고</span>
              <textarea name="note" rows="2" value={form.note} onChange={handleChange} />
            </label>
            <div className="quick-create-actions">
              {actionError && <span className="inline-alert">{actionError}</span>}
              {editingItem && (
                <button type="button" className="secondary-button" onClick={handleCancelEdit}>
                  수정 취소
                </button>
              )}
              <button type="submit" className="primary-action">
                {editingItem ? "수정 저장" : "이력 등록"}
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  );
}

function Field({ label, ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input {...props} />
    </label>
  );
}

function formatVehicleOption(vehicle) {
  return `${formatText(vehicle.vehicle_number)} / ${formatText(vehicle.vehicle_name)} / ${formatText(vehicle.driver_name)}`;
}

function formatText(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatPeriod(startDate, endDate) {
  return `${formatText(startDate)} ~ ${formatText(endDate)}`;
}

function formatCurrency(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return Number(value || 0).toLocaleString("ko-KR");
}

function textOrNull(value) {
  const trimmedValue = value.trim();
  return trimmedValue || null;
}

export default VehicleInsuranceHistory;
