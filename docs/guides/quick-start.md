# 快速开始

## 环境要求

| 组件 | 版本 |
|------|------|
| Python | 3.12+ |
| Node.js | 18+ |
| SQLite | 内置（开发默认） |
| PostgreSQL | 可选（生产推荐） |

## 方式一：Docker Compose（推荐）

```bash
git clone https://github.com/lz84/agents_nexus.git
cd agents_nexus

# 复制配置
cp config/.env.example config/.env

# 一键启动
docker-compose up -d
```

启动后访问：
- **前端**: http://localhost:5173
- **API 文档**: http://localhost:8097/docs
- **ReDoc**: http://localhost:8097/redoc

## 方式二：手动部署

### 1. 后端

```bash
cd packages/server

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp config/.env.example config/.env
# 编辑 .env 修改数据库路径等

# 执行数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn api.server:app --host 0.0.0.0 --port 8097 --reload
```

### 2. 前端

```bash
cd packages/ui

# 安装依赖
npm install

# 启动开发服务器（自动代理到后端 8097 端口）
npm run dev
```

### 3. 验证

```bash
# 检查后端健康
curl http://localhost:8097/api/v1/health
# → {"status": "healthy", "service": "reins"}
```

## 首次使用

1. 访问 http://localhost:5173 打开前端
2. 系统已就绪，进入系统管理页面配置 Agent 平台连接
3. 创建第一个 Goal，系统会自动分解为 Projects 和 Tasks
4. Task 会自动匹配最佳 Agent 执行

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|------|
| `DATABASE_URL` | 数据库连接字符串 | `sqlite:///data/reins.db` |
| `REINS_HOST` | 后端监听地址 | `0.0.0.0` |
| `REINS_PORT` | 后端端口 | `8097` |
| `REINS_DEBUG` | 调试模式 | `false` |
| `JWT_SECRET` | JWT 密钥 | `your-secret-change-me` |
| `JWT_EXPIRE_HOURS` | JWT 过期时间（小时） | `24` |

## 常见问题

### 数据库迁移失败

```bash
# 重置迁移状态
alembic stamp head
alembic upgrade head
```

### 前端端口被占用

Vite 会自动切换到下一个可用端口（5174, 5175...），或者手动指定：

```bash
npm run dev -- --port 3000
```

### Windows 路径问题

Windows 上数据库路径需要用 `sqlite+aiosqlite:///` 前缀：

```ini
DATABASE_URL=sqlite+aiosqlite:///data/reins.db
```

### 后端连接数据库失败

检查 `config/.env` 中的 `DATABASE_URL` 配置是否正确。
