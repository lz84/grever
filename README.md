# Nexus — AI Agent 团队协作编排框架

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![React 18+](https://img.shields.io/badge/React-18+-blue.svg)](https://react.dev/)

Nexus 是一个 **AI Agent 团队协作编排框架**——将战略目标拆解为可执行任务，自动分配 AI Agent，人机协作审批，持续进化优化。

> Dify 帮一个人搭 AI 应用，Nexus 帮一个团队管 AI。

## 核心能力

Nexus 将 AI Agent 协作分为五个领域（五域架构）：

| 域 | 英文名 | 职责 |
|---|------|------|
| 🧠 认知域 | **GrASP** | 知识注入、认知评估、GraphRAG 检索，从文档和任务结果中提取认知 |
| 🎯 驾驭域 | **Reins** | 目标→工程→任务分解、Agent 调度、人机协作 (HITL)、任务执行追踪 |
| 🧬 进化域 | **Evo** | 从历史任务中蒸馏知识胶囊，持续优化 Agent 能力权重 |
| 🔌 拓展域 | **Reach** | 场景库、行业包、技能管理，预定义场景一键实例化为完整目标树 |
| 🛡️ 安全域 | **Vigil** | 信任管理、争议裁决、安全门禁，异常检测和降级策略 |

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Frontend (React)                    │
│  Dashboard │ Goals │ Projects │ Tasks │ Agents │ Scenarios  │
├─────────────────────────────────────────────────────────────┤
│                     FastAPI Backend                          │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │  GrASP   │  Reins   │   Evo    │  Reach   │  Vigil   │   │
│  │ 认知引擎 │ 调度引擎 │ 进化引擎 │ 拓展引擎 │ 安全引擎 │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
├─────────────────────────────────────────────────────────────┤
│                     SQLite / PostgreSQL                       │
└─────────────────────────────────────────────────────────────┘
```

**数据模型：**

```
Goal (1) ──→ Project (N) ──→ Task (N) ──→ Agent (M:N)
  │              │              │
  │ 战略目标      │ 工程项目      │ 执行任务
  │              │              ↓
  │              │        Execution Record
  │              │              ↓
  │              │        Verification Result
  │              │              ↓
  │              │        HITL Review (optional)
```

## 快速开始

### 方式一：Docker Compose

```bash
docker-compose up -d
```

- 前端：http://localhost:5173
- API 文档：http://localhost:8097/docs

### 方式二：手动部署

**后端：**

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

# 数据库迁移
alembic upgrade head

# 启动
uvicorn api.server:app --host 0.0.0.0 --port 8097 --reload
```

**前端：**

```bash
cd packages/ui
npm install
npm run dev
```

**验证：**

```bash
curl http://localhost:8097/api/v1/health
# → {"status": "healthy", "service": "reins"}
```

## 项目结构

```
├── packages/
│   ├── server/              # Python 后端 (FastAPI)
│   │   ├── src/
│   │   │   ├── cognitive/   # GrASP 认知域
│   │   │   ├── steering/    # Reins 驾驭域
│   │   │   ├── evolution/   # Evo 进化域
│   │   │   ├── extension/   # Reach 拓展域
│   │   │   ├── security/    # Vigil 安全域
│   │   │   ├── shared/      # 公共服务（DB、EventBus、Auth）
│   │   │   ├── models/      # ORM 模型
│   │   │   ├── services/    # 业务服务
│   │   │   └── api/         # API 网关
│   │   ├── alembic/         # 数据库迁移
│   │   └── tests/           # 测试套件（296 个 E2E 测试）
│   └── ui/                  # React 前端
│       └── src/
│           ├── pages/       # 功能页面
│           └── shared/      # 共享组件 (shadcn/ui)
├── docs/                    # 文档
│   ├── architecture/        # 架构设计
│   ├── guides/              # 使用指南
│   └── contributing/        # 贡献指南
├── config/                  # 配置
├── docker-compose.yml
└── LICENSE                  # AGPL v3
```

## API

完整的 API 文档由 OpenAPI/Swagger 自动生成：

- **Swagger UI**: http://localhost:8097/docs
- **ReDoc**: http://localhost:8097/redoc
- **OpenAPI JSON**: http://localhost:8097/openapi.json

主要端点：

| 模块 | 前缀 | 说明 |
|------|------|------|
| GrASP | `/api/v1/grasp/` | 认知注入、检索、评估 |
| Reins | `/api/v1/goals/` | 目标管理 |
| Reins | `/api/v1/projects/` | 工程管理 |
| Reins | `/api/v1/tasks/` | 任务管理 |
| Reins | `/api/v1/agents/` | Agent 注册与调度 |
| Evo | `/api/v1/evo/` | 蒸馏与进化 |
| Reach | `/api/v1/scenarios/` | 场景库 |
| Vigil | `/api/v1/vigil/` | 安全与争议 |

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite + shadcn/ui |
| 后端 | Python 3.12+ + FastAPI + SQLAlchemy |
| 数据库 | SQLite（开发默认）/ PostgreSQL（生产推荐） |
| 部署 | Docker Compose |

## 核心概念

### 目标-工程-任务三层模型

Nexus 采用 Goal → Project → Task 三层分解模型：

- **Goal（目标）**：战略意图，定义"要达成什么"
- **Project（工程）**：项目级拆解，定义"怎么做"
- **Task（任务）**：可执行单元，定义"谁来做"

每个 Task 自动匹配最佳 Agent 执行，执行结果经过验证（可选人机协作 HITL），验证结果反馈到 Agent 能力权重。

### Agent 匹配与调度

创建 Task 时，系统根据 Task 的能力标签（capability_tags）自动匹配 Agent：

1. 计算 Agent 与 Task 的能力匹配分数
2. 考虑 Agent 当前负载（load）
3. 选择最优 Agent 派发

### HITL 人机协作

任务执行结果可进入人工审核：

- **争议裁决（disputed）**：验证者标记为争议，人工 approve/reject/request_changes
- **人工审批（approval）**：关键任务需人工 approve/reject
- **人工输入（assist）**：任务请求人工协助

## 许可证

本项目采用 **GNU Affero General Public License v3.0** (AGPL-3.0)。

- ✅ 可以自由使用、修改、分发
- ✅ 可以内部部署用于自己的业务
- ⚠️ 如果修改代码后作为**网络服务**提供给他人，必须开源你的修改
- 🔒 防止他人拿你的改进闭源商用

详见 [LICENSE](LICENSE)。

## 贡献

欢迎提交 Issue 和 Pull Request。详见 [贡献指南](docs/contributing/guide.md)。

## 文档

- [架构概览](docs/architecture/overview.md)
- [快速开始](docs/guides/quick-start.md)
- [贡献指南](docs/contributing/guide.md)
