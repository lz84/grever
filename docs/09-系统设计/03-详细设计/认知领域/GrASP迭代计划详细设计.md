# GrASP 迭代计划详细设计

**版本**: v1.0
**作者**: 扣子
**日期**: 2026-05-28
**状态**: 草稿
**关联需求**: Nexus-GrASP 迭代决策回路
**变更记录**:
- v1.0 2026-05-28 扣子 初始版本

---

## 1. 概述

### 1.1 设计目标

Nexus GrASP 迭代计划模块是 GrASP（知）系统的核心决策回路，支持通过多轮迭代生成、比较、讨论，逐步收敛到满足约束条件的最优方案。核心设计原则为 **人机协同迭代**：人类提供反馈，AI 生成建议，系统自动收敛。

### 1.2 核心职责

| 职责 | 说明 |
|------|------|
| 迭代记录 | 管理每轮迭代的输入输出 |
| AI 分析 | 自动生成方案分析和建议 |
| 讨论机制 | 支持人类与 AI 的多轮对话 |
| 共识检测 | 检测讨论中的共识关键词 |
| 约束应用 | 共识达成后自动更新约束 |

---

## 2. 核心流程

### 2.1 迭代完整链路

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           迭代完整链路                                        │
└──────────────────────────────────────────────────────────────────────────────┘

Step 1: 创建迭代记录
  POST /api/v1/goals/{goal_id}/iterations
  iteration_number = max + 1
         │
         ▼
Step 2: 方案生成与评分
  Agent 生成候选方案
  POST /api/v1/solutions/compare 计算评分
         │
         ▼
Step 3: AI 分析
  POST /api/v1/goals/{goal_id}/iterations/{iter_id}/analysis
  _generate_ai_analysis() 生成分析和建议
         │
         ▼
Step 4: 人工讨论
  POST /api/v1/goals/{goal_id}/iterations/{iter_id}/discuss
  1. 追加人类消息
  2. AI 生成回复
  3. 检测共识
         │
         ▼
Step 5: 共识达成
  共识关键词检测 → _apply_consensus()
  1. 更新约束条件
  2. 创建下一轮迭代
         │
         ▼
Step 6: 迭代完成
  status → completed
  记录 completed_at
```

### 2.2 讨论流程时序

```
时间轴
  │
  │  POST /iterations/{id}/discuss
  │  ──────────────────────────────
  ▼
T=0   接收讨论请求
  │
  ├─ Step 1: 解析已有对话
  │    _parse_discussion_list(iter_row.ai_discussion)
  │
  ├─ Step 2: 追加人类消息
  │    discussion.append({role: "human", content: ...})
  │
  ├─ Step 3: AI 生成回复
  │    ai_reply = _generate_ai_reply(content, goal_id, db)
  │    discussion.append({role: "ai", content: ai_reply})
  │
  ├─ Step 4: 保存对话
  │    UPDATE goal_iterations SET ai_discussion = ...
  │
  ├─ Step 5: 检测共识（仅 human 时）
  │    if _detect_consensus(discussion):
  │        _apply_consensus(goal_id, iter_id, db)
  │
  └─ Step 6: 返回响应
       {discussion: [...], consensus: {...}}
```

---

## 3. 数据模型

### 3.1 GoalIteration 表结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(50) | 迭代 ID |
| goal_id | VARCHAR(50) | 关联目标 ID |
| iteration_number | INT | 迭代序号（从 1 开始） |
| solution_id | VARCHAR(50) | 关联方案 ID |
| score | FLOAT | 本轮评分 |
| status | VARCHAR(20) | 状态：planned/running/completed |
| ai_analysis | TEXT | AI 分析内容 |
| ai_discussion | TEXT | 讨论记录（JSON 数组） |
| started_at | DATETIME | 开始时间 |
| completed_at | DATETIME | 完成时间 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 3.2 Discussion 消息结构

```json
{
  "role": "human" | "ai",
  "content": "消息内容",
  "timestamp": "2026-05-28T10:00:00"
}
```

---

## 4. 状态机

### 4.1 Iteration 状态机

| 当前状态 | 可转换到 | 触发条件 |
|---------|---------|---------|
| `planned` | `running` | 开始执行本轮迭代 |
| `running` | `completed` | 本轮迭代完成 |
| `running` | `failed` | 本轮迭代失败 |
| `completed` | — | 终态 |

### 4.2 状态流转图

```
[planned]
   │ 开始执行
   ▼
