# 快速开始

## 环境要求

- Python 3.12+
- Node.js 18+
- SQLite（默认）或 PostgreSQL

## Docker Compose（推荐）

```bash
docker-compose up -d
```

访问：
- 前端：http://localhost:5173
- API 文档：http://localhost:8097/docs

## 手动部署

### 后端

```bash
cd packages/server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env
alembic upgrade head
uvicorn api.server:app --host 0.0.0.0 --port 8097 --reload
```

### 前端

```bash
cd packages/ui
npm install
npm run dev
```

## 验证

```bash
curl http://localhost:8097/api/v1/health
# → {"status": "healthy", "service": "reins"}
```
