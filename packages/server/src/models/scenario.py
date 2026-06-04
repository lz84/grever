"""
场景库数据模型

MAK-189: 场景库模型定义
"""

import uuid
from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import Column, String, Integer, Text, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, ConfigDict

from .base import Base

class ScenarioStatus(str):
    """场景状态"""
    ACTIVE = 'active'
    ARCHIVED = 'archived'
    DRAFT = 'draft'

class ScenarioCategory(str):
    """场景分类"""
    EARTHQUAKE = 'earthquake'
    FIRE = 'fire'
    CHEMICAL = 'chemical'
    FLOOD = 'flood'
    GENERAL = 'general'

class ScenarioSource(str):
    """
    场景来源枚举
    
    Task 2: 扩展 source 字段枚举值
    - manual: 手动创建
    - ai_generated: AI 生成
    - execution_flowback: 执行回流（原 execution_derived）
    - cognitive_derived: 从认知推导
    - execution_derived: 从执行记录推导
    - template: 从模板创建
    - evolved: 自动演化优化
    """
    MANUAL = 'manual'
    AI_GENERATED = 'ai_generated'
    EXECUTION_FLOWBACK = 'execution_flowback'
    COGNITIVE_DERIVED = 'cognitive_derived'
    EXECUTION_DERIVED = 'execution_derived'
    TEMPLATE = 'template'
    EVOLVED = 'evolved'

# ========== Pydantic 模型 ==========

class ScenarioStep(BaseModel):
    """协作步骤（别名，兼容旧代码）"""
    order: int
    name: str
    agent_type: Optional[str] = None
    required_capabilities: Optional[List[str]] = None

class ScenarioProjectTask(BaseModel):
    """场景项目内的任务"""
    id: str
    name: str
    description: Optional[str] = None
    agent_type: Optional[str] = None
    required_capabilities: Optional[Any] = None
    dependencies: Optional[Any] = None
    order_in_phase: int = 0
    estimated_hours: Optional[float] = None
    priority: str = 'medium'
    condition_type: str = 'none'
    condition_data: Optional[str] = None
    executor_type: str = 'ai'

class ScenarioProject(BaseModel):
    """场景项目（即步骤 + 关联任务）"""
    id: str
    name: str
    description: Optional[str] = None
    order: int
    agent_type: Optional[str] = None
    required_capabilities: Optional[Any] = None
    condition_type: str = 'none'
    condition_data: Optional[Any] = None
    project_type: str = 'mandatory'  # Sprint 85a: mandatory/conditional
    capability_tags: Optional[Any] = None  # Sprint 85a: JSON object
    next_step: Optional[Any] = None  # Sprint 85a: JSON array
    tasks: List[ScenarioProjectTask] = []

class ScenarioMetrics(BaseModel):
    """数据背书"""
    total_executions: int = 0
    success_count: int = 0
    failed_count: int = 0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    avg_conflicts: float = 0.0
    avg_step_completion: float = 0.0

class ScenarioCreate(BaseModel):
    """创建工作场景请求"""
    name: str
    category: str
    status: str = 'draft'
    version: str = 'v1.0'
    description: Optional[str] = None
    scenario_desc: str = ""
    triggers: Optional[List[str]] = None
    steps: Optional[List[dict]] = None

    model_config = ConfigDict(from_attributes=True)

class ScenarioUpdate(BaseModel):
    """更新场景请求"""
    name: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    scenario_desc: Optional[str] = None
    triggers: Optional[List[str]] = None
    steps: Optional[List[dict]] = None
    projects: Optional[List[dict]] = None  # Sprint 85b
    fullset: Optional[dict] = None  # Sprint 85b
    goal_capability_tags: Optional[dict] = None  # Sprint 85a

    model_config = ConfigDict(from_attributes=True)

