const REFRESH_MS = 30000;
const NEWS_LIMIT = 10;

const quoteCards = document.getElementById("quote-cards");
const newsGrid = document.getElementById("news-grid");
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

function renderEngagement(item) {
  const parts = [];
  if (item.score != null) parts.push(`${item.score} upvotes`);
  if (item.comments != null) parts.push(`${item.comments} 评论`);
  return parts.length ? ` · ${parts.join(" · ")}` : "";
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
        </article>
      `;
    })
    .join("");
}

function renderNews(news) {
  const latestNews = news.slice(0, NEWS_LIMIT);

  if (!latestNews.length) {
    newsGrid.innerHTML = `<div class="empty-state">暂时没有抓到 Reddit 帖子，请稍后再试。</div>`;
    return;
  }

  newsGrid.innerHTML = latestNews
    .map(
      (item) => `
        <article class="news-card">
          <span class="news-tag">${escapeHtml(item.symbol)}</span>
          <a href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener noreferrer">
            <h3 class="news-title">${escapeHtml(item.title)}</h3>
          </a>
          <p class="news-summary">${escapeHtml(item.summary || "Reddit 讨论帖")}</p>
          <div class="news-meta">
            <span>${escapeHtml(item.publisher || "Reddit")}</span>
            <span>${formatDate(item.published_at)}${renderEngagement(item)}</span>
          </div>
        </article>
      `
    )
    .join("");
}

async function loadDashboard() {
  try {
    const [quotesRes, newsRes] = await Promise.all([
      fetch("/api/quotes"),
      fetch(`/api/news?limit=${NEWS_LIMIT}`),
    ]);

    if (!quotesRes.ok || !newsRes.ok) {
      throw new Error("API request failed");
    }

    const quotesData = await quotesRes.json();
    const newsData = await newsRes.json();

    renderQuotes(quotesData.quotes || []);
    renderNews(newsData.news || []);

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
