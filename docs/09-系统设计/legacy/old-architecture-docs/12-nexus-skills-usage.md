# Nexus 技能使用指南（Agent 版）

**版本**: v2.0 (2026-05-07)
**适用对象**: 所有接入 Nexus 平台的 Agent

---

## 1. 快速获取技能

### 方式 A：通过前端技能库下载

1. 访问 Nexus 前端 → 能力库 → Nexus 技能（`/system/skills`）
2. 浏览可用技能列表
3. 点击「下载」按钮 → SKILL.md 自动复制到剪贴板
4. 粘贴到 Agent 工作区的 `skills/{技能名}/SKILL.md`

### 方式 B：通过 API 直接获取

```bash
# 获取所有技能列表
GET http://<nexus_server>/api/v1/skills

# 获取单个技能（含完整 SKILL.md）
GET http://<nexus_server>/api/v1/skills/{skill_id}

# 按类别筛选
GET http://<nexus_server>/api/v1/skills?category=协调

# 关键词搜索
GET http://<nexus_server>/api/v1/skills?q=心跳
```

### 方式 C：直接访问技能文件

```
D:\work\research\agents-nexus\skills\
├── genesis/SKILL.md + skill.py
├── reins/SKILL.md + skill.py
├── grasp/SKILL.md + TypeScript 源码
├── pulse/SKILL.md + skill.py
├── executor/SKILL.md + skill.py
└── verifier/SKILL.md + skill.py
```

---

## 2. 按角色选择技能

| 角色 | 必装 | 按需 |
|------|------|------|
| **协调者**（刚子） | grasp + pulse | genesis + reins + verifier |
| **执行者**（谷子/麻子/扣子） | grasp + pulse | reins + executor |
| **验证者** | grasp + pulse | verifier |

**规律**: 
- grasp（悟）和 pulse（息）是所有角色必装的公共底座
- genesis（生）和 executor（行）互斥 — 分解的不执行，执行的不分解
- reins（缰）和 verifier（鉴）按需安装

---

## 3. 技能速查

### grasp (悟) — 认知系统
- **功能**: 知识图谱检索、认知注册、领域知识注入
- **API**: `GET {grasp_api}/api/v1/grasp/retrieve?q=关键词`
- **何时用**: 需要领域知识、检索验收标准

### genesis (生) — 目标分解
- **功能**: 将目标分解为项目/任务树 + DAG
- **CLI**: `python skill.py decompose "Build a system"`
- **API**: `POST /api/v1/goals/{id}/decompose`
- **何时用**: 创建新目标需要自动分解

### reins (缰) — 实体 CRUD
- **功能**: Goal/Project/Task 增删改查 + 状态机
- **CLI**: `python skill.py goal-list`, `task-complete`, etc.
- **API**: `GET/POST/PUT/DELETE /api/v1/{goals|projects|tasks}`
- **何时用**: 管理目标/项目/任务生命周期

### pulse (息) — Agent 生命周期
- **功能**: 注册、心跳、发现、状态报告
- **CLI**: `python skill.py connect`, `discover`, `status`
- **API**: `POST /api/v1/agents`, `POST /api/v1/agents/{id}/heartbeat`
- **何时用**: Agent 启动注册、心跳保活、发现协作者

### executor (行) — 任务执行
- **功能**: 领取任务、执行、上报结果
- **CLI**: `python skill.py claim`, `complete`, `fail`
- **API**: 通过心跳获取 assigned_tasks，POST /tasks/{id}/complete
- **何时用**: 领取并执行分配的任务

### verifier (鉴) — 统一验证
- **功能**: 编译检查、API 测试、文件校验、LLM 审查
- **CLI**: `python skill.py compile`, `api`, `file`, `llm`
- **输出**: JSON `{passed, type, details}`
- **何时用**: 任务完成后的验收

---

## 4. 快速上手示例

### 执行者接入 Nexus（领取任务 → 执行 → 上报）