class ScenarioSummary(BaseModel):
    """场景列表项"""
    id: str
    name: str
    category: str
    status: str
    version: str
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    usage_count: int = 0
    scenario_desc: str = ""
    project_count: int = 0  # Sprint 85b: 项目数
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ScenarioResponse(BaseModel):
    """场景详情响应"""
    id: str
    name: str
    category: str
    status: str
    version: str
    description: Optional[str] = None
    scenario_desc: str = ""
    triggers: List[str] = []
    steps: List[ScenarioStep] = []
    # Sprint 85a-2: projects array (step + embedded tasks)
    projects: List[ScenarioProject] = []
    metrics: ScenarioMetrics = None
    versions: Optional[List[Any]] = []
    # Task 5: task_templates from scenario_tasks table
    task_templates: Optional[List[Any]] = []
    # Extra fields from extended scenario model
    level: Optional[str] = None
    trust_level: Optional[str] = None
    source: Optional[str] = None
    template_dag: Optional[Any] = None
    fullset: Optional[Any] = None
    goal_capability_tags: Optional[Any] = None  # Sprint 85a
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class FeedbackRequest(BaseModel):
    """反馈请求"""
    workflow_id: str
    status: str  # 'completed' or 'failed'
    duration_ms: Optional[float] = None
    steps_completed: int = 0
    steps_total: int = 0
    conflicts_count: int = 0
    user_modifications: Optional[List[dict]] = None

class FeedbackResponse(BaseModel):
    """反馈响应"""
    success: bool = True
    new_version_suggested: bool = False
    updated_metrics: Optional[ScenarioMetrics] = None
    message: Optional[str] = None

# ========== Task 5: 自定义场景创建 API（三层结构） ==========

class TaskTemplateInput(BaseModel):
    """任务模板输入"""
    name: str
    description: Optional[str] = None
    agent_type: Optional[str] = None
    required_capabilities: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    estimated_hours: Optional[float] = None
    priority: Optional[str] = 'medium'
    node_type: Optional[str] = 'step'
    children: Optional[List[str]] = None
    condition_type: Optional[str] = 'none'
    condition_data: Optional[dict] = None
    then_node: Optional[str] = None
    else_node: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class PhaseInput(BaseModel):
    """阶段输入"""
    phase_name: str
    phase_description: Optional[str] = None
    tasks: List[TaskTemplateInput] = []
    depends_on_phases: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)

class ProjectWorkflowInput(BaseModel):
    """项目工作流输入"""
    workflow_name: Optional[str] = None
    description: Optional[str] = None
    phases: List[PhaseInput] = []

    model_config = ConfigDict(from_attributes=True)

class BasicScenarioInput(BaseModel):
    """基础场景信息"""
    name: str
    category: str = 'general'
    description: Optional[str] = None
    scenario_desc: Optional[str] = None
    triggers: Optional[List[str]] = None
    status: Optional[str] = 'draft'
    version: Optional[str] = 'v1.0'
    source: Optional[str] = 'manual'

    model_config = ConfigDict(from_attributes=True)

class CustomScenarioCreateRequest(BaseModel):
    """自定义场景创建请求（三层结构）"""
    basic: BasicScenarioInput
    project_workflow: ProjectWorkflowInput
    task_templates: Optional[List[TaskTemplateInput]] = None
    strict_mode: Optional[bool] = False  # Sprint 98 B98-5: 前置标签校验模式

    model_config = ConfigDict(from_attributes=True)

class TaskTemplateResponse(BaseModel):
    """任务模板响应"""
    id: str
    scenario_id: str
    phase_name: str
    name: str
    description: Optional[str] = None
    agent_type: Optional[str] = None
    required_capabilities: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    order_in_phase: int = 0
    estimated_hours: Optional[float] = None
    priority: str = 'medium'
    condition_type: str = 'none'
    condition_data: Optional[str] = None
    executor_type: str = 'ai'
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CustomScenarioCreateResponse(BaseModel):
    """自定义场景创建响应"""
    id: str
    name: str
    category: str
    status: str
    version: str
    description: Optional[str] = None
    scenario_desc: Optional[str] = None
    template_dag: Optional[dict] = None
    phases: List[dict] = []
    task_templates: List[TaskTemplateResponse] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    # Sprint 98 B98-5: 前置标签校验增强
    warnings: Optional[List[dict]] = None
    auto_added_tags: Optional[List[str]] = None
    auto_added_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# ========== SQLAlchemy ORM 模型 ==========

