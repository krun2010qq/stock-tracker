const REFRESH_MS = 30000;
const NEWS_PER_STOCK = 4;

const quoteCards = document.getElementById("quote-cards");
const statusPill = document.getElementById("status-pill");
const lastUpdated = document.getElementById("last-updated");

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

function renderStockNews(quote) {
  const news = (quote.news || []).slice(0, NEWS_PER_STOCK);

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

function renderQuotes(quotes) {
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
          ${renderStockNews(quote)}
        </article>
      `;
    })
    .join("");
}

async function loadDashboard() {
  try {
    const quotesRes = await fetch("/api/quotes");

    if (!quotesRes.ok) {
      throw new Error("API request failed");
    }

    const quotesData = await quotesRes.json();
    renderQuotes(quotesData.quotes || []);

    statusPill.textContent = "数据已更新";
    statusPill.className = "status-pill ok";
    lastUpdated.textContent = `最后刷新：${new Date().toLocaleString("zh-CN", { hour12: false })}`;
  } catch (error) {
    statusPill.textContent = "更新失败";
    statusPill.className = "status-pill error";
    console.error(error);
  }
}

loadDashboard();
setInterval(loadDashboard, REFRESH_MS);