```bash
# 1. 设置环境变量
export NEXUS_SERVER_URL=http://localhost:8091
export NEXUS_AGENT_ID=my-agent
export NEXUS_AGENT_NAME="My Agent"
export NEXUS_CAPABILITIES="coding"

# 2. 注册并启动心跳
cd skills/pulse && python skill.py connect

# 3. 领取任务（心跳自动返回 assigned_tasks）
cd ../executor && python skill.py claim

# 4. 执行并上报
python skill.py complete task-xxx --result "任务完成，所有测试通过"
```

### 协调者使用 Nexus（分解目标 → 管理任务）

```bash
# 1. 注册
cd skills/pulse && python skill.py connect

# 2. 分解目标
cd ../genesis && python skill.py decompose "Build disaster response system"

# 3. 查看生成的任务
cd ../reins && python skill.py task-list --status todo

# 4. 设置验证者
python skill.py verifier-set task-xxx kouzi
```

---

## 5. 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `NEXUS_SERVER_URL` | Nexus API 地址 | `http://localhost:8090` |
| `NEXUS_AGENT_ID` | Agent 唯一 ID | 必填 |
| `NEXUS_AGENT_NAME` | Agent 显示名 | 必填 |
| `NEXUS_CAPABILITIES` | 能力标签，逗号分隔 | 必填 |
| `LLM_API` | LLM API URL | 可选 |
| `GRASP_API` | Grasp 认知库 API | 可选 |

---

*文档版本: v2.0 (2026-05-07)*


---


# Nexus Skill 架构决策记录

**日期**: 2026-04-30 00:18 ~ 01:15  
**参与者**: 用户、刚子（协调者）

---

## 背景

用户要求将 reins 技能改造成跨 Agent 通用的标准格式，使其能在 Claude Code、OpenClaw、Codex CLI、Gemini CLI 等不同 Agent 平台上使用。

---

## 调研发现

### SKILL.md 开放标准

- SKILL.md 是 Anthropic 为 Claude Code 创建的开放文件格式
- 已被 15+ AI Agent 采纳（Claude Code、OpenClaw、Codex CLI、Cursor、Gemini CLI、GitHub Copilot Agent Mode、Hermes 等）
- 核心格式：YAML frontmatter（name/description/tags）+ Markdown 指令正文
- 跨 Agent 兼容的原理：所有 Agent 约定用同一格式读写 SKILL.md
- **SKILL.md 是给 LLM 看的说明书，不是给程序跑的代码**
- Python/Node.js/Bash 代码只是可选的执行后端，不决定跨 Agent 兼容性

### Evolver 参考

`skills/evolver/` 展示了三层解耦设计：
1. **文件标准**：SKILL.md YAML frontmatter 让所有 Agent 自动发现技能
2. **运行时环境无关**：纯 Node.js + 文件系统操作，环境变量配置
3. **GEP 协议**：基因进化协议（genes.json/capsules.json/events.jsonl），Agent 只要按协议读写文件就能参与

---

## 架构决策

### 决策 1：reins 技能标准化（✅ 已执行）

**SKILL.md 完全符合 Agent Skills 开放标准：**
- 移除所有 OpenClaw 专属工具引用
- 指令只描述"做什么"，不指定"用什么工具做"
- 新增 API Reference 章节，无 Python 的 Agent 可直接调 HTTP
- 新增 Python Setup Guide，无 Python 环境时自动引导用户安装
- Python 路径完全解耦，无硬编码，通过环境变量覆盖

### 决策 2：Skill Registry 不需要在 Nexus 端实现（✅ 已确认）

**讨论结论：**
- Nexus 已有 `agents` 表 + `capabilities` 列 + 注册 API
- Agent 通过 reins skill 注册时上报 capabilities，Nexus 记录结果
- 发现也是 Agent 侧的事——通过 reins skill 调 `discover` 命令
- **Nexus 不需要额外建 `skills` 表、`/api/v1/skills` 端点**
- 责任划分：
  - **Skill 是 Agent 侧的事**：Agent 决定装什么 skill、怎么读 SKILL.md
  - **Nexus 侧只记录结果**：Agent 注册时上报 capabilities，用于匹配
  - **发现也是 Agent 侧的事**：Agent 通过 reins skill 查找其他 Agent

