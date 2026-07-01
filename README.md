# Grever — AI Agent 团队协作框架

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![React 18+](https://img.shields.io/badge/React-18+-blue.svg)](https://react.dev/)

Grever 是一个**面向 AI Agent 团队的协作编排框架**。它帮助团队管理战略目标分解、智能体任务分配、人机协作审批和持续进化。

**适合谁：**
- 🏢 企业：用 AI Agent 替代重复性人工流程
- 🛠️ 开发者：构建自定义 AI Agent 工作流
- 🔬 研究者：探索多智能体协作范式

## 核心能力

| 域 | 功能 | 说明 |
|----|------|------|
| 🧠 认知域 (GrASP) | 知识注入、认知评估、GraphRAG 检索 | 从文档/结果中提取认知，注入到任务上下文 |
| 🎯 驾驭域 (Reins) | 目标→工程→任务分解、Agent 调度、HITL 人机协作 | 战略目标拆解为可执行任务，自动分配 Agent |
| 🧬 进化域 (Evo) | 蒸馏、突变、权重更新 | 从历史任务中蒸馏知识胶囊，持续优化 Agent 能力 |
| 🔌 拓展域 (Reach) | 场景库、行业包、技能管理 | 预定义场景一键实例化为完整目标树 |
| 🛡️ 安全域 (Vigil) | 信任管理、争议裁决、安全门禁 | 人机协作审批流，异常检测和降级 |

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

## 快速开始

### 前置要求

- Python 3.12+
- Node.js 18+
- SQLite（内置）或 PostgreSQL

### 后端

```bash
cd packages/server

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
alembic upgrade head

# 启动
uvicorn api.server:app --host 0.0.0.0 --port 8096 --reload
```

### 前端

```bash
cd packages/ui

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 一键启动

```bash
docker-compose up -d
```

### 访问

- 前端：http://localhost
- 后端 API：http://localhost/api/v1/
- API 文档：http://localhost/api/v1/docs

## 项目结构

```
├── packages/
│   ├── server/          # Python 后端 (FastAPI)
│   │   ├── src/
│   │   │   ├── grasp/   # 认知域 - 知识注入与检索
│   │   │   ├── reins/   # 驾驭域 - 调度与人机协作
│   │   │   ├── evolution/ # 进化域 - 蒸馏与突变
│   │   │   ├── reach/   # 拓展域 - 场景与行业包
│   │   │   ├── vigil/   # 安全域 - 信任与争议
│   │   │   ├── shared/  # 公共服务
│   │   │   └── api/     # API 网关
│   │   └── tests/       # 测试套件 (296 E2E tests)
│   └── ui/              # React 前端
│       └── src/
│           ├── pages/   # 功能页面
│           └── shared/  # 共享组件
├── docs/                # 公开文档
│   ├── architecture/    # 架构设计
│   └── guides/          # 使用指南
├── docker-compose.yml
└── LICENSE              # AGPL v3
```

## API

完整的 API 文档由 OpenAPI 自动生成，启动后访问 `/docs`（Swagger UI）或 `/redoc`。

## 许可证

本项目采用 **GNU Affero General Public License v3.0** (AGPL-3.0)。

简单来说：
- ✅ 可以自由使用、修改、分发
- ✅ 可以内部部署用于自己的业务
- ⚠️ 如果修改代码后作为**网络服务**提供给他人，必须开源你的修改
- 🔒 防止他人拿你的改进闭源商用

详见 [LICENSE](LICENSE)。

## 贡献

欢迎提交 Issue 和 Pull Request。

## 致谢

Grever 受到以下项目的启发：
- [Dify](https://dify.ai) — AI 应用搭建平台
- [LangGraph](https://github.com/langchain-ai/langgraph) — Agent 工作流编排
- [CrewAI](https://github.com/crewAIInc/crewAI) — 多 Agent 协作
