# Sprint 58: 人工裁决中心

> 设计文档: docs/17-manual-ruling-center-design.md
> 目标：建立系统内闭环的人工裁决入口，不依赖外部系统
> 命名规范：人工而非人类

---

## Phase 0: 后端 API（2任务，可并行）

### 0.1 GET /api/v1/human-review/stats

**文件**: `packages/server/src/reins/api/tasks.py`（或新建 `human_review.py`）

**内容**:
- 查询 disputed / waiting_human / pending human_input 数量
- 返回最近 5 条待处理项
- 接口: `GET /api/v1/human-review/stats`

**验收标准**:
- [ ] curl 返回 200 + 正确 JSON 结构
- [ ] disputed_count = 实际 disputed 任务数
- [ ] pending_assist_count = 实际 pending human_input 数
- [ ] recent 数组包含 3 种类型的最近记录

### 0.2 GET /api/v1/human-review/pending + POST /human-review/batch-ruling

**文件**: 同上

**pending 列表**:
- `GET /api/v1/human-review/pending?type=all|disputed|waiting|assist&page=1&page_size=20`
- 合并查询 tasks(disputed/waiting_human) + human_input_requests(pending)
- 返回统一结构 + 分页

**批量裁决**:
- `POST /api/v1/human-review/batch-ruling`
- Body: `{ task_ids: [...], ruling: "...", action: "done|in_progress|verifying" }`
- 循环调用 ruling API，返回成功/失败统计

**验收标准**:
- [ ] curl pending 返回 200 + 包含 3 种类型的数据
- [ ] type=disputed 只返回 disputed 任务
- [ ] type=assist 只返回 human_input 请求
- [ ] 批量裁决 2 个任务 → 2 个都更新成功
- [ ] 批量裁决中一个失败 → failed 数组包含失败原因

---

## Phase 1: 前端核心页面（2任务）

### 1.1 裁决中心 /rulings 页面

**文件**: `packages/ui/src/pages/RulingsPage.tsx`（新建）

**内容**:
- Tab 切换: 全部/待裁决/待审批/待协助
- 筛选: 类型/优先级/创建时间
- 列表展示三种类型（不同 badge 颜色和操作按钮）
- 快速裁决弹窗（确认框 + 裁决意见 + action 选择）
- 批量操作（checkbox + 批量动作下拉 + 执行）
- human_input 详情面板（schema 表单渲染）
- 分页

**验收标准**:
- [ ] TypeScript 编译通过（npx tsc --noEmit 0 errors）
- [ ] 页面能正常渲染（不是白屏）
- [ ] Tab 切换正确过滤
- [ ] 快速裁决 → API 调用成功 → 列表刷新
- [ ] 批量裁决 → 多个任务同时更新
- [ ] human_input 点击展开详情面板（不跳转）

### 1.2 TaskDetail disputed 裁决入口

**文件**: `packages/ui/src/pages/TaskDetail.tsx`

**内容**:
- 检测任务 status === 'disputed' 时显示裁决输入框
- 输入框 + action 选择（通过/打回/调整）
- 提交后写 comment + 更新状态 + 刷新页面
- 显示最近验证结果摘要

**验收标准**:
- [ ] disputed 任务详情页显示裁决输入框
- [ ] 提交裁决 → comment 写入 → 状态更新
- [ ] 非 disputed 任务不显示裁决输入框
- [ ] TypeScript 编译通过

---

## Phase 2: 前端辅助功能（3任务）

### 2.1 Dashboard 待办卡片

**文件**: `packages/ui/src/pages/Dashboard.tsx`

**内容**:
- 新增"待我处理"统计卡片区域
- 三个小卡片: 待裁决/待审批/待协助（数字 + 跳转链接）
- 最近动态列表（滚动显示最近 5 条）
- 每 30 秒轮询刷新

**验收标准**:
- [ ] Dashboard 显示待办卡片，数字正确
- [ ] 点击"查看" → 跳转到 /rulings 对应 Tab
- [ ] 数字实时更新（轮询）

### 2.2 侧边栏铃铛

**文件**: `packages/ui/src/components/Sidebar.tsx`

**内容**:
- 铃铛图标 + 数字 badge
- 点击展开下拉面板（列出待处理项）
- 每 30 秒轮询 `GET /human-review/stats`
- 数字变化时动画

