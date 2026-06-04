# GrASP 迭代计划（2026-05-28）

## 当前状态

| 组件 | 状态 | 备注 |
|------|------|------|
| GraspFacade v3.1 | ✅ 完成 | LRU缓存/幂等/并发安全/domain校验 |
| MemoryAdapter | ✅ 完成 | 关键词检索，零成本 |
| GraspFacade API | ✅ 完成 | inject/retrieve/update/delete/backends/switch-backend |
| GraspRoutes | ✅ 完成 | `/api/v1/grasp/*` |
| DB 迁移 018 | ✅ 完成 | cognition_backend_map + content_hash |
| Phase 1a 完成时间 | 2026-05-28 | |

---

## Phase 1b — GraphRAG 适配器（1-2周）

### 目标
实现 Microsoft GraphRAG 适配器，具备生产级成本控制和降级策略。

### 任务

#### 1b-1：GraphRAGAdapter 骨架
- `grasp/adapters/graphrag.py`
- 实现 BaseGraspAdapter 全部抽象方法
- inject → 调用 LLM 提取实体+关系 → build_index
- retrieve → `global_search` / `local_search`
- 适配 Microsoft GraphRAG SDK

#### 1b-2：成本控制机制（P1-2）
- **批量窗口**：inject 后 5 分钟攒一批再 build_index，减少 LLM 调用次数
- **每日成本上限**：加告警阈值（如每天 $10），超了自动暂停 inject
- **小内容跳过**：内容 < 500 字不走 GraphRAG，走 MemoryAdapter

#### 1b-3：降级策略（P1-3）
- **健康检查定时任务**：每 60 秒检查 GraphRAG 服务可用性
- **自动降级**：GraphRAG 不可用时自动切换到 MemoryAdapter 并告警
- **恢复检测**：GraphRAG 恢复后自动切回

#### 1b-4：统一异常包装（P1-1）
- facade 层统一 catch 适配器异常
- 转成 NexusException（带 ErrorCode.GRASP_BACKEND_UNAVAILABLE 等）

### Done Criteria
- [ ] GraphRAGAdapter.inject() 能实际调用 GraphRAG CLI/API
- [ ] 成本窗口机制：批量 inject 后批量 build
- [ ] 降级：GraphRAG 不可用时自动切到 Memory
- [ ] API 验证：`POST /api/v1/grasp/inject` → GraphRAG 成功
- [ ] 成本告警触发（模拟超限场景）

---

## Phase 2 — API 路由切换（1周）

### 目标
将所有 `/api/v1/grasp/*` 路由从 GraspService 切换到 GraspFacade，删除旧实现。

### 任务

#### 2-1：路由切换
- 改造 `grasp/api/grasp_routes.py` → 底层调用 GraspFacade
- 验证新旧行为一致（无破坏性变更）
- 加 `/api/v1/grasp/status` → 返回当前 backend 状态

#### 2-2：旧代码清理
- 删除 `grasp/common/service.py`（旧的 GraspService）
- 删除 `grasp/common/graphrag_adapter.py`（旧的 GraspGraphRAGAdapter）
- 确认无残留引用

#### 2-3：E2E 验证
- 场景：inject → retrieve → update → delete 全流程跑通
- 验证 domain 路由对称性

### Done Criteria
- [ ] 所有 GrASP API 走 GraspFacade
- [ ] E2E 流程跑通
- [ ] 旧 GraspService 代码已删除
- [ ] 文档更新

---

## Phase 3 — 多后端扩展（2-3周，可选）

### 目标
支持 LlamaIndex 和 Neo4j 作为知识存储后端。

#### LlamaIndexAdapter
- 适合 POC 验证
- 支持向量检索

#### Neo4jAdapter
- 知识图谱存储
- Cypher 查询
- 需要独立部署 Neo4j

---

## 技术债务

| 债务项 | 优先级 | 备注 |
|--------|--------|------|
| P1-4: retrieve 分页性能 | P1 | 当前是客户端分页，应改为服务端 |
| P1-5: filters 能力校验 | P1 | 适配器声明支持的能力，facade 做校验 |
| P1-6: 观测性（metrics） | P2 | Phase 1 骨架不急 |
| P2-2: 批量 inject 接口 | P2 | 后续优化 |
| P2-4: mode 参数枚举 | P2 | local/global/drift/basic 枚举限制 |

---

## Sprint 拆分建议

| Sprint | 内容 | 周期 |
|--------|------|------|
| Sprint 101 | Phase 1b-1 GraphRAGAdapter 骨架 | 3-4天 |
| Sprint 102 | Phase 1b-2+1b-3 成本控制+降级 | 3-4天 |
| Sprint 103 | Phase 1b-4 异常包装+1b-2 收尾 | 2-3天 |
| Sprint 104 | Phase 2 路由切换 | 3-4天 |
| Sprint 105 | Phase 2 E2E+旧代码清理 | 2-3天 |

---

## 资源估算

- **Phase 1b**：约 1-2 周（GraphRAG 有开源 SDK，难度中等）
- **Phase 2**：约 1 周（主要是路由切换和测试）
- **Phase 3**：约 2-3 周（可选，取决于是否上 Neo4j）

---

## 风险

1. **GraphRAG 成本**：每次 inject 调 LLM，需要严格控制成本上限
2. **LLM API 依赖**：GraphRAG 依赖 LLM API 可用性，需要降级兜底
3. **性能**：GraphRAG index 构建慢，批量窗口可能导致认知延迟写入
