# Stock Tracker

追踪 **GOOGL**、**NVDA**、**AVGO** 三支美股的实时报价与相关新闻。

在线演示：http://49.51.195.205/

## 功能

- 实时股价（约 30 秒自动刷新）
- 涨跌幅与昨收价
- 三支股票相关新闻聚合展示

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器访问：`http://localhost:8000`

## API

- `GET /api/quotes` 股价数据
- `GET /api/news` 新闻数据
- `GET /api/health` 健康检查

## 部署

服务器上使用 systemd + nginx：

```bash
sudo mkdir -p /opt/stock-tracker
sudo python3 -m venv /opt/stock-tracker/.venv
sudo /opt/stock-tracker/.venv/bin/pip install -r /opt/stock-tracker/requirements.txt
sudo cp deploy/stock-tracker.service /etc/systemd/system/
sudo cp deploy/nginx-stock-tracker.conf /etc/nginx/conf.d/stock-tracker.conf
sudo systemctl daemon-reload
sudo systemctl enable --now stock-tracker nginx
```

可选：配置 Finnhub API Key 以获得更稳定的实时报价：

```bash
echo 'FINNHUB_API_KEY=你的key' | sudo tee /opt/stock-tracker/.env
sudo systemctl restart stock-tracker
```

## 数据来源

- 股价：Yahoo Finance / Finnhub（可选）
- 新闻：Google News RSS / Finnhub（可选）
- 免费数据源存在延迟，不等同于交易所毫秒级行情
