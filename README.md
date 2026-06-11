# Stock Tracker

追踪 **GOOGL**、**NVDA**、**AVGO** 三支美股的实时报价、Polymarket 赔率与 Yahoo Finance 新闻。

在线演示：http://49.51.195.205/

## 功能

- 用户注册 / 登录（邮箱个人注册）
- 微信 / 支付宝登录（需配置开放平台密钥）
- 微信 / 支付宝会员订阅支付（需配置商户号；默认演示模式）
- PostgreSQL 用户与订单数据库
- 实时股价、Polymarket 赔率、每股票 4 条 Yahoo 新闻

## 页面

| 路径 | 说明 |
|------|------|
| `/` | 主面板（需登录） |
| `/login.html` | 登录 |
| `/register.html` | 个人注册 |
| `/pricing.html` | 会员订阅（微信/支付宝） |

## 本地运行

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，配置 DATABASE_URL 和 SECRET_KEY

# 需要先安装并启动 PostgreSQL
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## PostgreSQL 初始化

```bash
sudo -u postgres psql -f deploy/postgresql-init.sql
```

或使用：

```bash
bash deploy/setup-postgresql.sh
```

## 环境变量

见 `.env.example`。关键配置：

- `DATABASE_URL`：PostgreSQL 连接
- `SECRET_KEY`：JWT 签名密钥
- `PAYMENT_DEMO_MODE=true`：演示支付（无需真实商户号）
- `WECHAT_*` / `ALIPAY_*`：正式接入微信/支付宝时填写

## API

### 认证
- `POST /api/auth/register` 邮箱注册
- `POST /api/auth/login` 邮箱登录
- `GET /api/auth/me` 当前用户
- `GET /api/auth/wechat/login` 微信 OAuth
- `GET /api/auth/alipay/login` 支付宝 OAuth

### 支付
- `GET /api/payments/plans` 订阅方案
- `POST /api/payments/create` 创建订单
- `POST /api/payments/demo/complete/{order_no}` 演示模式完成支付

### 数据（需 Bearer Token）
- `GET /api/quotes`
- `GET /api/news`
- `GET /api/health`

## 服务器部署

```bash
bash deploy/setup-postgresql.sh
sudo mkdir -p /opt/stock-tracker
# 上传代码后：
python3 -m venv /opt/stock-tracker/.venv
/opt/stock-tracker/.venv/bin/pip install -r /opt/stock-tracker/requirements.txt
cp /opt/stock-tracker/.env.example /opt/stock-tracker/.env
# 编辑 /opt/stock-tracker/.env
sudo cp /opt/stock-tracker/deploy/stock-tracker.service /etc/systemd/system/
sudo cp /opt/stock-tracker/deploy/nginx-stock-tracker.conf /etc/nginx/conf.d/stock-tracker.conf
sudo systemctl daemon-reload
sudo systemctl enable --now postgresql stock-tracker nginx
```

## 正式接入微信 / 支付宝

1. **微信登录**：在微信开放平台创建网站应用，配置回调 `https://你的域名/api/auth/wechat/callback`
2. **支付宝登录**：在支付宝开放平台创建应用，配置回调 `https://你的域名/api/auth/alipay/callback`
3. **微信支付 / 支付宝支付**：开通商户号，填写 `.env` 中对应密钥，并设置 `PAYMENT_DEMO_MODE=false`

## 数据来源

- 股价：Yahoo Finance / Finnhub（可选）
- 新闻：Yahoo Finance RSS
- 赔率：Polymarket Gamma API