[running] ◀──────────┐
   │                  │ 继续讨论
   │ 完成讨论         │
   ▼                  │
[completed] ─────────┘
```

---

## 5. 关键函数签名

### 5.1 迭代管理

```python
# reins/api/goals_exploration_iteration.py

def create_iteration(goal_id: str, req: CreateIterationRequest, db: Session):
    """
    创建迭代记录
    
    自动生成 iteration_number = max + 1
    返回: {"id": "iter-xxx", "iteration_number": 3, "status": "planned"}
    """

@router.get("/api/v1/goals/{goal_id}/iterations")
def list_iterations(goal_id: str, db: Session):
    """
    获取迭代历史
    
    返回迭代列表
    """
```

### 5.2 AI 分析

```python
# reins/api/goals_exploration_iteration.py

@router.post("/api/v1/goals/{goal_id}/iterations/{iter_id}/analysis")
def generate_analysis(goal_id: str, iter_id: str, db: Session):
    """
    生成 AI 分析
    
    返回: {"analysis": "...", "suggestion": "..."}
    """
```

### 5.3 讨论机制

```python
# reins/api/goals_exploration_iteration.py

@router.post("/api/v1/goals/{goal_id}/iterations/{iter_id}/discuss")
def send_discussion(goal_id: str, iter_id: str, req: DiscussRequest, db: Session):
    """
    发送讨论消息
    
    1. 追加人的消息到 ai_discussion
    2. AI 生成回复
    3. 如果是 human 且检测到共识，自动触发 _apply_consensus
    """

# reins/api/solutions_iteration_helpers.py

def _generate_ai_analysis(goal_id: str, iter_id: str, db: Session) -> dict:
    """生成 AI 分析（基于解决方案和约束）"""

def _generate_ai_reply(content: str, goal_id: str, db: Session) -> str:
    """生成 AI 回复（关键词匹配 + 模板）"""
```

### 5.4 共识应用

```python
# grasp/api/solutions_consensus.py

def _apply_consensus(goal_id: str, iter_id: str, db: Session) -> dict:
    """
    应用共识
    
    1. 从讨论中提取共识
    2. 更新 IterationConstraint 表
    3. 创建下一轮迭代（可选）
    """
```

---

## 6. 接口清单

### 6.1 迭代管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/goals/{goal_id}/iterations | 创建迭代记录 |
| GET | /api/v1/goals/{goal_id}/iterations | 获取迭代历史 |
| POST | /api/v1/goals/{goal_id}/iterations/{id}/analysis | 生成 AI 分析 |
| POST | /api/v1/goals/{goal_id}/iterations/{id}/discuss | 发送讨论消息 |
| POST | /api/v1/goals/{goal_id}/iterations/{id}/consensus | 手动触发共识检测 |

### 6.2 Sprint 78 新增

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/solutions/consensus | 手动触发共识 |

---

## 7. 错误处理

### 7.1 错误码定义

| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| 404 | Goal/Iteration 不存在 | 返回 404 错误 |
| 400 | 参数错误 | 返回详细错误信息 |
| 500 | 共识应用失败 | 记录错误，返回错误详情 |

### 7.2 异常处理

```python
# Goal 不存在
goal_row = db.execute(
    text("SELECT id, title FROM goals WHERE id = :id"),
    {"id": goal_id}
).fetchone()
if not goal_row:
    raise HTTPException(status_code=404, detail="Goal not found")

# Iteration 不存在
iter_row = db.execute(
    text("SELECT id FROM goal_iterations WHERE id = :id AND goal_id = :gid"),
    {"id": iter_id, "gid": goal_id}
).fetchone()
if not iter_row:
    raise HTTPException(status_code=404, detail="Iteration not found")

# 共识应用失败（不阻断讨论）
try:
    consensus_result = _apply_consensus(goal_id, iter_id, db)
except Exception as e:
    logger.error(f"[discuss] Consensus auto-trigger failed: {e}")
    consensus_result = {"consensus": True, "error": str(e)}
```

---

## 8. 与其他模块的关系

### 8.1 与 Solutions 模块

- 迭代关联具体方案（solution_id）
- 方案评分影响迭代结果
- 收敛判断依赖方案评分

### 8.2 与 IterationConstraint 模块

- 共识达成后更新约束
- 约束变化影响下一轮方案生成

### 8.3 与 Exploration Mode

- 迭代是探索模式的核心机制
- 探索模式设置 iteration 参数
- 迭代结果反馈给探索模式

---

*文档完成 — 2026-05-28*