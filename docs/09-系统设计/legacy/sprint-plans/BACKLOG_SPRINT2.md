# Sprint 2 Backlog：功能替代 Paperclip

## 目标
实现完整的任务管理能力：目标管理、项目管理、任务管理、状态管理 + Agent上下文注入 + Agent连接（注册/心跳/生命周期）

## 目标管理 (Goal Management)

- [ ] SP2-01: Goal 数据模型设计
- [ ] SP2-02: Goal CRUD API
- [ ] SP2-03: Goal 状态机（draft → active → completed → archived）
- [ ] SP2-04: Goal 优先级和截止日期

## 项目管理 (Project Management)

- [ ] SP2-05: Project 数据模型设计
- [ ] SP2-06: Project CRUD API
- [ ] SP2-07: Project-Goal 关联
- [ ] SP2-08: Project 成员管理

## 任务管理 (Task Management)

- [ ] SP2-09: Task 数据模型设计（增强版，替代 issues 表）
- [ ] SP2-10: Task CRUD API
- [ ] SP2-11: Task 状态机（todo → in_progress → done / blocked / paused）
- [ ] SP2-12: Task 优先级和分类
- [ ] SP2-13: Task 依赖关系（DAG）
- [ ] SP2-14: Subtask 管理和父子关系

## Agent 上下文注入

- [ ] SP2-15: Agent 上下文注入服务
- [ ] SP2-16: 基于任务状态的动态上下文
- [ ] SP2-17: 上下文缓存和失效策略

## Agent 连接（注册/心跳/生命周期）

- [ ] SP2-18: Agent 注册 API
- [ ] SP2-19: Agent 心跳机制
- [ ] SP2-20: Agent 生命周期管理（在线/离线/超时检测）
- [ ] SP2-21: Agent 能力画像上报

## 状态管理和追踪

- [ ] SP2-22: 任务状态变更事件
- [ ] SP2-23: 执行日志增强（关联 task_id, agent_id）
- [ ] SP2-24: 状态快照和历史回溯

---

## 技术约束
- 不得使用 Mock，必须是真实数据库（SQLite 开发 + PostgreSQL 生产）
- 遵循 Sprint 1 的架构设计
- API 需通过交叉审查
