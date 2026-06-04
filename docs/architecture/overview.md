# 架构概览

Nexus 是一个 AI Agent 团队协作编排框架，采用**五域分离**的微服务架构。

## 五大领域

| 域 | 职责 | 目录 |
|----|------|------|
| 🧠 认知域 (GrASP) | 知识注入、认知评估、GraphRAG 检索 | `cognitive/` |
| 🎯 驾驭域 (Reins) | 目标分解、Agent 调度、HITL 人机协作 | `steering/` |
| 🧬 进化域 (Evo) | 蒸馏、突变、权重更新 | `evolution/` |
| 🔌 拓展域 (Reach) | 场景库、行业包、技能管理 | `extension/` |
| 🛡️ 安全域 (Vigil) | 信任管理、争议裁决 | `security/` |

## 数据模型

```
Goal (1) → Project (N) → Task (N) → Agent (M:N) → Execution → Verification
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite + shadcn/ui |
| 后端 | Python 3.12+ + FastAPI + SQLAlchemy |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| 部署 | Docker Compose |
