# Grever — AI Agent 任务管理与编排平台

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![React 18+](https://img.shields.io/badge/React-18+-blue.svg)](https://react.dev/)

Grever 是一个 **AI Agent 任务管理与编排平台**。它将战略目标拆解为可执行的 Agent 任务，实现自动分发、人机协作审批和持续进化。

> **Dify 帮一个人搭 AI 应用，Grever 帮一个团队管 AI。**

## 快速开始

3 步即可启动：

### 1. Docker 部署

```bash
docker-compose up -d
```

### 2. 初始化

```bash
docker-compose exec server python scripts/init_grever.py --seed
```

### 3. 访问

浏览器打开 [http://localhost:5173](http://localhost:5173)

> 后端端口 8096，前端端口 5173。完整 API 文档启动后访问 `/api/v1/docs`。

## Grever 是什么

### 核心模型

```
Goal (战略目标)
 └─ Project (战略项目)
     └─ Task (战术任务)
         └─ Agent (执行者)
```

Grever 用 **Goal → Project → Task → Agent** 四层模型，将抽象的业务目标转化为具体的 Agent 行动。每个层级都有清晰的状态流转和责任人分配。

### 适用场景

- 🏢 技术团队管理多个 AI Agent 的日常工作流
- 📋 复杂业务需求的自动化拆解与追踪
- 🤝 人机协作审批流（Agent 执行，人类裁决）
- 📈 持续进化：从历史任务中提炼经验，优化 Agent 能力

## 功能概览

| 功能 | 说明 |
|------|------|
| 🎯 **Goal 管理** | 战略目标定义、进度追踪、自动分解为 Projects |
| 📋 **Project 管理** | 项目层任务拆分，依赖关系管理 |
| ✅ **Task 调度** | 自动匹配 Agent，支持人工分配与 HITL 审批 |
| 🤖 **Agent 注册** | 多平台适配器（OpenClaw/Dify/Coze/Hermes 等 7 个） |
| 📦 **行业包** | 一键导入行业模板（场景+任务+Agent 方案） |
| 🔄 **进化系统** | 从历史任务蒸馏知识胶囊，持续优化 Agent |
| 🧠 **认知引擎** | GraphRAG 知识注入，上下文自动构建 |

## 架构

```
┌─────────────────────────────────────────────────────┐
│              Web Frontend (React + TypeScript)        │
│  Dashboard │ Goals │ Projects │ Tasks │ Agents      │
├─────────────────────────────────────────────────────┤
│              FastAPI Backend (Python)                │
│  ┌────────┬────────┬───────┬────────┬──────────┐    │
│  │ GrASP  │ Reins  │  Evo  │ Reach  │  Vigil   │    │
│  │ 认知   │ 调度   │ 进化  │ 拓展   │  安全    │    │
│  └────────┴────────┴───────┴────────┴──────────┘    │
├─────────────────────────────────────────────────────┤
│              GreverScheduler (后台调度)               │
│  任务派发 → Agent 匹配 → 执行追踪 → 结果验证          │
├─────────────────────────────────────────────────────┤
│              SQLite / PostgreSQL                     │
└─────────────────────────────────────────────────────┘
```

## 开发指南

### 源码部署

**后端**：

```bash
cd packages/server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn api.server:app --host 0.0.0.0 --port 8096 --reload
```

**前端**：

```bash
cd packages/ui
npm install
npm run dev
```

**初始化**：

```bash
python scripts/init_grever.py --seed   # 灌入演示数据
python scripts/init_grever.py --reset  # 清空演示数据
python scripts/init_grever.py --fix    # 修复数据质量
```

### 添加 Agent 适配器

1. 在 `src/agent_service/adapters/` 下创建新适配器
2. 继承 `BaseAdapter`，实现 `execute()` / `check_status()` / `get_result()`
3. 在 `adapters/facade.py` 中注册新适配器
4. 测试通过后，Agent 即可被调度器识别和分配

### 贡献指南

欢迎提交 Issue 和 Pull Request。

- **Bug 报告**：请包含复现步骤、预期行为、实际行为
- **功能请求**：请说明使用场景和期望效果
- **代码贡献**：请确保通过现有测试，新功能请附带测试

项目使用 AGPL-3.0 许可证，贡献代码即表示你同意在此许可证下分发。

## 许可证

[GNU Affero General Public License v3.0](LICENSE)

简单来说：可以自由使用和修改，但如果将修改后的代码作为网络服务提供，必须开源你的修改。
