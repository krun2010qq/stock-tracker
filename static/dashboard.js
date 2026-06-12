const REFRESH_MS = 30000;
const MAX_FAVORITES = 12;

const quoteCards = document.getElementById("quote-cards");
const statusPill = document.getElementById("status-pill");
const lastUpdated = document.getElementById("last-updated");
const userLabel = document.getElementById("user-label");
const navActions = document.getElementById("nav-actions");
const heroSubtitle = document.getElementById("hero-subtitle");
const preferencesPanel = document.getElementById("preferences-panel");
const marketTabs = document.getElementById("market-tabs");
const symbolSearchInput = document.getElementById("symbol-search-input");
const symbolSearchBtn = document.getElementById("symbol-search-btn");
const searchResults = document.getElementById("search-results");
const selectedSymbolsEl = document.getElementById("selected-symbols");
const selectedCountEl = document.getElementById("selected-count");
const newsLimitInput = document.getElementById("news-limit");
const newsLimitValue = document.getElementById("news-limit-value");
const savePreferencesBtn = document.getElementById("save-preferences-btn");
const preferencesMessage = document.getElementById("preferences-message");

let currentUser = null;
let selectedSymbols = new Map();
let catalog = { featured: [], markets: [], max_favorites: MAX_FAVORITES };
let activeMarket = "all";
let searchTimer = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatPrice(value, currency = "USD") {
  if (value == null) return "--";
  const locale = currency === "CNY" ? "zh-CN" : "en-US";
  return new Intl.NumberFormat(locale, {
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
    heroSubtitle.textContent = "你已登录，可搜索纳斯达克或 A 股并添加到你关注的股票列表。";
    return;
  }

  userLabel.textContent = "访客模式";
  navActions.innerHTML = `
    <a class="nav-btn" href="/login.html">登录</a>
    <a class="nav-btn" href="/register.html">注册</a>
  `;
  preferencesPanel.classList.add("hidden");
  heroSubtitle.textContent = "无需注册即可浏览默认行情。注册登录后可搜索纳斯达克与 A 股并添加到关注列表。";
}

function renderMarketTabs() {
  const markets = catalog.markets?.length
    ? catalog.markets
    : [
        { key: "all", label: "全部" },
        { key: "nasdaq", label: "纳斯达克" },
        { key: "ashare", label: "A股" },
      ];

  marketTabs.innerHTML = markets
    .map(
      (market) => `
        <button
          type="button"
          class="market-tab ${market.key === activeMarket ? "active" : ""}"
          data-market="${escapeHtml(market.key)}"
        >
          ${escapeHtml(market.label)}
        </button>
      `
    )
    .join("");

  marketTabs.querySelectorAll(".market-tab").forEach((button) => {
    button.addEventListener("click", () => {
      activeMarket = button.dataset.market;
      renderMarketTabs();
      const query = symbolSearchInput.value.trim();
      if (query) runSymbolSearch(query);
    });
  });
}

function renderSelectedSymbols() {
  const maxFavorites = catalog.max_favorites || MAX_FAVORITES;
  selectedCountEl.textContent = `${selectedSymbols.size} / ${maxFavorites}`;

  if (!selectedSymbols.size) {
    selectedSymbolsEl.innerHTML = `<p class="selected-empty">还没有添加股票，请先搜索并添加。</p>`;
    return;
  }

  selectedSymbolsEl.innerHTML = Array.from(selectedSymbols.entries())
    .map(
      ([symbol, meta]) => `
        <div class="selected-chip">
          <div>
            <strong>${escapeHtml(symbol)}</strong>
            <small>${escapeHtml(meta.name || symbol)} · ${escapeHtml(meta.market || "")}</small>
          </div>
          <button type="button" data-remove="${escapeHtml(symbol)}" aria-label="移除">×</button>
        </div>
      `
    )
    .join("");

  selectedSymbolsEl.querySelectorAll("button[data-remove]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedSymbols.delete(button.dataset.remove);
      renderSelectedSymbols();
    });
  });
}

function addSymbol(item) {
  const maxFavorites = catalog.max_favorites || MAX_FAVORITES;
  if (selectedSymbols.size >= maxFavorites) {
    showMessage(preferencesMessage, `最多添加 ${maxFavorites} 只股票`, "error");
    return;
  }
  selectedSymbols.set(item.symbol, item);
  renderSelectedSymbols();
  searchResults.classList.add("hidden");
  showMessage(preferencesMessage, `已添加 ${item.symbol}`, "success");
}

