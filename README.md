# Stock Tracker

追踪 **GOOGL**、**NVDA**、**AVGO** 三支美股的实时报价与相关新闻。

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
sudo cp deploy/nginx-stock-tracker.conf /etc/nginx/sites-available/stock-tracker
sudo ln -sf /etc/nginx/sites-available/stock-tracker /etc/nginx/sites-enabled/stock-tracker
sudo systemctl daemon-reload
sudo systemctl enable --now stock-tracker
sudo nginx -t && sudo systemctl reload nginx
```

## 数据来源

- 股价与新闻来自 [Yahoo Finance](https://finance.yahoo.com/) 公开接口
- 免费数据源存在延迟，不等同于交易所毫秒级行情
