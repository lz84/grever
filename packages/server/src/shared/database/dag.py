"""
DAG (Directed Acyclic Graph) 工具模块

提供工作流 DAG 的：
- 拓扑排序 (topological sort)
- 循环检测 (cycle detection)
- 可执行节点计算 (runnable nodes)
- 层级划分 (layer partitioning)
"""

from typing import List, Set, Dict, Optional, Tuple
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class DAGError(Exception):
    """DAG 相关错误基类"""
    pass


class CycleError(DAGError):
    """检测到循环依赖"""
    pass


class EmptyGraphError(DAGError):
    """图为空"""
    pass


class DAG:
    """
    有向无环图 (DAG) 操作工具

    节点: str (step_id)
    边: List[Tuple[str, str]] — (from_node, to_node)，from → to 表示 from 依赖 to

    Example:
        dag = DAG()
        dag.add_node("step1")
        dag.add_node("step2")
        dag.add_node("step3")
        dag.add_edge("step1", "step2")  # step2 依赖 step1
        dag.add_edge("step2", "step3")  # step3 依赖 step2
        dag.topological_sort()  # ["step1", "step2", "step3"]
    """

    def __init__(self, edges: Optional[List[Tuple[str, str]]] = None):
        self._nodes: Set[str] = set()
        self._adj: Dict[str, List[str]] = defaultdict(list)  # node -> successors
        self._pred: Dict[str, List[str]] = defaultdict(list)  # node -> predecessors

        if edges:
            for src, dst in edges:
                self.add_edge(src, dst)

    def add_node(self, node: str) -> None:
        """添加节点"""
        self._nodes.add(node)
        if node not in self._adj:
            self._adj[node] = []
        if node not in self._pred:
            self._pred[node] = []

    def add_edge(self, src: str, dst: str) -> None:
        """
        添加边: src → dst
        表示 dst 依赖 src (src 必须在 dst 之前完成)
        """
        self.add_node(src)
        self.add_node(dst)
        if dst not in self._adj[src]:
            self._adj[src].append(dst)
        if src not in self._pred[dst]:
            self._pred[dst].append(src)

    @property
    def nodes(self) -> List[str]:
        """返回所有节点"""
        return list(self._nodes)

    @property
    def edges(self) -> List[Tuple[str, str]]:
        """返回所有边"""
        return [
            (src, dst)
            for src, successors in self._adj.items()
            for dst in successors
        ]

    def incoming(self, node: str) -> List[str]:
        """返回指向 node 的前驱节点列表 (依赖项)"""
        return list(self._pred.get(node, []))

    def outgoing(self, node: str) -> List[str]:
        """返回从 node 出发指向的后继节点列表"""
        return list(self._adj.get(node, []))

    def has_cycle(self) -> bool:
        """检测是否存在循环依赖 (DFS)"""
        WHITE, GREY, BLACK = 0, 1, 2
        color: Dict[str, int] = {n: WHITE for n in self._nodes}

        def dfs(n: str) -> bool:
            color[n] = GREY
            for succ in self._adj.get(n, []):
                if color[succ] == GREY:
                    return True
                if color[succ] == WHITE and dfs(succ):
                    return True
            color[n] = BLACK
            return False

        for node in self._nodes:
            if color[node] == WHITE and dfs(node):
                return True
        return False

    def topological_sort(self) -> List[str]:
        """
        Kahn 算法拓扑排序

        返回按依赖顺序排列的节点列表。
        如果存在环，抛出 CycleError。

        依赖关系: edge(src, dst) 表示 dst 依赖 src，
                 所以 src 排在 dst 前面。
        """
        if not self._nodes:
            return []

        if self.has_cycle():
            raise CycleError("Cannot topological sort: graph contains a cycle")

        # 入度
        in_degree: Dict[str, int] = {
            n: len(self._pred.get(n, [])) for n in self._nodes
        }

        # 入度为 0 的节点队列
        queue = deque([n for n, d in in_degree.items() if d == 0])
        result: List[str] = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for succ in self._adj.get(node, []):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        if len(result) != len(self._nodes):
            raise CycleError("Cannot topological sort: graph contains a cycle")

        return result

    def layers(self) -> List[List[str]]:
        """
        将 DAG 划分为层级 (layers)

        同一层的节点可以并行执行。
        Layer 0: 无依赖的节点
        Layer N: 依赖 Layer 0..N-1 中某些节点的节点

        Returns:
            List of layers, each layer is a list of node ids
        """
        if not self._nodes:
            return []

        # 复制入度
        in_degree: Dict[str, int] = {
            n: len(self._pred.get(n, [])) for n in self._nodes
        }

        layers: List[List[str]] = []
        remaining = set(self._nodes)

        while remaining:
            # 当前层: 入度为 0 的节点
            layer = [n for n in remaining if in_degree[n] == 0]
            if not layer:
                # 不应该发生（如果 has_cycle 检查过）
                raise CycleError("Layer partitioning failed: cycle detected")

            layers.append(layer)
            for node in layer:
                remaining.remove(node)
                for succ in self._adj.get(node, []):
                    in_degree[succ] -= 1

        return layers

    def runnable_nodes(self, completed: Set[str]) -> List[str]:
        """
        计算在 completed 集合完成后，哪些节点可以执行

        Args:
            completed: 已完成执行的节点 ID 集合

        Returns:
            可执行的节点列表（去重）
        """
        runnable = []
        for node in self._nodes:
            if node in completed:
                continue
            # 所有前驱都已完成
            if all(pred in completed for pred in self._pred.get(node, [])):
                runnable.append(node)
        return runnable

    def build_from_steps(
        self,
        steps: List[dict]
    ) -> 'DAG':
        """
        从 WorkflowStep 列表构建 DAG

        steps: List[dict]，每个 dict 至少包含:
            - id: 步骤 ID
            - dependencies: List[str] — 前驱步骤 ID 列表

        依赖关系: step A 依赖 step B → edge(B, A)
                 即 A 的所有 dependencies 指向 A
        """
        dag = DAG()
        for step in steps:
            step_id = step['id']
            dag.add_node(step_id)
            for dep in step.get('dependencies', []) or []:
                # dep → step_id
                dag.add_edge(dep, step_id)
        return dag

    def __repr__(self) -> str:
        return f"<DAG nodes={len(self._nodes)}, edges={len(self.edges)}>"
