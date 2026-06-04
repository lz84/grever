"""
Agent 发现 (Agent Discovery)
负责按能力和状态查询 Agent
"""

from typing import List, Optional
from models import AgentInfo, AgentStatus, DiscoverResult

class AgentDiscovery:
    """
    Agent 发现管理器
    提供按能力和状态查询 Agent 的能力
    """

    def __init__(self, agent_registry):
        self._registry = agent_registry

    def discover(
        self,
        capabilities: List[str] = None,
        status: AgentStatus = None,
        max_load: int = None,
    ) -> List[AgentInfo]:
        """
        发现 Agent

        Args:
            capabilities: 所需能力列表（需全部匹配）
            status: Agent 状态过滤
            max_load: 最大负载百分比

        Returns:
            List[AgentInfo]: 符合条件的 Agent 列表
        """
        agents = self._registry.list_agents()

        # 按状态过滤
        if status:
            agents = [a for a in agents if a.status == status]

        # 按能力过滤
        if capabilities:
            agents = [a for a in agents if self._match_capabilities(a, capabilities)]

        # 按负载过滤
        if max_load is not None:
            agents = [a for a in agents if a.load <= max_load]

        # 按负载排序（负载低的优先）
        agents = sorted(agents, key=lambda a: a.load)

        return agents

    def find(self, agent_id: str) -> AgentInfo:
        """
        查找特定 Agent

        Args:
            agent_id: Agent ID

        Returns:
            AgentInfo: Agent 信息，不存在返回 None
        """
        return self._registry.get_agent(agent_id)

    def find_by_capability(self, capability: str) -> List[AgentInfo]:
        """
        按单个能力查找 Agent

        Args:
            capability: 能力名称

        Returns:
            List[AgentInfo]: 符合条件的 Agent 列表
        """
        return self.discover(capabilities=[capability])

    def find_by_capabilities_any(self, capabilities: List[str]) -> List[AgentInfo]:
        """
        按多个能力查找 Agent（任意匹配）

        Args:
            capabilities: 能力列表

        Returns:
            List[AgentInfo]: 符合条件的 Agent 列表
        """
        agents = self._registry.list_agents()
        matched = []

        for agent in agents:
            for cap in capabilities:
                if cap.lower() in [c.lower() for c in agent.capabilities]:
                    matched.append(agent)
                    break

        return matched

    def find_available(self) -> List[AgentInfo]:
        """
        查找可用的 Agent（在线且负载低于 50%）

        Returns:
            List[AgentInfo]: 可用 Agent 列表
        """
        return self.discover(status=AgentStatus.ONLINE, max_load=50)

    def find_least_loaded(self, capabilities: List[str] = None) -> AgentInfo:
        """
        查找负载最低的 Agent

        Args:
            capabilities: 所需能力列表（可选）

        Returns:
            AgentInfo: 负载最低的 Agent，不存在返回 None
        """
        agents = self.discover(capabilities=capabilities, status=AgentStatus.ONLINE)

        if not agents:
            agents = self.discover(capabilities=capabilities)

        return agents[0] if agents else None

    def _match_capabilities(self, agent: AgentInfo, required: List[str]) -> bool:
        """
        检查 Agent 是否匹配所需能力

        Args:
            agent: Agent 信息
            required: 所需能力列表

        Returns:
            bool: 是否全部匹配
        """
        agent_caps = [c.lower() for c in agent.capabilities]

        for req in required:
            req_lower = req.lower()
            found = False
            for cap in agent_caps:
                # 支持部分匹配
                if req_lower in cap or cap in req_lower:
                    found = True
                    break
            if not found:
                return False

        return True

    def get_agents_by_project(self, project_members: List[dict]) -> List[AgentInfo]:
        """
        获取项目成员中的 Agent

        Args:
            project_members: 项目成员列表 [{"agent_id": "xxx", "role": "xxx"}]

        Returns:
            List[AgentInfo]: Agent 信息列表
        """
        result = []
        for member in project_members:
            agent = self._registry.get_agent(member["agent_id"])
            if agent:
                result.append(agent)
        return result

    def get_all_capabilities(self) -> dict:
        """
        获取所有已注册 Agent 的能力汇总

        Returns:
            dict: {capability: [agent_id, ...]}
        """
        capabilities = {}

        for agent in self._registry.list_agents():
            for cap in agent.capabilities:
                cap_lower = cap.lower()
                if cap_lower not in capabilities:
                    capabilities[cap_lower] = []
                capabilities[cap_lower].append(agent.id)

        return capabilities

    def search(self, query: str) -> List[AgentInfo]:
        """
        模糊搜索 Agent

        Args:
            query: 搜索词（匹配名称和能力）

        Returns:
            List[AgentInfo]: 匹配的 Agent 列表
        """
        query_lower = query.lower()
        results = []

        for agent in self._registry.list_agents():
            # 匹配名称
            if query_lower in agent.name.lower():
                results.append(agent)
                continue

            # 匹配能力
            for cap in agent.capabilities:
                if query_lower in cap.lower():
                    results.append(agent)
                    break

        return results
