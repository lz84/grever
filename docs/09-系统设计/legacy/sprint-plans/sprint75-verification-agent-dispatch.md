# Sprint 75: 验证智能体调度做实

> 基线：`feat/sprint68`（Sprint 68-73 迭代优化 + Sprint 74 Push 架构）
> 来源：用户指示"验证是验证智能体的任务，框架只评估验证智能体有没有能力"
> 核心思想：框架不验证，只调度验证智能体 + 评估其能力

## 问题陈述

Sprint 67 发现 `_dispatch_to_worker` 是空壳（永远返回 `{"passed": True}`）。

但更深层的问题是：**验证不应该是框架的硬编码逻辑，而是验证智能体的能力。**

框架的职责：
1. **选谁验证** → 根据任务类型匹配有能力的验证智能体
2. **派给谁** → 把任务结果 + 验收标准发给验证智能体
3. **它行不行** → 记录历史表现，评估能力

## 架构变更

### 现状（空壳）
```
任务 done → _dispatch_to_worker() → return {"passed": True}  # 永远通过
```

### 改后（真实派发）
```
任务 done
  → 框架：根据 verifier_type 查 capabilities 表 → 找到有能力的验证智能体
  → 框架：查 ability_tracker → 选历史表现最好的
  → 框架：dispatch(任务结果 + 验收标准 + 产物) → 验证智能体
  → 验证智能体：执行验证 → 返回 passed/failed + 证据
  → 框架：记录能力数据（这次验证是成功还是失败）
  → 根据结果决定 done / failed / review_needed
```

## 关键设计原则

### 1. 能力发现（不是硬编码映射）

```
capabilities 表：
  id, name, category, description, status, agents

查询逻辑：
  SELECT agents FROM capabilities WHERE category = :verifier_type AND status = 'active'
  
示例：
  category = "code_test" → agents = ["麻子", "扣子"]
  category = "content_review" → agents = ["蚊子"]
  category = "analysis_check" → agents = ["谷子"]
  category = "default" → agents = ["刚子", "麻子", "扣子"]
```

### 2. 能力评估（ability_tracker）

```
verification_task_log 表：
  id, task_id, agent_id, verifier_type, input_summary, output_raw, 
  passed, message, duration_seconds, created_at

能力统计：
  SELECT agent_id, COUNT(*) as total,
         SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed_count,
         AVG(duration_seconds) as avg_duration
  FROM verification_task_log
  WHERE agent_id = :agent_id
  GROUP BY agent_id
```

**能力排名逻辑**：
- 优先选通过率高（passed_count/total）的智能体
- 通过率的智能体之间，选平均用时短的
- 没有历史数据的智能体，给默认权重

### 3. 降级策略

| 情况 | 处理 |
|------|------|
| 没有匹配的验证智能体 | 触发人工审核（review_needed） |
| 验证智能体超时 | 记录失败，标记 failed |
| 验证智能体返回失败 | 记录失败，任务进入 review_needed |
| 验证循环 ≥ 3 次 | 升级为 disputed，转人工裁决 |

## 修改文件

| 文件 | 改动 |
|------|------|
| `result_verifier.py` | `_dispatch_to_worker` 替换为空壳，接入 VerificationDispatcher |
| `verifiers/agent_dispatcher.py` | **已有**：动态能力发现 + 派发逻辑 |
| `verifiers/ability_tracker.py` | **已有**：能力记录 + 统计查询 |
| `verifiers/task_builders.py` | **已有**：构造验证任务 prompt |
| `verifiers/evidence_parser.py` | **已有**：解析验证智能体输出 |
| `migration/020_verification_task_log.py` | **已有**：verification_task_log 表 |
| `capabilities 表` | **已有**：4 条验证能力记录 |

## 不需要改的

- `scheduler/core.py` — 调度逻辑不变
- `optimization_loop.py` — 迭代优化不变
- `solutions.py` — 方案管理不变
- 前端 UI — Sprint 75 是纯后端改造

## 核心流程

### 任务完成后的验证链

```python
# result_verifier.py
def _dispatch_to_worker(self, task_id, subjective_checks, result):
    """不再返回 {"passed": True}，而是真实派发"""
    dispatcher = VerificationDispatcher(get_db_session)
    
    for check in subjective_checks:
        vr = dispatcher.dispatch(
            task_id=task_id,
            result_summary=result,
            acceptance_criteria=check['desc'],
            artifacts={"result_summary": result},
            verifier_type=check['type'],
        )
        
        if vr.agent_id is None:
            # 无验证智能体 → 人工审核
            results.append({"passed": False, "detail": "无验证智能体，需人工审核"})
        elif vr.passed:
            results.append({"passed": True, "detail": vr.message})
        else:
            results.append({"passed": False, "detail": vr.message})
    
    return results
```

### 验证智能体调度

```python
# agent_dispatcher.py
def dispatch(self, task_id, result_summary, acceptance_criteria, artifacts, verifier_type):
    # 1. 查 capabilities 表 → 找到候选智能体
    candidates = self._find_candidates(verifier_type)
    if not candidates:
        return VerificationResult(agent_id=None, passed=False, message="无验证智能体")
    
    # 2. 查 ability_tracker → 选最优
    best = self._select_best(candidates)
    
    # 3. 派发
    output = self._spawn_verification(best, prompt)
    
    # 4. 解析结果
    parsed = EvidenceParser.parse(output)
    
    # 5. 记录能力
    AbilityTracker.record(best, parsed)
    
    return VerificationResult(
        agent_id=best, 
        passed=parsed["passed"],
        message=parsed["message"],
        evidence=parsed["evidence"]
    )
```

## Acceptance Criteria

```json
{
  "criteria": [
    {
      "type": "api",
      "name": "验证派发不空壳",
      "desc": "调用 complete_task 后，VerificationDispatcher 真实派发给验证智能体，不是直接返回 True"
    },
    {
      "type": "compile",
      "name": "Python 编译",
      "desc": "python -m py_compile 所有 .py 文件，0 errors"
    },
    {
      "type": "compile",
      "name": "TypeScript 编译",
      "desc": "npx tsc --noEmit 0 errors"
    },
    {
      "type": "db",
      "name": "Migration 020 执行",
      "desc": "verification_task_log 表创建成功，可写入"
    },
    {
      "type": "e2e",
      "name": "端到端验证派发",
      "desc": "创建 code_test 任务 → 完成 → 验证智能体被真实派发 → 日志表有记录 → 状态根据 passed 正确流转"
    },
    {
      "type": "custom",
      "name": "降级容错",
      "desc": "验证智能体超时不崩溃 → 框架返回 failed；无匹配智能体 → review_needed"
    }
  ]
}
```

## 依赖关系

```
Sprint 75 依赖：
- Sprint 67（result_verifier.py 基础框架）✅ 已有
- Sprint 68-73（verifiers/ 模块）✅ 已有
- OpenClaw sessions_spawn 接口 ✅ 已有
```

## 时间估算

| 步骤 | 时间 |
|------|------|
| 确认现有 verifiers/ 模块完整性 | 15 min |
| 替换 _dispatch_to_worker 空壳 | 30 min |
| 端到端测试 | 30 min |
| 回归测试 | 15 min |
| **总计** | **~1.5 小时** |
