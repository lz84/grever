# Sprint 1 Backlog：打通端到端链路

## 持久化层

- [x] SP1-01: 接入 SQLite 数据库（开发环境）
- [x] SP1-02: 设计 Grasp 认知表（cognitions）
- [x] SP1-03: 设计 Reins 任务表（tasks, subtasks）
- [x] SP1-04: 设计执行日志表（execution_logs）
- [x] SP1-05: 编写 Alembic 迁移脚本

## Reins Server

- [x] SP1-06: 工作流引擎 - 任务状态机
- [x] SP1-07: 工作流引擎 - 依赖 DAG 调度
- [x] SP1-08: 工作流引擎 - 并行任务管理
- [x] SP1-09: 上下文注入 - 运行时查 Grasp
- [x] SP1-10: 上下文注入 - 缓存优化
- [x] SP1-11: 执行追踪 - 任务日志
- [x] SP1-12: 执行追踪 - 执行报告

## Grasp

- [x] SP1-13: GraphRAG 索引优化
  - ✅ `src/grasp/graphrag_adapter.py` 增加增量索引支持 (`inject` 方法添加 `use_incremental` 参数)
  - ✅ `src/grasp/graphrag_adapter.py` 新增 `build_index_from_documents` 批量索引方法
  - ✅ `src/grasp/graphrag_adapter.py` 新增 `cold_start_index` 冷启动方法
  - ✅ `scripts/cold_start_index.py` 冷启动脚本
- [x] SP1-14: 认知回流闭环
  - ✅ `src/grasp/service.py` 增加 `update_from_task_result(result)` 方法
  - ✅ `src/grasp/service.py` 新增 `_auto_detect_cognition_type` 自动判断认知类型（fact/pattern/lesson/meta）
  - ✅ `src/grasp/service.py` 新增 `_generate_cognition_content_from_result` 内容生成方法
  - ✅ `src/grasp/service.py` 新增 `_extract_tags_from_result` 标签提取方法
