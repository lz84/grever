# Workflow DAG 编辑详细设计

**版本**: v1.0
**作者**: 扣子
**日期**: 2026-05-28
**状态**: 草稿
**关联需求**: Nexus-Reins Workflow 编辑
**变更记录**:
- v1.0 2026-05-28 扣子 初始版本

---

## 1. 概述

### 1.1 设计目标

Nexus Workflow DAG 编辑模块是 Reins（御）系统的核心编辑组件，支持对工作流（Workflow）的有向无环图进行动态编辑。核心设计原则为 **原子化操作**：每个编辑操作都是独立的，支持节点和边的增删改查。

### 1.2 核心职责

| 职责 | 说明 |
|------|------|
| 节点管理 | 添加/更新/删除工作流节点 |
| 边管理 | 添加/删除节点间的依赖关系 |
| 重排 | 调整节点的执行顺序 |
| 原子编辑 | 统一的 DAG 编辑接口 |
| 状态同步 | 编辑后同步更新数据库 |

---

## 2. 核心流程

### 2.1 节点编辑流程

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           节点编辑流程                                         │
└──────────────────────────────────────────────────────────────────────────────┘

Case 1: 添加节点
  POST /api/v1/workflows/{id}/dag/nodes
  → 分配新节点 ID
  → 设置节点属性（name, description, node_type）
  → 设置依赖关系
  → 插入到执行顺序
         │
Case 2: 更新节点
  PATCH /api/v1/workflows/{id}/dag/nodes/{node_id}
  → 更新节点属性
  → 同步数据库
         │
Case 3: 删除节点
  DELETE /api/v1/workflows/{id}/dag/nodes/{node_id}
  → 从 DAG 中移除
  → 清理对该节点的依赖引用
  → 调整后续节点顺序
```

### 2.2 边编辑流程

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           边编辑流程                                           │
└──────────────────────────────────────────────────────────────────────────────┘

Case 1: 添加边
  POST /api/v1/workflows/{id}/dag/edges
  source ──▶ target
  → 验证 source 和 target 存在
  → 检测是否形成循环依赖
  → 添加边到 dependencies
         │
Case 2: 删除边
  DELETE /api/v1/workflows/{id}/dag/edges/{source}/{target}
  → 从 dependencies 中移除
  → 调整下游节点状态
```

### 2.3 重排流程

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           重排流程                                            │
└──────────────────────────────────────────────────────────────────────────────┘

POST /api/v1/workflows/{id}/dag/reorder
  {node_ids: ["n1", "n2", "n3"]}
         │
         ▼
  按新顺序重新分配 order
  → n1.order = 1
  → n2.order = 2
  → n3.order = 3
         │
         ▼
  同步到数据库
```

---

## 3. 数据模型

### 3.1 请求模型

```python
class AddNodeRequest(BaseModel):
    title: str                          # 节点标题
    description: Optional[str] = ""     # 描述
    node_type: str = "execution"        # 节点类型
    dependencies: List[str] = []       # 依赖节点 ID 列表
    assignee: Optional[str] = None      # 分配者

class UpdateNodeRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    node_type: Optional[str] = None
    assignee: Optional[str] = None

class AddEdgeRequest(BaseModel):
    source: str                         # 源节点 ID
    target: str                         # 目标节点 ID
    label: Optional[str] = None         # 边标签

class ReorderRequest(BaseModel):
    node_ids: List[str]                 # 新顺序的节点 ID 列表

class EditActionRequest(BaseModel):
    action: str                         # 操作类型
    node: Optional[Dict[str, Any]] = None
    node_id: Optional[str] = None
    updates: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    target: Optional[str] = None
```

### 3.2 响应模型

```python
class DagEditResponse(BaseModel):
    workflow_id: str                    # 工作流 ID
    name: str                           # 工作流名称
    status: str                         # 工作流状态
    dag: Dict[str, Any]                 # DAG 结构
    steps_synced: int = 0               # 同步的步骤数
```

---

## 4. 操作类型

### 4.1 支持的操作

| action | 说明 | 参数 |
|--------|------|------|
| `add_node` | 添加节点 | node |
| `update_node` | 更新节点 | node_id, updates |
| `delete_node` | 删除节点 | node_id |
| `add_edge` | 添加边 | source, target |
| `delete_edge` | 删除边 | source, target |
| `reorder` | 重排节点 | node_ids |

### 4.2 节点类型

| node_type | 说明 |
|-----------|------|
| `execution` | 执行节点（默认） |
| `condition` | 条件节点 |
| `parallel` | 并行执行节点 |
| `merge` | 合并节点 |

---

## 5. 关键函数签名

### 5.1 工作流编辑逻辑

```python
# reins/api/workflow_edit_logic.py