### 决策 3：Skill 即发现/注册桥梁（✅ 已确认）

```
Agent 安装 reins skill
         ↓
Agent 调用 skill.py connect
         ↓
skill.py → POST /api/v1/agents   ← Nexus 记录 Agent + capabilities
         ↓
Nexus 知道了谁在线、有什么能力
```

Nexus 不需要知道 Agent 装了什么 skill 文件，只需要知道 Agent 声明自己有什么能力。

---

## 改造内容

### reins skill v2.0 变更

| 变更 | 说明 |
|------|------|
| 合并 reins-connector | 连接管理功能并入主 reins skill |
| 移除 Paperclip Issue | create/issues 功能删除 |
| 新增 Goal CRUD | goal-list/create/update/delete |
| 新增 Project CRUD | project-list/create/update/delete |
| 新增 Task CRUD | task-list/create/update/complete/delete |
| 路径解耦 | 无硬编码，从 skill.py 相对路径推算 |
| 标准化 SKILL.md | YAML frontmatter + 纯文本指令 |
| Python Setup Guide | 无 Python 时引导用户安装 |

### 文件结构

```
skills/reins/
├── SKILL.md              # 技能定义（跨 Agent 标准格式）
├── skill.py              # Python CLI 后端（可选）
├── grasp_integration.py  # 知识检索（保持原样）
└── README.md             # 快速开始文档
```

---

## 附：Bug 修复记录

| Bug | 修复方式 |
|-----|---------|
| 迁移 002/008/009/010/012 duplicate column | 改为 no-op，列已由 server.py 内联迁移确保 |
| migration 002 版本冲突 | 重排为 014 |
| trace.total_duration_ms 只读错误 | 确认是旧进程残留，无需修复 |

---

*本记录由刚子于 2026-04-30 01:15 创建*


---


# Nexus 技能审计报告

**日期**: 2026-05-06  
**审计范围**: Nexus 项目目录下所有 SKILL.md 文件

---

## 一、现状总览

当前 Nexus 共有 **9 个技能文件**，分布在 **4 个目录**，其中存在 **1 个重复**。

### 目录结构

```
D:\work\research\agents-nexus\
├── nexus-skills/
│   └── task-dispatch/SKILL.md          ← [Nexus] 任务派发 API 指南
├── skills/
│   ├── grasp/Skill.md                  ← [Nexus] 认知系统接口
│   ├── task-dispatch/SKILL.md          ← [Nexus] 任务派发（完整 API 参考）
│   └── reins/SKILL.md                  ← [Nexus] Agent 连接 Nexus 平台
├── packages/server/skills/
│   └── nexus-agent/SKILL.md            ← [Server] Agent 拉取/执行任务
└── verifier-skills/
    ├── verify-api/SKILL.md             ← [验证者] API 端点验证
    ├── verify-compile/SKILL.md         ← [验证者] 编译/语法验证
    ├── verify-custom/SKILL.md          ← [验证者] 自定义脚本验证
    ├── verify-file/SKILL.md            ← [验证者] 文件存在性验证
    └── verify-llm-review/SKILL.md      ← [验证者] LLM 评审验证
```

---

## 二、逐个技能分析

### 1. task-dispatch（重复！）

| | nexus-skills/task-dispatch | skills/task-dispatch |
|--|---------------------------|---------------------|
| **标题** | Task Dispatch Skill | Task Dispatch |
| **格式** | 纯 Markdown，无前元数据 | 标准 YAML frontmatter |
| **内容** | API 调用示例（curl） | 完整 API 参考 + 使用模式 |
| **详细度** | 简略（~60 行） | 详细（~250 行） |
| **API 覆盖** | 基础 CRUD | CRUD + 验证 + 审阅 + 裁决 |
| **状态流转图** | 有 | 有（更详细） |
| **Acceptance Criteria 类型表** | 无 | 有 |

