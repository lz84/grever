# Nexus — AI Agent 团队协作编排框架

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

Nexus 是一个 **AI Agent 团队协作编排框架**——帮助团队管理战略目标分解、智能体任务分配、人机协作审批和持续进化。

> 一句话：**Dify 帮一个人搭 AI 应用，Nexus 帮一个团队管 AI。**

## 核心能力

| 域 | 功能 |
|---|------|
| 🧠 GrASP 认知域 | 知识注入、认知评估、GraphRAG 检索 |
| 🎯 Reins 驾驭域 | 目标→工程→任务分解、Agent 调度、HITL |
| 🧬 Evo 进化域 | 蒸馏、突变、权重更新 |
| 🔌 Reach 拓展域 | 场景库、行业包、技能管理 |
| 🛡️ Vigil 安全域 | 信任管理、争议裁决、安全门禁 |

## 快速开始

### Docker Compose

```bash
docker-compose up -d
```

- 前端：http://localhost:5173
- API 文档：http://localhost:8097/docs

### 手动部署

**后端：**
```bash
cd packages/server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env
alembic upgrade head
uvicorn api.server:app --host 0.0.0.0 --port 8097 --reload
```

**前端：**
```bash
cd packages/ui
npm install && npm run dev
```

## 项目结构

```
├── packages/
│   ├── server/          # Python 后端 (FastAPI)
│   │   ├── src/
│   │   │   ├── cognitive/   # GrASP 认知域
│   │   │   ├── steering/    # Reins 驾驭域
│   │   │   ├── evolution/   # Evo 进化域
│   │   │   ├── extension/   # Reach 拓展域
│   │   │   ├── security/    # Vigil 安全域
│   │   │   ├── shared/      # 公共服务
│   │   │   ├── models/      # ORM 模型
│   │   │   ├── services/    # 业务服务
│   │   │   └── api/         # API 网关
│   │   ├── alembic/     # 数据库迁移
│   │   └── tests/       # 测试
│   └── ui/              # React 前端
│       └── src/
│           ├── pages/   # 功能页面
│           └── shared/  # 共享组件
├── docs/                # 文档
│   ├── architecture/    # 架构设计
│   ├── guides/          # 使用指南
│   └── contributing/    # 贡献指南
├── config/              # 配置
├── docker-compose.yml
└── LICENSE              # AGPL v3
```

## 许可证

本项目采用 **GNU Affero General Public License v3.0**。

- ✅ 可以自由使用、修改、分发
- ✅ 可以内部部署用于自己的业务
- ⚠️ 如果修改代码后作为**网络服务**提供，必须开源你的修改

详见 [LICENSE](LICENSE)。

## 贡献

欢迎提交 Issue 和 Pull Request。详见 [贡献指南](docs/contributing/guide.md)。
