import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createNetworkCredential,
  deleteNetworkCredential,
  getNetworkCredentialSummary,
  getNetworkCredentials,
  revealNetworkCredentialPassword,
  updateNetworkCredential,
} from "../api/client.js";
import AdminAuthModal from "./AdminAuthModal.jsx";
import NetworkCredentialForm, {
  NETWORK_CREDENTIAL_IMPORTANCE,
} from "./NetworkCredentialForm.jsx";
import NetworkCredentialList from "./NetworkCredentialList.jsx";

const UNCATEGORIZED_CATEGORY_KEY = "__uncategorized__";
const UNCATEGORIZED_CATEGORY_LABEL = "기타";

const EMPTY_SUMMARY = {
  total: 0,
  important: 0,
  critical: 0,
  with_password: 0,
};

function NetworkCredentialPage() {
  const [credentials, setCredentials] = useState([]);
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [filters, setFilters] = useState({ keyword: "", importance: "" });
  const [selectedCategory, setSelectedCategory] = useState("");
  const [listState, setListState] = useState({ error: "", isLoading: false });
  const [formState, setFormState] = useState({
    credential: null,
    error: "",
    isOpen: false,
    isSubmitting: false,
  });
  const [revealedPasswords, setRevealedPasswords] = useState({});
  const [copyMessage, setCopyMessage] = useState("");
  const [authState, setAuthState] = useState({
    credential: null,
    error: "",
    isOpen: false,
    isSubmitting: false,
    mode: "reveal",
  });
  const hideTimersRef = useRef({});

  const activeFilters = useMemo(
    () => ({
      keyword: filters.keyword.trim(),
      importance: filters.importance,
    }),
    [filters],
  );

  const categoryTabs = useMemo(() => {
    const counts = new Map();
    credentials.forEach((credential) => {
      const category = normalizeCategory(credential.category);
      counts.set(category.key, {
        key: category.key,
        label: category.label,
        count: (counts.get(category.key)?.count || 0) + 1,
      });
    });

    return [
      { key: "", label: "전체", count: credentials.length },
      ...Array.from(counts.values()),
    ];
  }, [credentials]);

  const displayedCredentials = useMemo(() => {
    if (!selectedCategory) {
      return credentials;
    }
    return credentials.filter((credential) => normalizeCategory(credential.category).key === selectedCategory);
  }, [credentials, selectedCategory]);

  const loadCredentials = useCallback(async () => {
    setListState({ error: "", isLoading: true });
    try {
      const [items, nextSummary] = await Promise.all([
        getNetworkCredentials(activeFilters),
        getNetworkCredentialSummary(),
      ]);
      setCredentials(Array.isArray(items) ? items : []);
      setSummary({ ...EMPTY_SUMMARY, ...(nextSummary || {}) });
      setListState({ error: "", isLoading: false });
    } catch (error) {
      setCredentials([]);
      setSummary(EMPTY_SUMMARY);
      setListState({ error: error.message, isLoading: false });
    }
  }, [activeFilters]);

  useEffect(() => {
    loadCredentials();
  }, [loadCredentials]);

  useEffect(() => {
    if (selectedCategory && !categoryTabs.some((tab) => tab.key === selectedCategory)) {
      setSelectedCategory("");
    }
  }, [categoryTabs, selectedCategory]);

  useEffect(
    () => () => {
      Object.values(hideTimersRef.current).forEach((timerId) => window.clearTimeout(timerId));
    },
    [],
  );

  const handleSubmit = async (payload) => {
    setFormState((current) => ({ ...current, error: "", isSubmitting: true }));
    try {
      if (formState.credential) {
        await updateNetworkCredential(formState.credential.id, payload);
      } else {
        await createNetworkCredential(payload);
      }
      setFormState({ credential: null, error: "", isOpen: false, isSubmitting: false });
      await loadCredentials();
    } catch (error) {
      setFormState((current) => ({ ...current, error: error.message, isSubmitting: false }));
    }
  };

  const handleDelete = async (credential) => {
    const ok = window.confirm(`'${credential.service_name}' 접속정보를 삭제하시겠습니까?`);
    if (!ok) {
      return;
    }

    try {
      await deleteNetworkCredential(credential.id);
      clearRevealedPassword(credential.id);
      await loadCredentials();
    } catch (error) {
      setListState({ error: error.message, isLoading: false });
    }
  };

  const openRevealAuth = (credential, mode = "reveal") => {
    setAuthState({
      credential,
      error: "",
      isOpen: true,
      isSubmitting: false,
      mode,
    });
  };

  const handleAuthSubmit = async (adminPassword) => {
    if (!authState.credential) {
      return;
    }
    setAuthState((current) => ({ ...current, error: "", isSubmitting: true }));
    try {
      const result = await revealNetworkCredentialPassword(authState.credential.id, adminPassword);
      const password = result?.password || "";
      if (password) {
        showTemporaryPassword(authState.credential.id, password, Number(result?.expires_in || 15));
        if (authState.mode === "copy") {
          await copyText(password);
          showCopyMessage("복사되었습니다.");
        }
      } else {
        showCopyMessage(result?.message || "등록된 비밀번호가 없습니다.");
      }
      setAuthState({ credential: null, error: "", isOpen: false, isSubmitting: false, mode: "reveal" });
    } catch (error) {
      setAuthState((current) => ({ ...current, error: error.message, isSubmitting: false }));
    }
  };

  const handleCopyPassword = async (credential) => {
    const visiblePassword = revealedPasswords[credential.id];
    if (visiblePassword) {
      await copyText(visiblePassword);
      showCopyMessage("복사되었습니다.");
      scheduleHide(credential.id, 15);
      return;
    }

    openRevealAuth(credential, "copy");
  };

  const handleCopyText = async (value) => {
    if (!value) {
      return;
    }
    await copyText(value);
    showCopyMessage("복사되었습니다.");
  };

  const showTemporaryPassword = (credentialId, password, expiresIn) => {
    setRevealedPasswords((current) => ({
      ...current,
      [credentialId]: password,
    }));
    scheduleHide(credentialId, expiresIn || 15);
  };

  const scheduleHide = (credentialId, expiresIn) => {
    if (hideTimersRef.current[credentialId]) {
      window.clearTimeout(hideTimersRef.current[credentialId]);
    }
    hideTimersRef.current[credentialId] = window.setTimeout(() => {
      clearRevealedPassword(credentialId);
    }, Math.max(1, Number(expiresIn || 15)) * 1000);
  };

  const clearRevealedPassword = (credentialId) => {
    if (hideTimersRef.current[credentialId]) {
      window.clearTimeout(hideTimersRef.current[credentialId]);
      delete hideTimersRef.current[credentialId];
    }
    setRevealedPasswords((current) => {
      const next = { ...current };
      delete next[credentialId];
      return next;
    });
  };

  const showCopyMessage = (message) => {
    setCopyMessage(message);
    window.setTimeout(() => setCopyMessage(""), 2500);
  };

  return (
    <section className="network-credential-page">
      <div className="network-credential-toolbar">
        <div>
          <h3>접속정보 관리</h3>
          <p>내부 주소, 외부 URL, 계정과 비밀번호를 안전하게 관리합니다.</p>
        </div>
        <button
          type="button"
          className="primary-button"
          onClick={() => setFormState({ credential: null, error: "", isOpen: true, isSubmitting: false })}
        >
          등록
        </button>
      </div>

      <div className="network-credential-security-note" role="note">
        비밀번호는 암호화되어 저장되며, 보기/복사 후 15초 뒤 자동으로 숨겨집니다.
      </div>

      <section className="network-credential-summary" aria-label="접속정보 요약">
        <SummaryCard label="전체" value={summary.total} />
        <SummaryCard label="중요" value={summary.important} tone="important" />
        <SummaryCard label="매우중요" value={summary.critical} tone="critical" />
        <SummaryCard label="비밀번호 등록" value={summary.with_password} tone="password" />
      </section>

      <section className="content-panel network-credential-panel">
        <div className="network-credential-filters">
          <label className="field">
            <span>검색어</span>
            <input
              value={filters.keyword}
              placeholder="서비스명, 주소, 계정, 비고"
              onChange={(event) => setFilters((current) => ({ ...current, keyword: event.target.value }))}
            />
          </label>
          <label className="field">
            <span>중요도</span>
            <select
              value={filters.importance}
              onChange={(event) => setFilters((current) => ({ ...current, importance: event.target.value }))}
            >
              <option value="">전체</option>
              {NETWORK_CREDENTIAL_IMPORTANCE.map((importance) => (
                <option key={importance} value={importance}>{importance}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setSelectedCategory("");
              loadCredentials();
            }}
            disabled={listState.isLoading}
          >
            새로고침
          </button>
        </div>

        <CategoryTabs tabs={categoryTabs} selectedCategory={selectedCategory} onSelect={setSelectedCategory} />

        {copyMessage ? <p className="network-credential-message">{copyMessage}</p> : null}

        <NetworkCredentialList
          credentials={displayedCredentials}
          error={listState.error}
          isLoading={listState.isLoading}
          revealedPasswords={revealedPasswords}
          onCopyText={handleCopyText}
          onCopyPassword={handleCopyPassword}
          onDelete={handleDelete}
          onEdit={(credential) => setFormState({ credential, error: "", isOpen: true, isSubmitting: false })}
          onRevealPassword={(credential) => openRevealAuth(credential, "reveal")}
        />
      </section>

      <NetworkCredentialForm
        credential={formState.credential}
        error={formState.error}
        isOpen={formState.isOpen}
        isSubmitting={formState.isSubmitting}
        onClose={() => setFormState({ credential: null, error: "", isOpen: false, isSubmitting: false })}
        onSubmit={handleSubmit}
      />

      <AdminAuthModal
        error={authState.error}
        isOpen={authState.isOpen}
        isSubmitting={authState.isSubmitting}
        menuLabel="접속정보 비밀번호 보기"
        onCancel={() => setAuthState({ credential: null, error: "", isOpen: false, isSubmitting: false, mode: "reveal" })}
        onSubmit={handleAuthSubmit}
      />
    </section>
  );
}

function CategoryTabs({ tabs, selectedCategory, onSelect }) {
  return (
    <div className="network-credential-category-tabs" role="tablist" aria-label="접속정보 구분">
      {tabs.map((tab) => {
        const active = tab.key === selectedCategory;
        return (
          <button
            key={tab.key || "all"}
            type="button"
            className={`network-credential-category-chip${active ? " active" : ""}`}
            onClick={() => onSelect(tab.key)}
            role="tab"
            aria-selected={active}
          >
            <span>{tab.label}</span>
            <span className="network-credential-category-count">{tab.count}</span>
          </button>
        );
      })}
    </div>
  );
}

function SummaryCard({ label, value, tone = "normal" }) {
  return (
    <article className={`network-credential-summary-card network-credential-summary-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function normalizeCategory(value) {
  const label = String(value || "").trim();
  if (!label) {
    return { key: UNCATEGORIZED_CATEGORY_KEY, label: UNCATEGORIZED_CATEGORY_LABEL };
  }
  return { key: label, label };
}

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

export default NetworkCredentialPage;
