const TOKEN_KEY = "stock_tracker_token";
const ASSET_VERSION = "3.1.1";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function isLoggedIn() {
  return Boolean(getToken());
}

function formatApiError(data) {
  const detail = data?.detail ?? data?.message;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join("；");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return detail || "请求失败";
}

async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(formatApiError(data));
  }
  return data;
}

function logout() {
  clearToken();
  window.location.href = "/";
}

function showMessage(element, text, type = "error") {
  if (!element) return;
  element.textContent = text;
  element.className = `form-message ${type}`;
}
