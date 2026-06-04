# Sprint Execution Plan v7（2026-04-16）

> 基于两轮测试暴露的问题，重新规划 Sprint 节奏
> 规划日期：2026-04-16
> 总工期：~17 天

---

## 规划原则

1. **按功能切，不按层切** — 每个 Sprint 必须端到端可跑
2. **先通再全** — 先把核心链路跑通，再补功能和细节
3. **页面验证是硬标准** — curl 通了不算，浏览器里能看能用才算

---

## Sprint 节奏总览

| Sprint | 主题 | 目标 | 预计 | 验收标准 |
|--------|------|------|------|----------|
| Sprint 10 | 基础设施修复 | 让系统能跑，数据能通 | 3 天 | 无 500 错误，所有页面正常加载 |
| Sprint 11 | 核心链路打通 | Goal→分解→派发→执行→回收 | 5 天 | 完整流程端到端跑通 |
| Sprint 12 | 功能补齐 | 场景库+执行监控+全局功能 | 5 天 | E2E 测试通过率 ≥ 85% |
| Sprint 13 | 打磨验收 | Bug修复 + E2E测试 + 场景进化 + 前端对接 | ~1 天 | 全链路通过，无 500 错误 |

---

## Done 标准

不再是"单元测试通过"。现在是：

| 层级 | 要求 |
|------|------|
| 代码 | 单元测试通过 + 无 lint 警告 |
| API | curl 验证通过 |
| **页面** | **浏览器能正常渲染（不是白屏）** ← 硬标准 |
| **端到端** | **核心流程能完整跑通** ← 硬标准 |
| 文档 | 测试报告已写入 E2E-Test-Results.md |

节奏：先修路 → 再跑车 → 补功能 → 磨细节。每个 Sprint 结束后**我亲自做页面验证和回归测试**，不等到用户问起才检查。

---

## Sprint 10：基础设施（先修路）

**解决问题**：现在连基本的数据加载都有问题（500 错误、缺表、列名不对）

