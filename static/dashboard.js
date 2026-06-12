const REFRESH_MS = 30000;

const quoteCards = document.getElementById("quote-cards");
const statusPill = document.getElementById("status-pill");
const lastUpdated = document.getElementById("last-updated");
const userLabel = document.getElementById("user-label");
const navActions = document.getElementById("nav-actions");
const heroSubtitle = document.getElementById("hero-subtitle");
const preferencesPanel = document.getElementById("preferences-panel");
const symbolPicker = document.getElementById("symbol-picker");
const newsLimitInput = document.getElementById("news-limit");
const newsLimitValue = document.getElementById("news-limit-value");
const savePreferencesBtn = document.getElementById("save-preferences-btn");
const preferencesMessage = document.getElementById("preferences-message");

let currentUser = null;
let selectedSymbols = new Set();
let availableSymbols = [];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatPrice(value, currency = "USD") {
  if (value == null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(value);
}

function formatChange(change, changePercent) {
  if (change == null || changePercent == null) {
    return { text: "暂无变动数据", className: "neutral" };
  }

  const sign = change >= 0 ? "+" : "";
  return {
    text: `${sign}${change.toFixed(2)} (${sign}${changePercent.toFixed(2)}%)`,
    className: change >= 0 ? "positive" : "negative",
  };
}

function formatDate(value) {
  if (!value) return "时间未知";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatOdds(value) {
  if (value == null) return "--";
  return `${value.toFixed(1)}%`;
}

function renderNav() {
  if (currentUser) {
    const name = currentUser.display_name || currentUser.email || "用户";
    userLabel.textContent = name;
    const adminLink = currentUser.is_admin
      ? `<a class="nav-btn" href="/admin.html">管理后台</a>`
      : "";
    navActions.innerHTML = `
      ${adminLink}
      <a class="nav-btn" href="#" id="logout-btn">退出</a>
    `;
    document.getElementById("logout-btn").addEventListener("click", (event) => {
      event.preventDefault();
      logout();
    });
    preferencesPanel.classList.remove("hidden");
    heroSubtitle.textContent = "你已登录，可在下方自定义关注的股票和新闻数量。";
    return;
  }

  userLabel.textContent = "访客模式";
  navActions.innerHTML = `
    <a class="nav-btn" href="/login.html">登录</a>
    <a class="nav-btn" href="/register.html">注册</a>
  `;
  preferencesPanel.classList.add("hidden");
  heroSubtitle.textContent = "无需注册即可浏览默认行情。注册登录后可自选关注的股票和新闻数量。";
}

function renderSymbolPicker() {
  symbolPicker.innerHTML = availableSymbols
    .map((item) => {
      const checked = selectedSymbols.has(item.symbol) ? "checked" : "";
      return `
        <label class="symbol-chip">
          <input type="checkbox" value="${escapeHtml(item.symbol)}" ${checked} />
          <span class="symbol-chip-label">
            <strong>${escapeHtml(item.symbol)}</strong>
            <small>${escapeHtml(item.name)}</small>
          </span>
        </label>
      `;
    })
    .join("");

  symbolPicker.querySelectorAll('input[type="checkbox"]').forEach((input) => {
    input.addEventListener("change", () => {
      if (input.checked) {
        selectedSymbols.add(input.value);
      } else {
        selectedSymbols.delete(input.value);
      }
    });
  });
}

function renderPolymarketMarkets(quote) {
  const markets = quote.polymarket || [];
  const searchUrl = quote.polymarket_search_url || "https://polymarket.com/";

  if (!markets.length) {
    return `
      <div class="poly-block">
        <div class="poly-head">
          <span>Polymarket 赔率</span>
          <a href="${escapeHtml(searchUrl)}" target="_blank" rel="noopener noreferrer">查看更多</a>
        </div>
        <p class="poly-empty">暂无相关预测市场</p>
      </div>
    `;
  }

  const items = markets
    .slice(0, 3)
    .map(
      (market) => `
        <a class="poly-item" href="${escapeHtml(market.url)}" target="_blank" rel="noopener noreferrer">
          <p class="poly-title">${escapeHtml(market.title)}</p>
          <div class="poly-odds">
            <span class="poly-yes">${escapeHtml(market.yes_label)} ${formatOdds(market.yes_odds)}</span>
            <span class="poly-no">${escapeHtml(market.no_label)} ${formatOdds(market.no_odds)}</span>
          </div>
        </a>
      `
    )
    .join("");

  return `
    <div class="poly-block">
      <div class="poly-head">
        <span>Polymarket 赔率</span>
        <a href="${escapeHtml(searchUrl)}" target="_blank" rel="noopener noreferrer">搜索 ${escapeHtml(quote.symbol)}</a>
      </div>
      ${items}
    </div>
  `;
}

function renderStockNews(quote, newsLimit) {
  const news = (quote.news || []).slice(0, newsLimit);

  if (!news.length) {
    return `
      <div class="news-block">
        <div class="news-head">Yahoo Finance 新闻</div>
        <p class="news-empty">暂无新闻</p>
      </div>
    `;
  }

  const items = news
    .map(
      (item) => `
        <a class="news-item" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener noreferrer">
          <p class="news-item-title">${escapeHtml(item.title)}</p>
          <p class="news-item-summary">${escapeHtml(item.summary || "Yahoo Finance 新闻")}</p>
          <div class="news-item-meta">
            <span>${escapeHtml(item.publisher || "Yahoo Finance")}</span>
            <span>${formatDate(item.published_at)}</span>
          </div>
        </a>
      `
    )
    .join("");

  return `
    <div class="news-block">
      <div class="news-head">Yahoo Finance 新闻</div>
      <div class="news-list">${items}</div>
    </div>
  `;
}

function renderQuotes(quotes, newsLimit) {
  quoteCards.style.gridTemplateColumns = `repeat(${Math.min(quotes.length, 3)}, minmax(0, 1fr))`;

  if (!quotes.length) {
    quoteCards.innerHTML = `<div class="empty-state">暂无股票数据</div>`;
    return;
  }

  quoteCards.innerHTML = quotes
    .map((quote) => {
      const change = formatChange(quote.change, quote.change_percent);
      return `
        <article class="card">
          <div class="card-top">
            <div>
              <div class="symbol">${escapeHtml(quote.symbol)}</div>
              <div class="name">${escapeHtml(quote.name)}</div>
            </div>
            <div class="market-state">${escapeHtml(quote.market_state || "N/A")}</div>
          </div>
          <p class="price">${formatPrice(quote.price, quote.currency)}</p>
          <div class="change-row ${change.className}">${change.text}</div>
          <div class="meta-row">
            <span>昨收 ${formatPrice(quote.previous_close, quote.currency)}</span>
            <span>${formatDate(quote.updated_at)}</span>
          </div>
          ${renderPolymarketMarkets(quote)}
          ${renderStockNews(quote, newsLimit)}
        </article>
      `;
    })
    .join("");
}

async function loadUserState() {
  if (!isLoggedIn()) {
    currentUser = null;
    renderNav();
    return;
  }

  try {
    const me = await apiFetch("/api/auth/me");
    currentUser = me.user;
    renderNav();

    const prefs = await apiFetch("/api/preferences");
    availableSymbols = prefs.available_symbols || [];
    selectedSymbols = new Set(prefs.preferences.favorite_symbols || []);
    newsLimitInput.value = String(prefs.preferences.news_per_symbol || 4);
    newsLimitValue.textContent = newsLimitInput.value;
    renderSymbolPicker();
  } catch (error) {
    clearToken();
    currentUser = null;
    renderNav();
  }
}

async function loadDashboard() {
  try {
    const quotesRes = await fetch("/api/quotes", { headers: authHeaders() });
    if (!quotesRes.ok) {
      throw new Error("API request failed");
    }

    const quotesData = await quotesRes.json();
    renderQuotes(quotesData.quotes || [], quotesData.news_per_symbol || 4);

    statusPill.textContent = quotesData.is_authenticated ? "已登录 · 数据已更新" : "访客模式 · 数据已更新";
    statusPill.className = "status-pill ok";
    lastUpdated.textContent = `最后刷新：${new Date().toLocaleString("zh-CN", { hour12: false })}`;
  } catch (error) {
    statusPill.textContent = "更新失败";
    statusPill.className = "status-pill error";
    console.error(error);
  }
}

async function savePreferences() {
  if (!currentUser) return;

  showMessage(preferencesMessage, "");
  if (selectedSymbols.size < 1) {
    showMessage(preferencesMessage, "请至少选择 1 只股票", "error");
    return;
  }
  if (selectedSymbols.size > 6) {
    showMessage(preferencesMessage, "最多选择 6 只股票", "error");
    return;
  }

  try {
    await apiFetch("/api/preferences", {
      method: "PUT",
      body: JSON.stringify({
        favorite_symbols: Array.from(selectedSymbols),
        news_per_symbol: Number(newsLimitInput.value),
      }),
    });
    showMessage(preferencesMessage, "偏好已保存，正在刷新数据...", "success");
    await loadDashboard();
  } catch (error) {
    showMessage(preferencesMessage, error.message, "error");
  }
}

newsLimitInput.addEventListener("input", () => {
  newsLimitValue.textContent = newsLimitInput.value;
});

savePreferencesBtn.addEventListener("click", savePreferences);

(async function init() {
  await loadUserState();
  await loadDashboard();
  setInterval(loadDashboard, REFRESH_MS);
})();