**结论**：`skills/task-dispatch/SKILL.md` 是完整版，`nexus-skills/` 下的是简略草稿，应**合并保留一份**。

---

### 2. grasp/Skill.md

| 项目 | 状态 |
|------|------|
| **定位** | Nexus 认知系统（Grasp/悟）的对外接口 |
| **核心能力** | register, inject, retrieve, update |
| **实现状态** | 仅设计文档，**未实现** |
| **问题** | 文件 500+ 行，包含 TypeScript 接口定义、MCP 协议、性能指标、监控告警——这更像是一个产品规格书，不是 agent skill |
| **建议** | 拆分为：设计文档（保留在 docs/）+ 精简版 SKILL.md（供 agent 使用的操作指南） |

---

### 3. reins/SKILL.md（太重，需拆分）

| 模块 | 行数 | 功能 | 建议 |
|------|------|------|------|
| Connection | ~30 | 注册、心跳、发现 | **独立为 `nexus-connect`** |
| Decomposition | ~15 | 目标分解 | **独立为 `nexus-decompose`** |
| Management | ~30 | Goal/Project/Task CRUD | **独立为 `nexus-manage`** |
| API Reference | ~30 | HTTP 直接调用 | 保留在 `nexus-manage` |
| Data Model | ~15 | Goal/Project/Task 字段 | 保留在 `nexus-manage` |
| Python 安装指南 | ~50 | 各系统 Python 安装 | **删除，移到 docs/** |
| 无 Python 时的用法 | ~15 | curl 示例 | 保留在 `nexus-manage` |

**核心判断**：reins 是一个"全能瑞士军刀"，但 Agent 只需要它的一部分功能。拆成 3 个小技能更合理。

---

### 4. nexus-agent/SKILL.md

| 项目 | 状态 |
|------|------|
| **定位** | Agent 从 Nexus 拉取任务并执行 |
| **核心能力** | 心跳拉任务、上下文读取、执行、结果上报 |
| **问题** | 与 reins 的 Connection 模块功能高度重叠 |
| **建议** | 功能并入 `nexus-connect`，删除此文件 |

---

### 5-9. verifier-skills/（5 个软件开发验证技能）

| 技能 | 验证方式 | 适用场景 |
|------|----------|----------|
| verify-api | HTTP API 调用 | 端点可用性检查 |
| verify-compile | 编译/语法检查 | 代码正确性 |
| verify-custom | 自定义脚本 | 项目特定验证 |
| verify-file | 文件存在性 | 文件是否生成 |
| verify-llm-review | LLM 代码评审 | 代码质量评估 |

**核心判断**：这 5 个技能**全部面向软件开发验证**，不是通用验证框架。不应该作为"基础设施"技能存在。

**建议**：
- 合并为一个 `verify-dev`（软件开发验证）技能，放在 `skills/dev/` 下
- 未来如果有非软件开发的验证场景（比如文档审查、数据验证），再建独立的验证技能

---

## 三、问题清单

| # | 问题 | 严重程度 | 影响 |
|---|------|----------|------|
| 1 | **task-dispatch 重复**：nexus-skills/ 和 skills/ 各有一份 | 高 | Agent 可能加载错误版本 |
| 2 | **grasp 不是 skill 而是设计文档**：500+ 行规格书，不适合做 agent skill | 中 | Agent 加载时 token 浪费 |
| 3 | **reins 太重**：230 行全能瑞士军刀，Agent 只需要其中一部分 | 中 | 加载 token 浪费，职责不清 |
| 4 | **nexus-agent 与 reins 重叠**：心跳/拉任务/reins 都做了 | 中 | 两个技能干一件事 |
| 5 | **verify 全面向软件开发**：5 个验证技能都是代码/编译/API 验证 | 低 | 未来非软件开发场景需要新技能 |
| 6 | **目录结构混乱**：4 个目录放技能，没有明确规则 | 低 | 维护困难 |
| 7 | **缺少统一格式标准**：有的有 frontmatter，有的没有 | 低 | 解析不一致 |

---

## 四、重构方案

### 目标目录结构

```
D:\work\research\agents-nexus/
├── skills/                          ← 统一技能目录
│   ├── nexus/                       ← Nexus 核心技能
│   │   ├── connect/SKILL.md         ← 注册、心跳、Agent 发现（reins + nexus-agent 合并）
│   │   ├── decompose/SKILL.md       ← 目标分解（从 reins 拆出）
│   │   ├── manage/SKILL.md          ← Goal/Project/Task CRUD（从 reins 拆出）
│   │   └── task-dispatch/SKILL.md   ← 保留完整版，删简版
│   ├── knowledge/                   ← 知识相关
│   │   └── grasp/SKILL.md           ← 精简为 agent 操作指南（~100 行）
│   └── dev/                         ← 软件开发专用
│       └── verify/SKILL.md          ← 合并 5 个软件开发验证技能
├── docs/                            ← 设计文档
│   └── grasp-design.md              ← grasp 原设计文档
└── docs/03-重构规划/
    └── skills-audit-2026-05-06.md   ← 本文件
```

### 具体动作

| 动作 | 涉及文件 | 说明 |
|------|----------|------|
| **拆分** | `reins` → `nexus/connect` + `nexus/decompose` + `nexus/manage` | 1 拆 3 |
| **合并** | `nexus-agent` → `nexus/connect` | 功能并入 connect |
| **去重** | 删除 `nexus-skills/task-dispatch/` | 保留 `skills/task-dispatch/` 完整版 |
| **拆分** | `grasp/Skill.md` → `docs/grasp-design.md` + `skills/knowledge/grasp/SKILL.md` | 设计文档 + 精简 skill |
| **合并** | 5 个 `verifier-skills/*` → `skills/dev/verify/SKILL.md` | 软件开发验证合集 |
| **清理** | 删除 `nexus-skills/` 目录 | 统一到 `skills/` |
| **清理** | 删除 `packages/server/skills/` 目录 | 统一到 `skills/` |
| **清理** | reins 中 Python 安装指南 | 移到 `docs/` 或删除 |

### 重构后技能清单

| 目录 | 技能 | 用途 | 来源 | 估计行数 |
|------|------|------|------|----------|
| **nexus/** | connect | Agent 注册、心跳、发现 | reins Connection + nexus-agent | ~80 |
| **nexus/** | decompose | 目标分解为子任务 | reins Decomposition | ~60 |
| **nexus/** | manage | Goal/Project/Task CRUD | reins Management | ~100 |
| **nexus/** | task-dispatch | REST API 任务派发完整参考 | skills/task-dispatch（完整版） | ~250 |
| **knowledge/** | grasp | 认知系统操作指南（精简版） | grasp（精简） | ~100 |
| **dev/** | verify | 软件开发验证合集 | 5 个 verifier 合并 | ~150 |

**重构前**: 9 个技能文件，4 个目录  
**重构后**: 6 个技能文件，3 个目录（nexus/ + knowledge/ + dev/）

---

## 五、风险与注意事项

1. **API 路径变更**：后端 skills API 需要更新扫描目录为 `skills/`
2. **Agent 加载路径**：确认 Agent 从哪个目录加载技能，重构后需同步更新
3. **向后兼容**：旧 `verifier-skills/` 路径可能有外部引用
4. **reins 拆分边界**：connect/decompose/manage 的拆分需要明确职责边界，避免 Agent 同时加载多个 reins 子技能时功能断裂

---

**下一步**：确认方案后开始执行重构，预计 30 分钟内完成。