function renderSearchResults(results) {
  if (!results.length) {
    searchResults.innerHTML = `<p class="search-empty">未找到匹配股票，请换关键词试试。</p>`;
    searchResults.classList.remove("hidden");
    return;
  }

  searchResults.innerHTML = results
    .map(
      (item) => `
        <button type="button" class="search-result-item" data-symbol="${escapeHtml(item.symbol)}">
          <div>
            <strong>${escapeHtml(item.symbol)}</strong>
            <span>${escapeHtml(item.name)}</span>
          </div>
          <small>${escapeHtml(item.market || "")}${item.exchange ? ` · ${escapeHtml(item.exchange)}` : ""}</small>
        </button>
      `
    )
    .join("");

  searchResults.querySelectorAll(".search-result-item").forEach((button) => {
    button.addEventListener("click", () => {
      const symbol = button.dataset.symbol;
      const item = results.find((entry) => entry.symbol === symbol);
      if (item) addSymbol(item);
    });
  });

  searchResults.classList.remove("hidden");
}

async function runSymbolSearch(query) {
  const trimmed = query.trim();
  if (!trimmed) {
    searchResults.classList.add("hidden");
    return;
  }

  try {
    const data = await apiFetch(
      `/api/symbols/search?q=${encodeURIComponent(trimmed)}&market=${encodeURIComponent(activeMarket)}&limit=20`
    );
    renderSearchResults(data.results || []);
  } catch (error) {
    showMessage(preferencesMessage, error.message, "error");
  }
}

function seedSelectedSymbols(symbols) {
  selectedSymbols = new Map();
  for (const symbol of symbols) {
    const featured = (catalog.featured || []).find((item) => item.symbol === symbol);
    selectedSymbols.set(symbol, featured || { symbol, name: symbol, market: "" });
  }
  renderSelectedSymbols();
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
  quoteCards.style.gridTemplateColumns = "repeat(auto-fit, minmax(280px, 1fr))";

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

async function loadCatalog() {
  try {
    catalog = await apiFetch("/api/symbols");
  } catch (error) {
    catalog = { featured: [], markets: [], max_favorites: MAX_FAVORITES };
  }
  renderMarketTabs();
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
    if (prefs.available_symbols) {
      catalog = { ...catalog, ...prefs.available_symbols };
      renderMarketTabs();
    }

    seedSelectedSymbols(prefs.preferences.favorite_symbols || []);
    newsLimitInput.value = String(prefs.preferences.news_per_symbol || 4);
    newsLimitValue.textContent = newsLimitInput.value;
  } catch (error) {
    clearToken();
    currentUser = null;
    renderNav();
    if (error.message.includes("禁用") || error.message.includes("未登录") || error.message.includes("过期")) {
      statusPill.textContent = "登录状态已失效，请重新登录";
      statusPill.className = "status-pill error";
    }
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
  const maxFavorites = catalog.max_favorites || MAX_FAVORITES;

  if (selectedSymbols.size < 1) {
    showMessage(preferencesMessage, "请至少添加 1 只股票", "error");
    return;
  }
  if (selectedSymbols.size > maxFavorites) {
    showMessage(preferencesMessage, `最多添加 ${maxFavorites} 只股票`, "error");
    return;
  }

  try {
    await apiFetch("/api/preferences", {
      method: "PUT",
      body: JSON.stringify({
        favorite_symbols: Array.from(selectedSymbols.keys()),
        news_per_symbol: Number(newsLimitInput.value),
      }),
    });
    showMessage(preferencesMessage, "偏好已保存，正在刷新数据...", "success");
    await loadDashboard();
  } catch (error) {
    showMessage(preferencesMessage, error.message, "error");
  }
}

symbolSearchBtn.addEventListener("click", () => runSymbolSearch(symbolSearchInput.value));
symbolSearchInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    runSymbolSearch(symbolSearchInput.value);
  }
});
symbolSearchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => runSymbolSearch(symbolSearchInput.value), 350);
});

newsLimitInput.addEventListener("input", () => {
  newsLimitValue.textContent = newsLimitInput.value;
});

savePreferencesBtn.addEventListener("click", savePreferences);

(async function init() {
  await loadCatalog();
  await loadUserState();
  await loadDashboard();
  setInterval(loadDashboard, REFRESH_MS);
})();
