"""MemoryAdapter — 基于内存的简单知识存储（Phase 1a）"""

import uuid
import hashlib
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from grasp.adapters.base import BaseGraspAdapter
from grasp.facade.models import (
    CognitionInput, InjectResult, RetrieveResult, UpdateResult, CognitionItem
)


class MemoryAdapter(BaseGraspAdapter):
    """
    内存存储适配器 — 开发/测试/兜底用

    使用 dict 存储 + 关键词匹配检索
    所有操作同步完成，无外部依赖
    """

    @property
    def name(self) -> str:
        return "memory"

    def __init__(self):
        # 主存储：cognition_id -> CognitionInput
        self._store: Dict[str, CognitionInput] = {}
        # content hash 索引：hash -> cognition_id（用于幂等查重）
        self._hash_index: Dict[str, str] = {}
        # 标签索引：tag -> set[cognition_id]
        self._tag_index: Dict[str, set] = {}
        # 类型索引：type -> set[cognition_id]
        self._type_index: Dict[str, set] = {}

    async def inject(self, cognition: CognitionInput) -> InjectResult:
        """注入认知到内存存储"""
        cognition_id = f"cog-{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        # 计算 content hash
        content_hash = hashlib.sha256(
            cognition.content.encode('utf-8')
        ).hexdigest()[:16]

        # 存储
        entry = CognitionInput(
            content=cognition.content,
            type=cognition.type,
            tags=list(cognition.tags),
            confidence=cognition.confidence,
            metadata=dict(cognition.metadata or {}),
            domain=cognition.domain,
        )
        entry.cognition_id = cognition_id
        entry._content_hash = content_hash  # 内部使用
        entry._created_at = now
        entry._updated_at = now

        self._store[cognition_id] = entry
        self._hash_index[content_hash] = cognition_id

        # 更新索引
        for tag in cognition.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(cognition_id)

        type_key = cognition.type or "what"
        if type_key not in self._type_index:
            self._type_index[type_key] = set()
        self._type_index[type_key].add(cognition_id)

        return InjectResult(
            cognition_id=cognition_id,
            backend=self.name,
            quality_score=0.0,
            is_duplicate=False,
        )

    async def retrieve(
        self,
        query: str,
        mode: str = "local",
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> RetrieveResult:
        """检索认知 — 简单关键词匹配"""
        filters = filters or {}
        keywords = self._extract_keywords(query)

        candidates = []
        for cog_id, entry in self._store.items():
            # 类型过滤
            if "type" in filters:
                filter_types = filters["type"]
                if isinstance(filter_types, list):
                    if entry.type not in filter_types:
                        continue
                elif entry.type != filter_types:
                    continue

            # 标签过滤（AND 匹配）
            if "tags" in filters:
                filter_tags = filters["tags"]
                if not all(tag in entry.tags for tag in filter_tags):
                    continue

            # 置信度过滤
            if "min_confidence" in filters:
                if entry.confidence < filters["min_confidence"]:
                    continue

            # 领域过滤
            if "domain" in filters and entry.domain != filters["domain"]:
                continue

            # 关键词匹配
            if keywords:
                match = any(kw in entry.content for kw in keywords)
                if not match:
                    continue

            candidates.append(entry)

        # 排序（按置信度降序）
        candidates.sort(key=lambda c: c.confidence, reverse=True)

        total = len(candidates)
        paginated = candidates[:limit]

        items = [
            CognitionItem(
                cognition_id=getattr(e, 'cognition_id', ''),
                type=e.type,
                content=e.content,
                tags=list(e.tags),
                confidence=e.confidence,
                quality_score=0.0,
                created_at=getattr(e, '_created_at', None),
                updated_at=getattr(e, '_updated_at', None),
            )
            for e in paginated
        ]

        return RetrieveResult(
            items=items,
            total=total,
            has_more=limit < total,
        )

    async def update(
        self, cognition_id: str, content: str,
        metadata: Dict[str, Any]
    ) -> UpdateResult:
        """更新已有认知"""
        if cognition_id not in self._store:
            raise KeyError(f"Cognition '{cognition_id}' not found")

        entry = self._store[cognition_id]
        old_hash = getattr(entry, '_content_hash', None)

        # 更新内容
        entry.content = content
        entry._updated_at = datetime.now().isoformat()

        # 更新 metadata
        if metadata:
            entry.metadata.update(metadata)

        # 更新 hash 索引
        new_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        entry._content_hash = new_hash
        if old_hash and old_hash in self._hash_index:
            del self._hash_index[old_hash]
        self._hash_index[new_hash] = cognition_id

        return UpdateResult(
            cognition_id=cognition_id,
            quality_score=0.0,
        )

    async def delete(self, cognition_id: str) -> bool:
        """删除认知"""
        if cognition_id not in self._store:
            return False

        entry = self._store.pop(cognition_id)

        # 清理 hash 索引
        content_hash = getattr(entry, '_content_hash', None)
        if content_hash and content_hash in self._hash_index:
            del self._hash_index[content_hash]

        # 清理标签索引
        for tag in entry.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(cognition_id)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]

        # 清理类型索引
        type_key = entry.type or "what"
        if type_key in self._type_index:
            self._type_index[type_key].discard(cognition_id)
            if not self._type_index[type_key]:
                del self._type_index[type_key]

        return True

    async def search_by_content_hash(
        self, content_hash: str, domain: Optional[str] = None
    ) -> Optional[CognitionInput]:
        """根据 content hash 查找已有认知（用于幂等查重）"""
        if content_hash not in self._hash_index:
            return None

        cognition_id = self._hash_index[content_hash]
        entry = self._store.get(cognition_id)
        if entry is None:
            return None

        # 领域过滤
        if domain is not None and entry.domain != domain:
            return None

        return entry

    def is_available(self) -> bool:
        """MemoryAdapter 始终可用"""
        return True

    def validate_filters(self, filters: Dict[str, Any]) -> List[str]:
        """
        验证过滤器支持情况
        MemoryAdapter 支持 type, tags, min_confidence, domain
        """
        unsupported = []
        supported = {"type", "tags", "min_confidence", "domain"}
        for key in filters:
            if key not in supported:
                unsupported.append(key)
        return unsupported

    def get_status(self) -> Dict[str, Any]:
        """返回后端状态"""
        return {
            "index_size": len(self._store),
            "backend_version": "1.0.0",
        }

    @staticmethod
    def _extract_keywords(query: str) -> List[str]:
        """从查询中提取关键词"""
        query = re.sub(r'[,.!?;:，。！？；：、]', ' ', query)
        keywords = [word.strip() for word in query.split() if word.strip()]
        return keywords
