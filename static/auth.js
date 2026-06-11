const TOKEN_KEY = "stock_tracker_token";

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
    throw new Error(data.detail || data.message || "请求失败");
  }
  return data;
}

function requireAuth(redirectTo = "/login.html") {
  if (!getToken()) {
    window.location.href = redirectTo;
    return false;
  }
  return true;
}

function saveOAuthTokenFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  if (token) {
    setToken(token);
    window.history.replaceState({}, "", window.location.pathname);
  }
}

function logout() {
  clearToken();
  window.location.href = "/login.html";
}

function showMessage(element, text, type = "error") {
  if (!element) return;
  element.textContent = text;
  element.className = `form-message ${type}`;
}

function bindPasswordToggle(buttonId, inputId) {
  const button = document.getElementById(buttonId);
  const input = document.getElementById(inputId);
  if (!button || !input) return;
  button.addEventListener("click", () => {
    input.type = input.type === "password" ? "text" : "password";
  });
}

async function loadAuthProviders(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  try {
    const data = await fetch("/api/auth/providers").then((r) => r.json());
    if (data.wechat) {
      container.innerHTML += `<a class="oauth-btn wechat" href="/api/auth/wechat/login">微信登录</a>`;
    } else {
      container.innerHTML += `<button class="oauth-btn wechat disabled" type="button" title="需配置微信开放平台">微信登录（待配置）</button>`;
    }
    if (data.alipay) {
      container.innerHTML += `<a class="oauth-btn alipay" href="/api/auth/alipay/login">支付宝登录</a>`;
    } else {
      container.innerHTML += `<button class="oauth-btn alipay disabled" type="button" title="需配置支付宝开放平台">支付宝登录（待配置）</button>`;
    }
  } catch (error) {
    container.innerHTML = `<p class="form-note">第三方登录加载失败</p>`;
  }
}
