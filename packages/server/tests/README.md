# 测试代码结构

> 按照《测试用例总览》文档（`docs/09-系统设计/25-测试用例总览.md`）的 L1-L4 层级组织。

## 目录结构

```
tests/
├── conftest.py                      # 根级 fixtures（mock nexus、path setup）
│
├── unit/                            # L1 单元测试 — 隔离测试单个函数/类/模块
│   ├── reins/                       # L1-01 状态机/命令/事件/SSE
│   │   ├── test_goal_statemachine.py
│   │   ├── test_state_machine.py
│   │   ├── test_state_machine_new.py
│   │   ├── test_command.py
│   │   ├── test_events.py
│   │   ├── test_event_bus.py
│   │   └── test_sse_events.py
│   ├── grasp/
│   │   └── parsers/                 # L1-02 GrASP 解析器
│   │       ├── conftest.py
│   │       ├── test_base.py
│   │       ├── test_import.py
│   │       ├── test_md_parser.py
│   │       └── test_registry.py
│   └── vigil/                       # L1-05 Vigil 熔断/降级
│       ├── test_circuit_breaker.py
│       ├── test_fallback.py
│       ├── test_graceful_fallback.py
│       └── test_vigil.py
│
├── integration/                     # L2 集成测试 — 多模块/多组件协作
│   ├── reins/                       # L2-01 Reins 调度/任务/工作流
│   │   ├── test_agent_sdk.py
│   │   ├── test_assignment.py
│   │   ├── test_context_injector.py
│   │   ├── test_context_md_lifecycle.py
│   │   ├── test_goal_decomposition.py
│   │   ├── test_goals_query.py
│   │   ├── test_load_manager.py
│   │   ├── test_p508_trace_enhancement.py
│   │   ├── test_plan_recommendation.py
│   │   ├── test_reins_task_manager.py
│   │   ├── test_result_recycle.py
│   │   ├── test_sprint5_batch2.py
│   │   └── test_workflow_engine.py
│   ├── grasp/                       # L2-02 GrASP 认知/分析
│   │   ├── test_analysis.py
│   │   ├── test_facade_exception_wrapping.py
│   │   ├── test_grasp.py
│   │   ├── test_grasp_degradation.py
│   │   ├── test_inject_business.py
│   │   └── test_knowledge_injection.py
│   ├── reach/                       # L2-03 Reach 场景反馈
│   │   └── test_scenario_feedback.py
│   ├── evo/                         # L2-04 Evo 进化
│   │   ├── test_correction_engine.py
│   │   └── test_evo.py
│   └── shared/                      # L2-06 Shared 工具
│       ├── test_compatibility.py
│       └── test_logging.py
│
├── api/                             # L3 API 测试 — 端点级 HTTP 测试
│   ├── goals/                       # L3-01 Goals API
│   │   └── test_goals_api.py
│   ├── grasp/                       # L3-04 GrASP API
│   │   ├── test_cognition_crud.py
│   │   ├── test_inject_api.py
│   │   └── test_plans_api.py
│   ├── performance/                 # L3-07 性能测试
│   │   └── test_performance.py
│   ├── projects/                    # L3-03 Projects API
│   │   ├── test_project_api.py
│   │   └── test_projects_api.py
│   ├── reach/                       # L3-05 Reach API
│   │   └── test_scenarios_api.py
│   ├── reins/                       # L3-08 Reins 通用 API
│   │   ├── test_api_direct.py
│   │   └── test_api_with_lifespan.py
│   ├── rulings/                     # L3-09 裁决 API
│   │   ├── test_human_ruling_disputed_state.py
│   │   ├── test_human_ruling_goal_*.py  (10 files)
│   ├── security/                    # L3-10 Vigil 安全 (Auth)
│   │   ├── test_auth.py
│   │   ├── test_auth_lifecycle.py
│   │   ├── test_auth_models.py
│   │   └── test_auth_service.py
│   ├── tasks/                       # L3-02 Task API + Verifier
│   │   ├── test_task_without_acceptance_criteria.py
│   │   ├── test_task_with_invalid_api_endpoint_goal_*.py  (2 files)
│   │   ├── test_verifier_inheritance_chain.py
│   │   ├── test_verifier_inheritance_validation.py
│   │   └── test_verifier_inheritance_validation_fixed.py
│   └── vigil/                       # L3-06 Vigil 搜索
│       └── test_global_search.py
│
└── e2e/                             # L4 E2E 测试 — 全流程端到端
    ├── agents/                      # L4-05 Agent 生命周期
    │   └── test_agent_lifecycle_e2e.py
    ├── config/                      # L4-14 系统配置
    │   └── test_config_e2e.py
    ├── cross_domain/                # L4-13 跨域集成
    │   └── test_cross_domain_e2e.py
    ├── dashboard/                   # L4-11 Dashboard 与可视化
    │   └── test_dashboard_e2e.py
    ├── evo/                         # L4-09 进化域
    │   └── test_evo_e2e.py
    ├── goals/                       # L4-01 Goal 全生命周期
    │   ├── test_e2e.py
    │   └── test_phase3_e2e.py
    ├── grasp/                       # L4-06 认知域
    │   └── test_grasp_e2e.py
    ├── hitl/                        # L4-03 人工审核
    │   ├── test_e2e_human_review.py
    │   └── test_human_input_integration.py
    ├── projects/                    # L4-04 Project 管理
    │   └── test_project_e2e.py
    ├── reach/                       # L4-08 拓展域
    │   └── test_reach_e2e.py
    ├── reins/                       # L4 其他 Reins 全流程
    │   └── test_reins.py
    ├── solutions/                   # L4-07 解决方案
    │   └── test_solutions_e2e.py
    ├── tasks/                       # L4-02 Task 全生命周期
    │   ├── test_e2e_verification_cycle.py
    │   └── test_e2e_verification_goal_7c93b8c64c07.py
    └── vigil/                       # L4-10 安全域
        └── test_vigil_e2e.py
```

## 统计

| 级别 | 目录 | 文件数 | 测试函数 | 说明 |
|------|------|--------|---------|------|
| L1 | `unit/` | 19 | 37 | 纯单元测试，无外部依赖 |
| L2 | `integration/` | 30 | 155 | 模块间集成，DB/LLM mock |
| L3 | `api/` | 43 | 94 | HTTP 端点测试 |
| L4 | `e2e/` | 17 | 274 | 端到端全流程 |
| **总计** | | **109** | **560** | |

> 注：58 个收集错误均为预存在的导入路径过期问题（如 `reins.engine` → `reins.core.engine`），非重组导致。

## 运行方式

```bash
# 运行全部测试
pytest packages/server/tests/

# 按级别运行
pytest packages/server/tests/unit/          # L1 单元测试
pytest packages/server/tests/integration/   # L2 集成测试
pytest packages/server/tests/api/           # L3 API 测试
pytest packages/server/tests/e2e/           # L4 E2E 测试

# 按领域运行
pytest packages/server/tests/unit/reins/    # Reins 域单元测试
pytest packages/server/tests/api/goals/     # Goals API 测试
pytest packages/server/tests/e2e/goals/     # Goal E2E 测试
```
