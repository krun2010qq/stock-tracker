const REFRESH_MS = 30000;

const quoteCards = document.getElementById("quote-cards");
const newsGrid = document.getElementById("news-grid");
const statusPill = document.getElementById("status-pill");
const lastUpdated = document.getElementById("last-updated");

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

function renderQuotes(quotes) {
  quoteCards.innerHTML = quotes
    .map((quote) => {
      const change = formatChange(quote.change, quote.change_percent);
      return `
        <article class="card">
          <div class="card-top">
            <div>
              <div class="symbol">${quote.symbol}</div>
              <div class="name">${quote.name}</div>
            </div>
            <div class="market-state">${quote.market_state || "N/A"}</div>
          </div>
          <p class="price">${formatPrice(quote.price, quote.currency)}</p>
          <div class="change-row ${change.className}">${change.text}</div>
          <div class="meta-row">
            <span>昨收 ${formatPrice(quote.previous_close, quote.currency)}</span>
            <span>${formatDate(quote.updated_at)}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderNews(news) {
  if (!news.length) {
    newsGrid.innerHTML = `<div class="empty-state">暂时没有抓到新闻，请稍后再试。</div>`;
    return;
  }

  newsGrid.innerHTML = news
    .map(
      (item) => `
        <article class="news-card">
          <span class="news-tag">${item.symbol}</span>
          <a href="${item.url || "#"}" target="_blank" rel="noopener noreferrer">
            <h3 class="news-title">${item.title}</h3>
          </a>
          <p class="news-summary">${item.summary || "暂无摘要"}</p>
          <div class="news-meta">
            <span>${item.publisher || "Unknown"}</span>
            <span>${formatDate(item.published_at)}</span>
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
      fetch("/api/news"),
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
