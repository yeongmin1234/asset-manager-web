import React, { useEffect, useRef, useState } from "react";

const initialProducts = [];

const emptyForm = {
  brand: "",
  code: "",
  name: "",
  boxQuantity: "",
  listPrice: "",
  order: "",
  supplyPrice: "",
  salePrice: "",
  image: null,
  preview: "",
};

const requiredFields = [
  ["brand", "브랜드"],
  ["code", "상품코드"],
  ["name", "상품명"],
  ["boxQuantity", "1박스당 상품갯수"],
  ["listPrice", "정상가"],
  ["order", "정렬순서"],
  ["supplyPrice", "공급가"],
  ["salePrice", "판매가"],
  ["image", "상품이미지"],
];

function formatPrice(value) {
  return Number(value).toLocaleString("ko-KR");
}

function ProductModal({ products, onClose, onRegister }) {
  const [form, setForm] = useState(emptyForm);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    const handleEscape = (event) => {
      if (event.key === "Escape") onClose();
    };

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: "" }));
  }

  function handleImage(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!["image/jpeg", "image/png"].includes(file.type)) {
      setForm((current) => ({ ...current, image: null, preview: "" }));
      setErrors((current) => ({ ...current, image: "jpg, jpeg, png 이미지 파일만 선택할 수 있습니다." }));
      event.target.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setForm((current) => ({ ...current, image: null, preview: "" }));
      setErrors((current) => ({ ...current, image: "이미지 크기는 5MB 이하여야 합니다." }));
      event.target.value = "";
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      setForm((current) => ({ ...current, image: file, preview: String(reader.result) }));
      setErrors((current) => ({ ...current, image: "" }));
    };
    reader.readAsDataURL(file);
  }

  function validate() {
    const nextErrors = {};
    requiredFields.forEach(([field, label]) => {
      if (!form[field]) nextErrors[field] = `${label} 항목을 입력해 주세요.`;
    });

    if (form.code && products.some((product) => product.code.toLowerCase() === form.code.trim().toLowerCase())) {
      nextErrors.code = "이미 등록된 상품코드입니다.";
    }

    ["listPrice", "supplyPrice", "salePrice"].forEach((field) => {
      if (form[field] !== "" && Number(form[field]) < 0) nextErrors[field] = "0 이상의 금액을 입력해 주세요.";
    });
    if (form.boxQuantity !== "" && Number(form.boxQuantity) < 1) nextErrors.boxQuantity = "1 이상의 수량을 입력해 주세요.";
    if (form.order !== "" && (!Number.isInteger(Number(form.order)) || Number(form.order) < 0)) {
      nextErrors.order = "0 이상의 정수를 입력해 주세요.";
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!validate()) return;

    onRegister({
      id: `temp-${form.code.trim()}`,
      date: "2026-07-27",
      brand: form.brand,
      name: form.name.trim(),
      code: form.code.trim(),
      listPrice: Number(form.listPrice),
      supplyPrice: Number(form.supplyPrice),
      salePrice: Number(form.salePrice),
      order: Number(form.order),
      color: "uploaded",
      preview: form.preview,
      fileName: form.image.name,
    });
  }

  const fields = [
    { key: "code", label: "상품코드", type: "text" },
    { key: "name", label: "상품명", type: "text" },
    { key: "boxQuantity", label: "1박스당 상품갯수", type: "number", suffix: "개", min: "1" },
    { key: "listPrice", label: "정상가", type: "number", min: "0" },
    { key: "order", label: "정렬순서", type: "number", min: "0", step: "1" },
    { key: "supplyPrice", label: "공급가", type: "number", min: "0" },
    { key: "salePrice", label: "판매가", type: "number", min: "0" },
  ];

  return (
    <div className="product-modal-layer" role="presentation">
      <section className="product-modal" role="dialog" aria-modal="true" aria-labelledby="product-modal-title">
        <div className="product-modal__header">
          <h2 id="product-modal-title">상품 등록하기</h2>
          <button type="button" onClick={onClose} aria-label="상품 등록 팝업 닫기">×</button>
        </div>
        <div className="product-modal__notice">
          <strong>(*)</strong> 매장관리프로그램에 노출할 제품을 등록하실 수 있습니다.
        </div>
        <form className="product-modal__form" onSubmit={handleSubmit} noValidate>
          <label className="product-field">
            <span><em>*</em> 브랜드</span>
            <select value={form.brand} onChange={(event) => updateField("brand", event.target.value)}>
              <option value="">브랜드 선택</option>
              <option value="Balmuda">Balmuda</option>
              <option value="Vermicular">Vermicular</option>
              <option value="Moon">Moon</option>
              <option value="기타">기타</option>
            </select>
            {errors.brand && <small>{errors.brand}</small>}
          </label>
          {fields.map((field) => (
            <label className="product-field" key={field.key}>
              <span><em>*</em> {field.label}</span>
              <div className={field.suffix ? "product-field__suffix" : ""}>
                <input
                  type={field.type}
                  min={field.min}
                  step={field.step}
                  value={form[field.key]}
                  onChange={(event) => updateField(field.key, event.target.value)}
                />
                {field.suffix && <b>{field.suffix}</b>}
              </div>
              {errors[field.key] && <small>{errors[field.key]}</small>}
            </label>
          ))}
          <label className="product-field product-field--image">
            <span><em>*</em> 상품이미지</span>
            <input type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" onChange={handleImage} />
            <p>허용 형식: jpg, jpeg, png · 최대 5MB</p>
            {form.image && <p className="selected-file">선택 파일: {form.image.name}</p>}
            {errors.image && <small>{errors.image}</small>}
            {form.preview && <img src={form.preview} alt="선택한 상품 이미지 미리보기" />}
          </label>
          <div className="product-modal__actions">
            <button type="button" onClick={onClose}>닫기</button>
            <button type="submit">상품 등록 하기</button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default function ProductManagement() {
  const [products, setProducts] = useState(initialProducts);
  const [searchType, setSearchType] = useState("name");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [toast, setToast] = useState("");
  const searchInputRef = useRef(null);

  useEffect(() => {
    const handleF8 = (event) => {
      if (event.key === "F8") {
        event.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleF8);
    return () => window.removeEventListener("keydown", handleF8);
  }, []);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 2500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const normalizedQuery = query.trim().toLowerCase();
  const filteredProducts = products.filter((product) =>
    String(product[searchType]).toLowerCase().includes(normalizedQuery),
  );

  function handleRegister(product) {
    setProducts((current) => [product, ...current]);
    setIsModalOpen(false);
    setToast(`${product.name} 상품이 임시 목록에 등록되었습니다.`);
  }

  return (
    <section className="store-content product-list-page" aria-labelledby="store-content-title">
      <div className="product-list-toolbar">
        <div>
          <h2 id="store-content-title">상품리스트</h2>
          <p>매장에 노출할 상품을 관리하는 프론트 임시 목록입니다.</p>
        </div>
        <div className="product-list-toolbar__actions">
          <button type="button" className="primary" onClick={() => setIsModalOpen(true)}>상품등록</button>
          <select value={searchType} onChange={(event) => setSearchType(event.target.value)} aria-label="검색 대상">
            <option value="name">상품명</option>
            <option value="code">상품코드</option>
            <option value="brand">브랜드</option>
          </select>
          <input
            ref={searchInputRef}
            type="search"
            value={query}
            placeholder="검색어 입력"
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="button" onClick={() => searchInputRef.current?.focus()}>검색(F8)</button>
        </div>
      </div>

      <div className="product-table-wrap">
        <table className="product-table">
          <colgroup>
            <col className="col-number" />
            <col className="col-date" />
            <col className="col-brand" />
            <col className="col-image" />
            <col className="col-name" />
            <col className="col-code" />
            <col className="col-price" />
            <col className="col-price" />
            <col className="col-price" />
            <col className="col-order" />
          </colgroup>
          <thead>
            <tr>
              <th>No.</th><th>등록일</th><th>브랜드</th><th>상품이미지</th><th>상품명</th>
              <th>상품코드</th><th>정상가</th><th>공급가</th><th>판매가</th><th>정렬순서</th>
            </tr>
          </thead>
          <tbody>
            {filteredProducts.map((product, index) => (
              <tr
                key={product.id}
                className={selectedId === product.id ? "product-table__selected" : ""}
                onClick={() => setSelectedId(product.id)}
              >
                <td>{index + 1}</td>
                <td>{product.date}</td>
                <td>{product.brand}</td>
                <td>
                  {product.preview ? (
                    <img className="product-thumb" src={product.preview} alt="" />
                  ) : (
                    <span className={`product-placeholder product-placeholder--${product.color}`}>{product.brand.slice(0, 1)}</span>
                  )}
                </td>
                <td className="product-table__name" title={product.name}>{product.name}</td>
                <td className="product-table__code" title={product.code}>{product.code}</td>
                <td className="number">{formatPrice(product.listPrice)}</td>
                <td className="number">{formatPrice(product.supplyPrice)}</td>
                <td className="number">{formatPrice(product.salePrice)}</td>
                <td className="number order-number">{product.order}</td>
              </tr>
            ))}
            {filteredProducts.length === 0 && (
              <tr><td className="product-table__empty" colSpan="10">검색 결과가 없습니다.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="product-list-footer">총 {filteredProducts.length}개 상품</div>

      {toast && <div className="product-toast" role="status">{toast}</div>}
      {isModalOpen && (
        <ProductModal
          products={products}
          onClose={() => setIsModalOpen(false)}
          onRegister={handleRegister}
        />
      )}
    </section>
  );
}