| 任务 ID | 任务名称 | 状态 | 说明 |
|---------|----------|------|------|
| MAK-218 | 测试-全链路 E2E 测试 | todo | E2E 验证当前基础设施状态 |
| MAK-214 | 单元测试-后端派发机制 | todo | 确保派发逻辑有测试覆盖 |
| MAK-215 | 单元测试-执行结果回收 | todo | 确保回收逻辑有测试覆盖 |
| MAK-222 | 单元测试-场景库反馈闭环 | todo | 场景库单元测试 |
| MAK-223 | 系统测试-全链路 E2E | todo | 全链路集成测试 |
| MAK-224 | Bug 修复-按测试报告修复 | todo | 根据谷子测试报告修复所有 bug |
| MAK-225 | 复测-回归测试验证 | todo | Bug 修复后的回归测试 |
| MAK-212 | 业务测试-注入管理 API | todo | /api/v1/grasp/inject/* 验证 |
| MAK-213 | 业务测试-安全中心 API | backlog | 暂时搁置 |

**交付物**：
- 场景库建表 → 解决 E2E-05 全部 500
- Agent 数据修复 → 列表能正常显示
- Schema 冲突修复 → ScenarioMetrics 类型统一
- 侧边栏补全 → 安全中心、技能库导航加上
- 测试数据填充 → 有足够的数据能看

**验收**：无 500 错误，所有页面正常加载

---

## Sprint 11：核心链路（跑通一辆车）

**解决问题**：轮子和车身都有，但没装到一辆车上

| 任务 ID | 任务名称 | 状态 | 说明 |
|---------|----------|------|------|
| MAK-226 | 目标自动分解（后端） | todo | Goal → LLM 分解 → Tasks |
| MAK-236 | 目标自动分解 UI | todo | P1 前端 |
| MAK-229 | 目标自动分解 UI（终极版） | todo | 前端终极版 |
| MAK-232 | 场景库反馈闭环（后端） | todo | 反馈 API + 版本升级 |
| MAK-233 | 工作流引擎与派发集成 | todo | Workflow → Tasks 自动加入派发队列 |
| MAK-234 | 执行监控页面增强 | todo | 实时任务队列 + SSE 日志流 |
| MAK-227 | Agent 端 Skill 适配 | todo | Agent 收到任务后自主执行 |
| MAK-235 | 任务失败重试机制 | todo | retry/blocked 状态 |
| MAK-237 | Agent 负载管理与限流 | todo | max_concurrent_tasks |

**交付物**：
- 目标自动分解前端 UI → 创建目标后能分解
- Agent 派发前端 → 能领任务
- 任务完成+进度回收 → Goal 进度自动更新
- 失败重试流程 → retry/blocked 状态正确
- 场景数据背书展示 → 成功率/次数能看到

**验收**：⚠️ 部分通过，详见实测记录

**实测验证（2026-04-16）**：
- ✅ POST /tasks/{id}/complete → 200 OK, goal_progress 更新到 60%
- ✅ POST /tasks/{id}/fail (retry<3) → next_action=retry, delay=30s
- ✅ POST /tasks/{id}/fail (retry>=3) → next_action=blocked
- ✅ POST /tasks/{id}/retry → retry_count 重置为 0
- ❌ POST /agents/{id}/heartbeat → 400 INVALID_PARAMETER（Pydantic AgentStatus enum bug）

**待修复**：
1. 前端 api.ts 缺少 completeTask/failTask/retryTask 方法（麻子处理中）
2. TaskList 页面缺少操作按钮
3. heartbeat API 有 enum 验证 bug（server.py AgentStatus 问题）

---

## Sprint 12：功能补齐（把功能做全）

**解决问题**：Dashboard 缺模块、执行监控缺筛选、全局缺面包屑/响应式

| 任务 ID | 任务名称 | 状态 | 说明 |
|---------|----------|------|------|
| MAK-189 | 后端-API 补全：场景库 | todo | POST/GET/PUT/DELETE /scenarios |
| MAK-190 | 后端-API 补全：注入管理 | todo | GET/PATCH /grasp/inject/rules |
| MAK-192 | 后端-API 补全：安全中心 | todo | 审计日志 + 告警 API |
| MAK-188 | 前端-场景库页面开发 | todo | Mock 数据，先跑起来 |
| MAK-187 | 前端-认知中心页面开发 | todo | 知识库 + 认知评估 |
| MAK-191 | 前端-安全中心页面开发 | todo | Mock 数据 |
| MAK-193 | 前端-Mock→真实 API 对接 | todo | 替换 mock 数据 |

**交付物**：
- Dashboard 补全 → 最近执行列表 + 30 秒自动刷新
- 执行监控完善 → 筛选功能 + 报告按钮逻辑
- 安全中心页面 → 告警列表 + 审计日志
- 全局功能 → 面包屑 + 响应式 + 错误边界 + Loading

**验收**：E2E 测试通过率 ≥ 85%

---

## Sprint 13：打磨验收（达到替代标准）

**解决问题**：细节没打磨、缺少自动化测试、Paperclip 审批流程缺失

| 任务 ID | 任务名称 | 状态 | 说明 |
|---------|----------|------|------|
| MAK-231 | Bug 修复 + 复测 | todo | 终极版测试报告 bug |
| MAK-228 | 场景进化闭环 | todo | 执行 → 评估 → 升级 |
| MAK-230 | 全链路 E2E 测试-终极版 | todo | 完整链路测试 |
| MAK-238 | 全链路系统测试（无Mock） | todo | 差距评估报告 |
| MAK-219 | 工具-Paperclip 迁移工具 | todo | Issues → Goals/Tasks |
| 前端 9 Bug | 谷子测试报告中的问题 | todo | 待确认具体项 |

**交付物**：
- 前端 9 个 Bug 修复 → 谷子测试报告中的问题
- 审批流程 → 对标 Paperclip
- Playwright 自动化 → 替代人工代码审查
- 全量回归测试 → 98 项 E2E 重测

**验收**：
- 单元测试 ≥ 80%
- Paperclip 替代就绪度 ≥ 80%

---

## Sprint 14：页面验收 + 错误处理（2026-04-16 新增）

**解决问题**：Mock 数据残留、缺少错误处理、缺乏页面级验收

**任务**：
1. 删除所有 Mock 数据 + 统一错误处理框架
2. 前后端模块联调测试（6 个业务模块）
3. 逐页业务测试 + 截图验收

**验收标准**：
- 所有页面零 Mock 数据
- API 失败时统一错误提示
- 所有页面截图保存
- 每个模块端到端流程跑通

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1-v6 | 2026-04-15 | 早期迭代规划 |
| **v7** | **2026-04-16** | **基于两轮测试结果重新规划 Sprint 10-13，确立新的 Done 标准** |

---

## Sprint 完成状态

| Sprint | 状态 | 完成日期 | 备注 |
|--------|------|----------|------|
| Sprint 10 | ✅ 完成 | 2026-04-16 | DB统一+场景库+Agent+Dashboard+Workflow Steps |
| Sprint 11 | ⚠️ 部分完成 | 2026-04-16 | 后端API完成，前端需补全，heartbeat需修 |

### Sprint 10 详情（2026-04-16）
**完成项**：场景库建表(4场景26步骤)/Agent数据/DB路径统一/Dashboard补全/Workflow Steps修复
**待处理**：旧DB文件已清理（保留唯一 packages/server/data/reins.db）

### Sprint 11 详情（2026-04-16）
**完成项**：后端API(complete/fail/retry实测通过)/前端AgentDetailModal心跳
**待处理**：前端api.ts缺方法/TaskList缺按钮/heartbeat有Pydantic bug
