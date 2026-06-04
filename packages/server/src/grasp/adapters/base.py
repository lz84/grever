"""BaseGraspAdapter — 所有 Graph RAG 后端必须实现的抽象接口"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from grasp.facade.models import (
    CognitionInput, InjectResult, RetrieveResult, UpdateResult
)


class BaseGraspAdapter(ABC):
    """所有 Grasp 存储后端必须实现的抽象接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        """后端标识名，如 'memory', 'microsoft-graphrag'"""
        pass

    @abstractmethod
    async def inject(self, cognition: CognitionInput) -> InjectResult:
        """注入认知到索引"""
        pass

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        mode: str = "local",
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> RetrieveResult:
        """
        检索认知

        :param mode: 'local'（实体）/ 'global'（社区）/ 'drift'（深度）/ 'basic'（关键词）
        :param filters: type, tags, min_confidence, domain 等
        """
        pass

    @abstractmethod
    async def update(self, cognition_id: str, content: str,
                     metadata: Dict[str, Any]) -> UpdateResult:
        """更新已有认知"""
        pass

    @abstractmethod
    async def delete(self, cognition_id: str) -> bool:
        """删除认知"""
        pass

    @abstractmethod
    async def search_by_content_hash(
        self, content_hash: str, domain: Optional[str] = None
    ) -> Optional[CognitionInput]:
        """根据 content hash 查找已有认知（用于幂等查重）"""
        pass

    def is_available(self) -> bool:
        """检查后端是否可用"""
        try:
            self._check_dependencies()
            return True
        except ImportError:
            return False

    def validate_filters(self, filters: Dict[str, Any]) -> List[str]:
        """
        验证过滤器支持情况
        Returns: 不支持的 filter 名称列表
        """
        return []

    def _check_dependencies(self):
        """子类实现：检查依赖"""
        pass

    def get_status(self) -> Dict[str, Any]:
        """返回后端健康状态和统计信息"""
        return {"index_size": 0, "backend_version": "0.0.0"}
