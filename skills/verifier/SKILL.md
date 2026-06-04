# Verifier Skill - Nexus 验证技能

## 核心原则

**先跑测试，再下结论。没有证据不判断。**

验证不是"看着代码猜质量"，而是"跑测试拿到证据，基于证据判断"。

---

## 执行者上下文（context_md）

验证者派发路径的 prompt 会自动注入 `### 🧭 执行者上下文` 小节，包含执行者填写的完整 context_md。该上下文包含：

1. **执行摘要** — 执行者做了什么、关键决策、已知风险
2. **变更文件** — 哪些文件被修改/新增/删除
3. **验证方法** — 执行者建议的验证步骤和命令
4. **相关资源** — 设计文档、相关任务 ID、参考链接

**使用方式**：
- 参考执行者提供的验证方法和变更文件，快速定位需要检查的范围
- 对照执行摘要中的"已知风险"，重点关注潜在问题区域
- 执行者提供的验证命令应作为验证的起点，但**不能替代**你自己的自动化测试和数据验证
- 如果 context_md 为空或内容无效，应在验证报告中记录此问题

---

## 验证流程

收到验证请求后，严格按以下步骤执行：

### Step 1: 解析 acceptance_criteria

从任务描述或 DB 中读取验收标准：
```json
{"criteria": [
  {"type": "compile", "name": "TypeScript编译", "desc": "npx tsc --noEmit 0 errors"},
  {"type": "api", "name": "Solutions API", "endpoint": "http://127.0.0.1:8094/api/v1/solutions", "desc": "返回200+正确JSON"},
  {"type": "page", "name": "方案列表页", "url": "http://localhost:5173/goals/test/solutions", "desc": "不是白屏，关键元素可见"}
]}
```

### Step 2: 跑自动化测试（硬性要求）

根据 criteria type 执行对应验证命令：

| type | 命令 | 通过标准 |
|------|------|----------|
| compile | `npx tsc --noEmit` 或 `python -m py_compile` | 0 errors |
| api | `curl -s -o /dev/null -w "%{http_code}" <endpoint>` | 200 + 有效 JSON |
| page | `curl -s -o /dev/null -w "%{http_code}" <url>` | 200 + 响应体 > 100 字节 |
| custom | 执行 `script` 字段指定的命令 | 命令 exit 0 |
| regression | `pytest scripts/regression/` | 所有测试通过 |

**关键规则**：
- 必须实际执行命令，不能假设能通过
- 必须记录命令输出作为证据
- 任何一项失败 → 整体验证失败

### Step 3: 数据验证（⚠️ 2026-05-12 新增，Sprint 68-73 惨痛教训）

**业务数据验证是强制步骤，不是可选项。** API 返回 200 不代表数据正确。

对于新增/修改功能的验证，**必须检查 DB 中的实际数据内容**：

```bash
# 示例：验证方案是否关联了工程
python -c "
import sqlite3; conn=sqlite3.connect('data/reins.db'); c=conn.cursor();
c.execute('SELECT id, project_ids, task_ids FROM solutions LIMIT 5');
[print(r) for r in c.fetchall()]
"
# 如果 project_ids/task_ids 全是 null → 验证失败！
```

**通用规则**：
- 任务 done 时写入方案的表 → 查方案表的 task_ids 是否非 null
- 新加字段 → 查 DB 中该字段是否有值
- 自动捕获逻辑 → 真的跑一个任务完成流程，看方案是否自动生成
- 方案去重 → 提交两次相同参数，看是否只有一条记录

**数据验证必须做的 4 件事**：
1. **查列**：`PRAGMA table_info(表名)` 确认字段存在
2. **查值**：`SELECT 关键字段 FROM 表名` 确认非 null
3. **查关联**：JOIN 或子查询确认外键关系有效
4. **查业务**：跑一次完整业务流，看数据是否符合预期

### Step 4: 跑回归测试

执行 `scripts/regression/` 下的所有相关测试：
```bash
pytest scripts/regression/ -v
```

如果某个测试失败，说明引入了 regression，必须退回修复。

### Step 5: 主观审视（基于证据）