**验收标准**:
- [ ] 侧边栏显示铃铛图标 + 正确数字
- [ ] 点击展开下拉面板
- [ ] 点击待处理项 → 跳转到对应页面

### 2.3 HumanInputPage 改名

**文件**: `packages/ui/src/pages/HumanInputPage.tsx`

**内容**:
- 页面标题 "人类输入" → "人工协助"
- 文案中所有 "人类" → "人工"
- 路由 /human-input → /human-assist（保留兼容）

**验收标准**:
- [ ] 页面标题显示"人工协助"
- [ ] /human-assist 路由可访问
- [ ] /human-input 重定向到 /human-assist

---

## Phase 3: 通知 + 批量增强（2任务）

### 3.1 disputed 飞书通知

**文件**: `packages/server/src/reins/services/feishu_notification.py`

**内容**:
- 新增 `notify_task_disputed(task_id, cycle, detail)` 函数
- 在 ResultVerifier disputed 分支调用
- 消息包含: 任务标题、验证失败原因、跳转链接

**验收标准**:
- [ ] disputed 任务产生时收到飞书消息
- [ ] 消息包含任务链接
- [ ] 点击链接跳转到 Nexus TaskDetail 页面

### 3.2 批量裁决增强

**文件**: 同 0.2

**内容**:
- 批量裁决支持 human_input 类型
- 批量操作时显示进度条
- 部分失败时显示详细错误

**验收标准**:
- [ ] 批量操作混合类型（disputed + human_input）→ 都成功
- [ ] 进度条显示
- [ ] 部分失败时清晰展示失败原因

---

## Phase 4: E2E 测试（1任务）

### 4.1 完整流程验证

**文件**: `packages/server/temp/test_sprint58.py`

**测试场景**（至少 8 个）:

| # | 场景 | 验证点 |
|---|------|--------|
| 1 | stats API 返回 3 种类型数量 | 数字正确 |
| 2 | pending API 按 type 筛选 | 过滤正确 |
| 3 | 裁决中心页面渲染 | 3 种类型显示 |
| 4 | 快速裁决 disputed | 状态更新为 done |
| 5 | 批量裁决 2 个 disputed | 2 个都 done |
| 6 | TaskDetail 裁决 | comment 写入 + 状态更新 |
| 7 | human_input 详情面板 | 展开不跳转 |
| 8 | Dashboard 卡片跳转 | 到 /rulings 正确 Tab |

**验收标准**:
- [ ] 8 个场景全部通过
- [ ] TypeScript 编译通过（0 errors）
- [ ] 后端重启无错误

---

## Phase 执行顺序

```
Phase 0 (后端 API) ← 必须先做
  ├── 0.1 stats API
  └── 0.2 pending + batch API
        ↓
Phase 1 (前端核心) ← 依赖 Phase 0
  ├── 1.1 裁决中心页面
  └── 1.2 TaskDetail 裁决入口
        ↓
Phase 2 (前端辅助) ← 依赖 Phase 1
  ├── 2.1 Dashboard 卡片
  ├── 2.2 侧边栏铃铛
  └── 2.3 HumanInputPage 改名
        ↓
Phase 3 (通知 + 批量) ← 依赖 Phase 0
  ├── 3.1 disputed 飞书通知
  └── 3.2 批量裁决增强
        ↓
Phase 4 (E2E 测试) ← 依赖所有
  └── 4.1 完整流程验证
```

## 任务汇总表

| Phase | 任务数 | 预估工作量 |
|-------|--------|-----------|
| Phase 0 | 2 | 中 |
| Phase 1 | 2 | 大 |
| Phase 2 | 3 | 中 |
| Phase 3 | 2 | 小 |
| Phase 4 | 1 | 小 |
| **总计** | **10** | — |

## 全局验收标准

1. ✅ 三种类型在裁决中心统一展示
2. ✅ 快速裁决/批量操作在列表内完成
3. ✅ TaskDetail 裁决通过 comment 完成
4. ✅ Dashboard 显示待办统计
5. ✅ 侧边栏铃铛实时更新
6. ✅ 飞书通知（辅助）
7. ✅ TypeScript 编译通过
8. ✅ E2E 测试 8/8 通过
9. ✅ 系统内自我闭环（不依赖外部系统也能完成所有操作）
