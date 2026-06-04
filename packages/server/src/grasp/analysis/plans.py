"""
Grasp 预案（Plan）管理
提供预案的存储、检索和关键词匹配功能

预案是结构化的应急响应方案，包含标题、描述、适用场景、关键步骤等
"""

import re
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class Plan:
    """预案实体"""
    plan_id: str
    title: str
    description: str
    content: str  # 预案详细内容（JSON 或 Markdown）
    tags: List[str] = field(default_factory=list)
    applicable_scenarios: List[str] = field(default_factory=list)  # 适用场景关键词
    status: str = "ready"  # ready | draft | archived
    version: str = "1.0"
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plan':
        return cls(
            plan_id=data.get('plan_id', f'plan-{uuid.uuid4().hex[:12]}'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            content=data.get('content', ''),
            tags=data.get('tags', []),
            applicable_scenarios=data.get('applicable_scenarios', []),
            status=data.get('status', 'ready'),
            version=data.get('version', '1.0'),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
        )


@dataclass
class PlanMatchResult:
    """预案匹配结果"""
    plan: Plan
    score: float  # 匹配分数 0-1
    matched_keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'plan': self.plan.to_dict(),
            'score': round(self.score, 4),
            'matched_keywords': self.matched_keywords,
        }


class PlanStore:
    """
    预案存储
    内存存储 + JSONL 持久化
    """

    def __init__(self, data_dir: Optional[str] = None):
        self._plans: Dict[str, Plan] = {}
        self._data_file = None
        if data_dir:
            data_path = Path(data_dir)
            data_path.mkdir(parents=True, exist_ok=True)
            self._data_file = data_path / "plans.jsonl"
            self._load_from_file()

    def add(self, plan: Plan) -> Plan:
        """添加预案"""
        self._plans[plan.plan_id] = plan
        self._save_to_file()
        return plan

    def get(self, plan_id: str) -> Optional[Plan]:
        """获取预案"""
        return self._plans.get(plan_id)

    def list_all(self, status: Optional[str] = None) -> List[Plan]:
        """列出所有预案"""
        plans = list(self._plans.values())
        if status:
            plans = [p for p in plans if p.status == status]
        return plans

    def delete(self, plan_id: str) -> bool:
        """删除预案"""
        if plan_id in self._plans:
            del self._plans[plan_id]
            self._save_to_file()
            return True
        return False

    def _save_to_file(self):
        """持久化到 JSONL 文件"""
        if not self._data_file:
            return
        with open(self._data_file, 'w', encoding='utf-8') as f:
            for plan in self._plans.values():
                f.write(json.dumps(plan.to_dict(), ensure_ascii=False) + '\n')

    def _load_from_file(self):
        """从 JSONL 文件加载"""
        if not self._data_file or not self._data_file.exists():
            return
        with open(self._data_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        plan = Plan.from_dict(data)
                        self._plans[plan.plan_id] = plan
                    except (json.JSONDecodeError, KeyError):
                        continue


class PlanMatcher:
    """
    预案匹配器
    根据关键词匹配预案，返回按匹配分数排序的结果
    """

    def __init__(self, store: PlanStore):
        self._store = store

    def search(self, query: str, limit: int = 10) -> List[PlanMatchResult]:
        """
        搜索匹配预案

        匹配策略：
        1. 标题匹配（权重 0.4）
        2. 描述匹配（权重 0.2）
        3. 标签匹配（权重 0.2）
        4. 适用场景匹配（权重 0.15）
        5. 内容匹配（权重 0.05）

        :param query: 搜索关键词
        :param limit: 返回数量上限
        :return: 按匹配分数降序排列的结果列表
        """
        if not query or not query.strip():
            # 无查询词时返回所有预案（按创建时间倒序）
            plans = self._store.list_all(status="ready")
            plans.sort(key=lambda p: p.created_at, reverse=True)
            return [
                PlanMatchResult(plan=p, score=0.0, matched_keywords=[])
                for p in plans[:limit]
            ]

        keywords = self._extract_keywords(query)
        if not keywords:
            return []

        results = []
        for plan in self._store.list_all():
            score, matched = self._calculate_match_score(plan, keywords)
            if score > 0:
                results.append(PlanMatchResult(
                    plan=plan,
                    score=score,
                    matched_keywords=matched,
                ))

        # 按分数降序排序
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词：按空格/标点分割，过滤短词"""
        # 移除标点
        query = re.sub(r'[,.!?;:，。！？；：、\[\]{}()（）]', ' ', query)
        # 分割并过滤
        keywords = [w.strip() for w in query.split() if len(w.strip()) > 0]
        return keywords

    def _calculate_match_score(
        self, plan: Plan, keywords: List[str]
    ) -> tuple[float, List[str]]:
        """
        计算预案与关键词的匹配分数

        Returns: (score, matched_keywords)
        """
        matched_keywords = []
        field_scores = {
            'title': 0.0,
            'description': 0.0,
            'tags': 0.0,
            'scenarios': 0.0,
            'content': 0.0,
        }

        text_fields = {
            'title': plan.title.lower(),
            'description': plan.description.lower(),
            'content': plan.content.lower(),
        }

        for kw in keywords:
            kw_lower = kw.lower()
            kw_matched = False

            # 标题匹配
            if kw_lower in text_fields['title']:
                field_scores['title'] += 1.0
                kw_matched = True

            # 描述匹配
            if kw_lower in text_fields['description']:
                field_scores['description'] += 1.0
                kw_matched = True

            # 标签匹配（精确匹配）
            if any(kw_lower == tag.lower() for tag in plan.tags):
                field_scores['tags'] += 1.0
                kw_matched = True

            # 适用场景匹配
            if any(kw_lower in s.lower() for s in plan.applicable_scenarios):
                field_scores['scenarios'] += 1.0
                kw_matched = True

            # 内容匹配
            if kw_lower in text_fields['content']:
                field_scores['content'] += 1.0
                kw_matched = True

            if kw_matched:
                matched_keywords.append(kw)

        if not matched_keywords:
            return 0.0, []

        # 加权计算
        weights = {
            'title': 0.4,
            'description': 0.2,
            'tags': 0.2,
            'scenarios': 0.15,
            'content': 0.05,
        }

        # 归一化：每个字段的最大可能分数 = keyword 数量
        max_per_field = max(len(keywords), 1)
        total_score = 0.0
        for field_name, weight in weights.items():
            normalized = field_scores[field_name] / max_per_field
            total_score += normalized * weight

        # 分数上限为 1.0
        return min(total_score, 1.0), matched_keywords


# 全局实例（惰性初始化）
_default_store: Optional[PlanStore] = None
_default_matcher: Optional[PlanMatcher] = None


def get_store(data_dir: Optional[str] = None) -> PlanStore:
    """获取或创建全局 PlanStore"""
    global _default_store
    if _default_store is None:
        if data_dir is None:
            # 默认数据目录
            data_dir = str(Path(__file__).parent.parent / "data")
        _default_store = PlanStore(data_dir=data_dir)
    return _default_store


def get_matcher(data_dir: Optional[str] = None) -> PlanMatcher:
    """获取或创建全局 PlanMatcher"""
    global _default_matcher
    if _default_matcher is None:
        store = get_store(data_dir)
        _default_matcher = PlanMatcher(store)
    return _default_matcher