在自动化测试和数据验证都通过的前提下，进行主观检查：
- 代码结构是否合理
- 命名是否清晰
- 是否有明显的安全/性能问题
- 是否符合项目规范

**禁止**：在自动化测试或数据验证未通过时做主观判断。

### Step 6: 输出验证报告

必须使用以下格式：

```json
{
  "task_id": "task-xxx",
  "verification_result": "pass" | "fail",
  "checks": [
    {"name": "TypeScript编译", "type": "compile", "passed": true, "evidence": "npx tsc --noEmit: 0 errors"},
    {"name": "Solutions API", "type": "api", "passed": true, "evidence": "curl → 200, body: {\"solutions\":[]}"},
    {"name": "数据验证", "type": "data", "passed": true, "evidence": "solutions 表 project_ids 非 null, task_ids 非 null"},
    {"name": "回归测试", "type": "regression", "passed": true, "evidence": "pytest: 12 passed"}
  ],
  "issues": [],
  "summary": "所有检查通过"
}
```

**必须包含**：
- 每项检查的 `evidence` 字段（实际命令输出）
- 失败的检查必须包含 `detail` 字段（具体错误信息）
- 整体 `verification_result` 必须基于所有 checks 的 passed 状态
- **数据验证 check 是必填项**，不能省略

---

## 已知回归测试用例

每修一个 bug，必须在此处和 `scripts/regression/` 中各加一条。

| Bug | 测试文件 | 描述 |
|-----|----------|------|
| 验证空壳 | `scripts/regression/test_verification.py` | `_dispatch_to_worker` 必须真正调用验证智能体 |
| API 422 | `scripts/regression/test_solutions_api.py` | Create Solution 必须接受 dict 和 string 类型的 parameters |
| 方法不匹配 | `scripts/regression/test_solutions_api.py` | setGoalMode 必须用 POST 方法 |
| ORM 字段缺失 | `scripts/regression/test_goal_model.py` | Goal 模型必须定义 mode/optimization_target 等列 |
| ruling_comment_id | `scripts/regression/test_verification.py` | 验证通过后 ruling_comment_id 必须非空 |

---

## 命令模板

```bash
# TypeScript 编译
cd packages/ui && npx tsc --noEmit 2>&1

# Python 编译
python -m py_compile path/to/file.py

# API 检查
curl -s -w "\nHTTP %{http_code}" http://127.0.0.1:8094/api/v1/solutions

# 页面检查
curl -s -w "\nHTTP %{http_code}" http://localhost:5173/solutions

# 回归测试
cd D:\work\research\agents-nexus && pytest scripts/regression/ -v

# DB 检查
python -c "import sqlite3; conn=sqlite3.connect('data/reins.db'); c=conn.cursor(); c.execute('PRAGMA table_info(solutions)'); print([r[1] for r in c.fetchall()])"
```

---

## 纪律

1. **不跑测试不判断** — 没有执行验证命令就下结论 = 验证失败
2. **不记录证据不报告** — 每项检查必须有证据字段
3. **回归测试是硬门** — 新代码不能破坏已有功能
4. **自动化先于主观** — 主观判断只在自动化通过后进行
5. **不查数据不算验证** — API 200 + 页面不白屏 ≠ 功能正常，必须查 DB 数据
6. **不跑业务闭环不算完成** — 说"任务完成自动创建方案"，就真跑一个任务看看

---

## 历史教训（2026-05-12 固化）

| 教训 | 来源 | 固化措施 |
|------|------|----------|
| Sprint 50-52 质量事故 | MEMORY.md | 验收三板斧 + 任务派发必须带 Done Criteria |
| Sprint 64 验证缺失 | MEMORY.md | acceptance_criteria 为空 → 强制拦截 |
| Sprint 67 验证空壳 | MEMORY.md | result_verifier.py 不再直接返回 passed |
| Sprint 68-73 数据割裂 | 2026-05-12 | 验证必须查 DB 数据 + 跑业务闭环 |
| 反复犯同错 | 用户指令 | 本文件固化所有教训，不靠记忆 |
