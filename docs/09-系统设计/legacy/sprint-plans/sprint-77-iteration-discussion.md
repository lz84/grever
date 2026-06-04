# Sprint 77: 迭代模式对话调整

## 背景
迭代模式下，每次迭代完成后需要人与 AI 有交流，动态调整后续迭代内容和计划。

## 改动范围

### 后端
1. **新建 `goal_iterations` 表**（migration）
   - 迭代序号、状态、方案ID、评分
   - `ai_analysis` — AI 分析报告
   - `ai_discussion` — JSON 数组，存储人机对话记录
   - 开始/结束时间

2. **新增 API**：
   - `POST /api/v1/goals/{id}/iterations` — 创建新迭代
   - `GET /api/v1/goals/{id}/iterations` — 获取迭代历史
   - `POST /api/v1/goals/{goal_id}/iterations/{iter_id}/analysis` — AI 分析本次迭代
   - `POST /api/v1/goals/{goal_id}/iterations/{iter_id}/discuss` — 发送讨论消息

3. **自动触发**：
   - `auto_capture_solution` 完成时 → 自动创建/更新 goal_iterations 记录
   - AI 自动生成分析

### 前端
1. **GoalDetail 新增 "迭代" tab**（仅 optimization 模式可见）
2. **迭代列表** — 每个迭代卡片显示：
   - 方案/评分/约束
   - AI 分析摘要
   - 展开讨论区
3. **讨论区** — 类似聊天界面：
   - AI 消息 + 人消息
   - 输入框 + 发送按钮
   - 发送后触发 AI 响应

### 验收标准
1. 创建 optimization 模式目标 → 可以看到迭代 tab
2. 迭代完成后自动显示 AI 分析
3. 人发送消息 → AI 回复（通过子代理）
4. 讨论记录持久化

## 依赖
- Sprint 76 的 `_collect_result` 修复（已有）
- `iteration_constraints` 表（已有）

## Done Criteria
- [ ] migration 执行成功，新表创建
- [ ] 迭代列表 API 返回正确数据
- [ ] 讨论 API 可以发送/接收
- [ ] 前端迭代 tab 显示
- [ ] 讨论区可以发送消息并收到 AI 回复
- [ ] TS 编译 0 errors
