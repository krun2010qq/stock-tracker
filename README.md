# Stock Tracker

追踪美股的实时报价、Polymarket 赔率与 Yahoo Finance 新闻。

在线演示：http://49.51.195.205/

## 功能

- 访客无需注册即可浏览默认行情（GOOGL / NVDA / AVGO）
- 邮箱注册 / 登录
- 登录用户可自选关注的股票（最多 6 只）和每只股票的新闻条数（2–8 条）
- PostgreSQL 用户与偏好设置

## 页面

| 路径 | 说明 |
|------|------|
| `/` | 主面板（访客可访问，登录后可自定义偏好） |
| `/login.html` | 登录 |
| `/register.html` | 个人注册 |

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

## API

### 认证
- `POST /api/auth/register` 邮箱注册
- `POST /api/auth/login` 邮箱登录
- `GET /api/auth/me` 当前用户（需 Bearer Token）

### 偏好（需 Bearer Token）
- `GET /api/preferences` 获取用户偏好
- `PUT /api/preferences` 保存用户偏好

### 数据（访客可访问，登录用户返回个性化内容）
- `GET /api/symbols` 可选股票列表
- `GET /api/quotes` 股价 + Polymarket + 新闻
- `GET /api/news` 新闻
- `GET /api/polymarket` Polymarket 赔率
- `GET /api/health` 健康检查

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

快速更新已部署服务器：

```bash
python remote_update.py
```

## 数据来源

- 股价：Yahoo Finance / Finnhub（可选）
- 新闻：Yahoo Finance RSS
- 赔率：Polymarket Gamma API