class WorkflowEditLogic:
    """Workflow DAG 编辑逻辑"""
    
    def edit_workflow_dag(self, workflow_id: str, req: EditActionRequest) -> dict:
        """
        DAG 统一编辑接口
        
        根据 action 调用对应的处理方法
        """
    
    def add_workflow_node(self, workflow_id: str, req: AddNodeRequest) -> dict:
        """添加节点"""
    
    def update_workflow_node(self, workflow_id: str, node_id: str, 
                           req: UpdateNodeRequest) -> dict:
        """更新节点属性"""
    
    def delete_workflow_node(self, workflow_id: str, node_id: str) -> dict:
        """删除节点"""
    
    def add_workflow_edge(self, workflow_id: str, req: AddEdgeRequest) -> dict:
        """添加边"""
    
    def delete_workflow_edge(self, workflow_id: str, source: str, 
                           target: str) -> dict:
        """删除边"""
    
    def reorder_workflow_nodes(self, workflow_id: str, 
                             req: ReorderRequest) -> dict:
        """重排节点顺序"""
```

### 5.2 DAG 操作

```python
# reins/api/workflow_edit.py

@router.patch("/api/v1/workflows/{workflow_id}/dag")
def edit_workflow_dag(workflow_id: str, req: EditActionRequest):
    """Workflow DAG 统一编辑接口"""

@router.post("/api/v1/workflows/{workflow_id}/dag/nodes")
def add_workflow_node(workflow_id: str, req: AddNodeRequest):
    """添加 Workflow 节点"""

@router.patch("/api/v1/workflows/{workflow_id}/dag/nodes/{node_id}")
def update_workflow_node(workflow_id: str, node_id: str, req: UpdateNodeRequest):
    """更新 Workflow 节点属性"""

@router.delete("/api/v1/workflows/{workflow_id}/dag/nodes/{node_id}")
def delete_workflow_node(workflow_id: str, node_id: str):
    """删除 Workflow 节点"""

@router.post("/api/v1/workflows/{workflow_id}/dag/edges")
def add_workflow_edge(workflow_id: str, req: AddEdgeRequest):
    """添加 Workflow 边"""

@router.delete("/api/v1/workflows/{workflow_id}/dag/edges/{source}/{target}")
def delete_workflow_edge(workflow_id: str, source: str, target: str):
    """删除 Workflow 边"""

@router.post("/api/v1/workflows/{workflow_id}/dag/reorder")
def reorder_workflow_nodes(workflow_id: str, req: ReorderRequest):
    """重排 Workflow 节点顺序"""
```

---

## 6. 接口清单

### 6.1 DAG 编辑接口

| 方法 | 路径 | 说明 |
|------|------|------|
| PATCH | /api/v1/workflows/{id}/dag | 统一编辑 |
| POST | /api/v1/workflows/{id}/dag/nodes | 添加节点 |
| PATCH | /api/v1/workflows/{id}/dag/nodes/{node_id} | 更新节点 |
| DELETE | /api/v1/workflows/{id}/dag/nodes/{node_id} | 删除节点 |
| POST | /api/v1/workflows/{id}/dag/edges | 添加边 |
| DELETE | /api/v1/workflows/{id}/dag/edges/{source}/{target} | 删除边 |
| POST | /api/v1/workflows/{id}/dag/reorder | 重排节点 |

---

## 7. 错误处理

### 7.1 错误类型

| 错误类型 | 说明 | 处理方式 |
|---------|------|----------|
| `WorkflowNotFoundError` | 工作流不存在 | 返回 404 |
| `NodeNotFoundError` | 节点不存在 | 返回 404 |
| `CircularDependencyError` | 循环依赖 | 返回 400 |
| `InvalidOperationError` | 无效操作 | 返回 400 |

### 7.2 验证规则

```python
# 工作流存在验证
workflow = workflow_repo.get(workflow_id)
if not workflow:
    raise HTTPException(status_code=404, 
                        detail=f"Workflow {workflow_id} not found")

# 节点存在验证
node = step_repo.get(node_id)
if not node:
    raise HTTPException(status_code=404,
                        detail=f"Node {node_id} not found")

# 循环依赖检测
if would_create_cycle(dag, source, target):
    raise HTTPException(status_code=400,
                        detail="Cannot add edge: would create circular dependency")

# 边已存在检测
if edge_exists(source, target):
    raise HTTPException(status_code=400,
                        detail="Edge already exists")
```

---

## 8. 与其他模块的关系

### 8.1 与 WorkflowEngine 模块

- DAG 编辑后需要同步到执行引擎
- 编辑操作在运行时可能被限制
- 删除节点需要更新执行状态

### 8.2 与 WorkflowExecutionEngine 模块

- 动态添加节点调用 `add_step()`
- 运行时编辑需要暂停执行
- 节点顺序影响并行分组

### 8.3 与 Scheduler 模块

- Workflow 完成状态影响调度
- 节点执行受调度器管理

---

*文档完成 — 2026-05-28*