def _generate_id():
    return f"scenario-{uuid.uuid4().hex[:12]}"

class Scenario(Base):
    """场景表"""
    __tablename__ = 'scenarios'

    id = Column(String(36), primary_key=True, default=_generate_id)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, index=True)  # earthquake, fire, chemical, flood, general
    status = Column(String(50), default='draft', index=True)  # active, archived, draft
    version = Column(String(20), default='v1.0')
    description = Column(Text, nullable=True)
    scenario_desc = Column(Text, default="")  # 适用场景描述
    triggers = Column(JSON, nullable=True)  # 触发条件列表
    
    # 统计数据
    total_executions = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    avg_duration_ms = Column(Float, default=0.0)
    min_duration_ms = Column(Float, default=0.0)
    max_duration_ms = Column(Float, default=0.0)
    avg_conflicts = Column(Float, default=0.0)
    avg_step_completion = Column(Float, default=0.0)
    usage_count = Column(Integer, default=0)
    
    versions = Column(JSON, nullable=True)  # 版本号列表 ["v1.0", "v1.1", ...]
    execution_log = Column(JSON, nullable=True)  # MAK-228: 执行日志
    template_dag = Column(JSON, nullable=True)  # Sprint 22: 模板 DAG
    agent_requirements = Column(JSON, nullable=True)  # Sprint 22: Agent 要求
    trust_level = Column(Float, nullable=True)  # Sprint 22: 信任等级
    source = Column(String(50), nullable=True)  # Sprint 22: 来源
    # Capability tag system: 场景全集
    fullset = Column(JSON, nullable=True)  # JSON object: {goal_tags:{}, projects:[{capability_tags:{}, tasks:[]...}]}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    # steps = relationship('ScenarioStepModel', back_populates='scenario', cascade='all, delete-orphan')  # DROPPED: scenario_steps table removed
    projects = relationship('ScenarioProjectModel', back_populates='scenario', cascade='all, delete-orphan', order_by='ScenarioProjectModel.order_index')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'status': self.status,
            'version': self.version,
            'description': self.description,
            'scenario_desc': self.scenario_desc,
            'triggers': self.triggers,
            'total_executions': self.total_executions,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'success_rate': self.success_rate,
            'avg_duration_ms': self.avg_duration_ms,
            'min_duration_ms': self.min_duration_ms,
            'max_duration_ms': self.max_duration_ms,
            'avg_conflicts': self.avg_conflicts,
            'avg_step_completion': self.avg_step_completion,
            'usage_count': self.usage_count,
            'versions': self.versions,
            'template_dag': getattr(self, 'template_dag', None),
            'agent_requirements': getattr(self, 'agent_requirements', None),
            'trust_level': getattr(self, 'trust_level', None),
            'source': getattr(self, 'source', None),
            'fullset': getattr(self, 'fullset', None),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

# DROPPED: scenario_steps table removed, class kept for reference only
# class ScenarioStepModel(Base):
#     """场景步骤表"""
#     __tablename__ = 'scenario_steps'
#     ...

    def to_dict(self):
        return {
            'id': self.id,
            'scenario_id': self.scenario_id,
            'order': self.order,
            'name': self.name,
            'agent_type': self.agent_type,
            'required_capabilities': self.required_capabilities,
            'condition_type': self.condition_type,
            'condition_data': self.condition_data,
        }

class ScenarioStepSchema(BaseModel):
    """场景步骤 Pydantic 模型（给 API 使用）"""
    order: int
    name: str
    agent_type: str
    required_capabilities: Optional[List[str]] = None

# ========== Sprint 85a: Scenario Project 模型 ==========

def _generate_scenario_project_id():
    return f"sp-{uuid.uuid4().hex[:12]}"

