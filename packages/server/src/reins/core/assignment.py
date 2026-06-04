"""
Reins Server - 任务自动分配（Agent能力匹配）

实现：
- TaskAssigner: 根据能力需求+负载均衡自动分配任务
- 数据源自数据库（无内存缓存）

依赖：
- AgentRegistry (DB-backed): 注册/心跳/负载管理
"""

from loguru import logger
from typing import Dict, List, Optional, Any
from reins.scheduler.assigner.agent_registry import AgentRegistry

# ============================================================================
# 任务分配器
# ============================================================================

class TaskAssigner:
    """
    任务分配器

    根据步骤的能力需求，自动分配最合适的Agent：
    - 能力匹配度优先
    - 负载均衡作为次要因素
    - 负载过高时选择次优Agent

    所有数据直接从 AgentRegistry (DB-backed) 读取，无内存缓存。
    """

    def __init__(self, registry):
        """
        Args:
            registry: AgentRegistry 实例（DB-backed）
        """
        self._registry = registry

    def assign(self, step: Any, workflow_context: Dict[str, Any] = None) -> Optional[str]:
        """
        为步骤分配Agent

        :param step: WorkflowStep对象或其数据
        :param workflow_context: 工作流上下文（可选）
        :return: 分配的Agent ID，如果没有合适的Agent则返回None
        """
        # 提取步骤的能力需求
        capabilities = self._extract_capabilities(step)

        # 如果步骤已经指定了agent_id，检查是否有效
        assigned_agent = getattr(step, 'agent_id', None)
        if assigned_agent:
            agent = self._registry.get_agent(assigned_agent)
            if agent:
                if agent.can_handle():
                    self._registry.increment_load(assigned_agent)
                    logger.info(f"Step {getattr(step, 'id', 'unknown')} assigned to specified agent {assigned_agent}")
                    return assigned_agent
                else:
                    logger.warning(f"Specified agent {assigned_agent} is at max load")

        # 自动选择最合适的Agent
        return self._select_best_agent(capabilities)

    def _extract_capabilities(self, step: Any) -> List[str]:
        """
        从步骤中提取能力需求

        支持多种格式：
        - step.capabilities: List[str]
        - step.input_data.get('capabilities'): List[str]
        - 从step名称/描述推断
        """
        capabilities = []

        # 直接属性
        if hasattr(step, 'capabilities') and step.capabilities:
            if isinstance(step.capabilities, list):
                capabilities.extend(step.capabilities)
            elif isinstance(step.capabilities, str):
                capabilities.append(step.capabilities)

        # input_data中的能力需求
        input_data = getattr(step, 'input_data', None)
        if input_data:
            if isinstance(input_data, dict):
                if 'capabilities' in input_data:
                    caps = input_data['capabilities']
                    if isinstance(caps, list):
                        capabilities.extend(caps)
                    elif isinstance(caps, str):
                        capabilities.append(caps)
                # 从名称推断
                name = getattr(step, 'name', '') or input_data.get('name', '')
                desc = getattr(step, 'description', '') or input_data.get('description', '')
                inferred = self._infer_capabilities(name, desc)
                capabilities.extend(inferred)
            elif isinstance(input_data, list):
                capabilities.extend(input_data)

        # 从名称/描述推断
        if not capabilities:
            name = getattr(step, 'name', '') or ''
            desc = getattr(step, 'description', '') or ''
            capabilities = self._infer_capabilities(name, desc)

        return list(set(capabilities))

    def _infer_capabilities(self, name: str, description: str) -> List[str]:
        """
        从名称/描述推断能力需求

        基于关键词的简单推断逻辑
        """
        text = f"{name} {description}".lower()
        capabilities = []

        capability_keywords = {
            'rescue': ['rescue', '搜救', '救援', '被困人员', '营救', '搜索'],
            'medical': ['medical', '医疗', '救治', '伤员', '急救'],
            'fire': ['fire', '消防', '灭火', '火灾', '燃烧'],
            'chemical': ['chemical', '化工', '化工厂', '危化品', '泄漏', '有毒'],
            'communication': ['communication', '通讯', '通信', '联络', '信号'],
            'transport': ['transport', '运输', '转运', '运送', '物流'],
            'assessment': ['assessment', '评估', '分析', '判断', '勘测'],
            'command': ['command', '指挥', '协调', '调度', '统筹'],
            'logistics': ['logistics', '后勤', '物资', '保障', '供给'],
            'search': ['search', '搜索', '探测', '寻找', '定位'],
        }

        for cap, keywords in capability_keywords.items():
            if any(kw in text for kw in keywords):
                capabilities.append(cap)

        return capabilities

    def _select_best_agent(self, capabilities: List[str]) -> Optional[str]:
        """
        选择最佳Agent

        策略：
        1. 找到所有满足能力需求的Agent
        2. 按综合分数排序（能力匹配度*0.7 + 负载分数*0.3）
        3. 优先选择分数最高的Agent
        4. 如果最高分的Agent已满载，选择次优
        """
        if not capabilities:
            available = self._registry.get_available_agents()
            if not available:
                all_agents = self._registry.list_agents()
                if all_agents:
                    best = min(all_agents, key=lambda a: a.current_load)
                    self._registry.increment_load(best.id)
                    return best.id
            elif available:
                best = min(available, key=lambda a: a.current_load)
                self._registry.increment_load(best.id)
                return best.id
            return None

        # 找到具备所需能力的Agent
        capable_agents = self._registry.get_agents_by_capabilities(capabilities, require_all=True)

        if not capable_agents:
            capable_agents = self._registry.get_agents_by_capabilities(capabilities, require_all=False)

        if not capable_agents:
            logger.warning(f"No agent found with capabilities: {capabilities}")
            return None

        # 按分数排序
        scored = [(agent, agent.score_for_capabilities(capabilities)) for agent in capable_agents]
        scored.sort(key=lambda x: x[1], reverse=True)

        # 选择最佳Agent（优先考虑能处理任务的）
        for agent, score in scored:
            if agent.can_handle():
                self._registry.increment_load(agent.id)
                logger.info(f"Assigned step to agent {agent.id} (score={score:.2f}, load={agent.current_load}/{agent.load})")
                return agent.id

        # 所有Agent都满载，选择分数最高的
        best_agent = scored[0][0]
        logger.warning(f"All capable agents at max load, assigning to {best_agent.id} anyway")
        self._registry.increment_load(best_agent.id)
        return best_agent.id

    def reassign(self, step: Any, new_agent_id: str) -> bool:
        """重新分配步骤到新的Agent"""
        old_agent_id = getattr(step, 'agent_id', None)
        if old_agent_id:
            self._registry.decrement_load(old_agent_id)
        step.agent_id = new_agent_id
        self._registry.increment_load(new_agent_id)
        logger.info(f"Reassigned step {getattr(step, 'id', 'unknown')} from {old_agent_id} to {new_agent_id}")
        return True

    def unassign(self, step: Any) -> bool:
        """取消分配（释放Agent负载）"""
        agent_id = getattr(step, 'agent_id', None)
        if agent_id:
            self._registry.decrement_load(agent_id)
            logger.debug(f"Unassigned step from agent {agent_id}")
            return True
        return False

# ============================================================================
# 单例实例（直接使用 reins.agent_registry，无额外缓存）
# ============================================================================

_global_assigner: Optional[TaskAssigner] = None
_global_registry: Optional["AgentRegistry"] = None

def get_agent_registry():
    """
    获取全局Agent注册表实例（DB-backed）

    直接创建 AgentRegistry 实例，与 ReinsServer 共享逻辑。
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry

def get_task_assigner() -> TaskAssigner:
    """获取全局任务分配器实例"""
    global _global_assigner
    if _global_assigner is None:
        _global_assigner = TaskAssigner(get_agent_registry())
    return _global_assigner


# Compatibility alias
from reins.scheduler.assigner.agent_registry import AgentRegistry as AgentCapabilityRegistry