class ScenarioProjectModel(Base):
    """
    场景项目表（Sprint 85a 新增）
    替代 scenario_steps 作为 Project 层，对齐 Goal → Projects → Tasks 结构
    """
    __tablename__ = 'scenario_projects'

    id = Column(String(36), primary_key=True, default=_generate_scenario_project_id)
    scenario_id = Column(String(36), ForeignKey('scenarios.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    project_type = Column(String(20), default='mandatory')  # mandatory/conditional
    condition_type = Column(String(20), default='none')  # none/auto_eval/human_decision/human_input
    condition_data = Column(Text, nullable=True)  # JSON
    next_step = Column(Text, nullable=True)  # JSON array of project IDs
    capability_tags = Column(Text, default='{}')  # JSON object
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    scenario = relationship('Scenario', back_populates='projects')

    def to_dict(self):
        return {
            'id': self.id,
            'scenario_id': self.scenario_id,
            'name': self.name,
            'description': self.description,
            'project_type': self.project_type,
            'condition_type': self.condition_type,
            'condition_data': self.condition_data,
            'next_step': self.next_step,
            'capability_tags': self.capability_tags,
            'order_index': self.order_index,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

# ========== Task 5: 场景任务模型 ==========

def _generate_scenario_task_id():
    return f"task-{uuid.uuid4().hex[:12]}"

class ScenarioTask(Base):
    """
    场景任务表
    
    Task 5: 自定义场景创建 API（三层结构）
    存储场景中的任务，支持 phases 分组
    
    原名: ScenarioTaskTemplate (表名: scenario_task_templates)
    迁移: scenario_task_templates → scenario_tasks
    """
    __tablename__ = 'scenario_tasks'

    id = Column(String(36), primary_key=True, default=_generate_scenario_task_id)
    scenario_id = Column(String(36), ForeignKey('scenarios.id'), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey('scenario_projects.id'), nullable=True, index=True)  # Sprint 85a
    phase_name = Column(String(100), nullable=False, index=True)  # 所属阶段名称（兼容旧数据）
    name = Column(String(255), nullable=False)  # 原名: task_name
    description = Column(Text, nullable=True)  # 原名: task_description
    agent_type = Column(String(100), nullable=True)
    required_capabilities = Column(JSON, nullable=True)  # 能力列表
    dependencies = Column(JSON, nullable=True)  # 依赖的任务 ID 列表
    order_in_phase = Column(Integer, default=0)  # 在阶段内的顺序
    estimated_hours = Column(Float, default=0.0)
    priority = Column(String(20), default='medium')  # high/medium/low
    condition_type = Column(String(20), default='none')  # none/before/after/conditional
    condition_data = Column(Text, nullable=True)  # 条件数据 JSON
    executor_type = Column(String(20), nullable=False, default='ai')  # ai/human/hybrid
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'scenario_id': self.scenario_id,
            'phase_name': self.phase_name,
            'name': self.name,
            'description': self.description,
            'agent_type': self.agent_type,
            'required_capabilities': self.required_capabilities,
            'dependencies': self.dependencies,
            'order_in_phase': self.order_in_phase,
            'estimated_hours': self.estimated_hours,
            'priority': self.priority,
            'condition_type': self.condition_type,
            'condition_data': self.condition_data,
            'executor_type': getattr(self, 'executor_type', 'ai'),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

class TaskTemplateSchema(BaseModel):
    """任务模板 Pydantic 模型"""
    name: str
    description: Optional[str] = None
    agent_type: Optional[str] = None
    required_capabilities: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None  # 任务名称引用，会被转换为 ID
    order_in_phase: int = 0
    estimated_hours: Optional[float] = None
    priority: Optional[str] = 'medium'
    condition_type: str = 'none'
    condition_data: Optional[str] = None
    executor_type: str = 'ai'

    model_config = ConfigDict(from_attributes=True)

# 向后兼容别名（旧代码仍可用 ScenarioTaskTemplate）
ScenarioTaskTemplate = ScenarioTask
