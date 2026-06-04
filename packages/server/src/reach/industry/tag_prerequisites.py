"""
标签 Prerequisites 校验引擎

提供标签依赖校验、环形依赖检测、prerequisites 递归展开、废弃标签检查、替代标签推荐。
"""

import json
from loguru import logger
from typing import Dict, List, Set, Optional

from reins.common.database import get_db_session
from models.industry_tag import IndustryCapabilityTag

# =============================================================================
# Custom Exceptions
# =============================================================================

class CircularDependencyError(Exception):
    """检测到环形依赖时抛出"""

    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"Circular dependency detected: {' → '.join(cycle)}")

class MaxDepthExceededError(Exception):
    """递归展开超过最大深度时抛出"""

    def __init__(self, tag_id: str, depth: int):
        self.tag_id = tag_id
        self.depth = depth
        super().__init__(f"Max depth exceeded while resolving prerequisites for '{tag_id}' at depth {depth}")

# =============================================================================
# Internal Helpers
# =============================================================================

def _parse_prerequisites(prereq_json: str) -> List[str]:
    """安全解析 prerequisites JSON 字段"""
    if not prereq_json:
        return []
    try:
        parsed = json.loads(prereq_json)
        if isinstance(parsed, list):
            return [str(p) for p in parsed]
        return []
    except (json.JSONDecodeError, TypeError):
        return []

def _fetch_tags_by_ids(tag_ids: List[str]) -> Dict[str, IndustryCapabilityTag]:
    """批量查询标签，返回 {id: tag} 字典"""
    if not tag_ids:
        return {}
    session = get_db_session()
    try:
        tags = session.query(IndustryCapabilityTag).filter(
            IndustryCapabilityTag.id.in_(tag_ids)
        ).all()
        return {tag.id: tag for tag in tags}
    finally:
        session.close()

# =============================================================================
# Public API
# =============================================================================

def detect_circular_dependencies(tag_ids: List[str], max_depth: int = 10) -> List[List[str]]:
    """
    检测标签依赖中的环形依赖。

    Args:
        tag_ids: 待检测的标签 ID 列表
        max_depth: 最大递归深度限制（超过此深度视为环形）

    Returns:
        环列表：[["A", "B", "C", "A"], ["C", "D", "E", "C"]]
        使用 DFS，visited + rec_stack 模式
    """
    if not tag_ids:
        return []

    session = get_db_session()
    try:
        # 批量获取所有相关标签（向上递归收集）
        all_ids: Set[str] = set(tag_ids)
        ids_to_fetch: Set[str] = set(tag_ids)

        # 迭代展开所有 prerequisites 直到稳定
        for _ in range(max_depth):
            if not ids_to_fetch:
                break
            tags = session.query(IndustryCapabilityTag).filter(
                IndustryCapabilityTag.id.in_(list(ids_to_fetch))
            ).all()
            ids_to_fetch.clear()
            for tag in tags:
                prereqs = _parse_prerequisites(tag.prerequisites)
                for p in prereqs:
                    if p not in all_ids:
                        all_ids.add(p)
                        ids_to_fetch.add(p)
    finally:
        session.close()

    # 构建完整的依赖图
    session = get_db_session()
    try:
        graph: Dict[str, List[str]] = {}
        for tag_id in all_ids:
            tag = session.query(IndustryCapabilityTag).filter(
                IndustryCapabilityTag.id == tag_id
            ).first()
            if tag:
                graph[tag_id] = _parse_prerequisites(tag.prerequisites)
            else:
                graph[tag_id] = []
    finally:
        session.close()

    # DFS 环形检测
    cycles: List[List[str]] = []
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    path: List[str] = []

    def dfs_find_cycle(tag_id: str) -> None:
        if tag_id in rec_stack:
            # 发现环：找到环的起点
            cycle_start_idx = path.index(tag_id)
            cycle = path[cycle_start_idx:] + [tag_id]
            cycles.append(cycle)
            return
        if tag_id in visited:
            return

        rec_stack.add(tag_id)
        path.append(tag_id)

        for prereq in graph.get(tag_id, []):
            dfs_find_cycle(prereq)

        path.pop()
        rec_stack.remove(tag_id)
        visited.add(tag_id)

    for tag_id in all_ids:
        if tag_id not in visited:
            dfs_find_cycle(tag_id)

    return cycles

def resolve_all_prerequisites(tag_ids: List[str], max_depth: int = 10) -> List[str]:
    """
    递归解析所有 prerequisites，返回完整标签 ID 列表（含原始标签 + 所有前置）。

    Args:
        tag_ids: 起始标签 ID 列表
        max_depth: 最大递归深度限制

    Returns:
        完整标签 ID 列表（含原始标签 + 所有递归前置）
    """
    if not tag_ids:
        return []

    graph: Dict[str, List[str]] = {}
    visited: Set[str] = set()
    depth_map: Dict[str, int] = {}

    def resolveRecursive(ids: List[str], current_depth: int) -> Set[str]:
        if current_depth > max_depth:
            raise MaxDepthExceededError(list(ids)[0] if ids else "unknown", current_depth)

        result: Set[str] = set()
        ids_to_fetch = [tid for tid in ids if tid not in graph]

        if ids_to_fetch:
            session = get_db_session()
            try:
                tags = session.query(IndustryCapabilityTag).filter(
                    IndustryCapabilityTag.id.in_(ids_to_fetch)
                ).all()
                for tag in tags:
                    graph[tag.id] = _parse_prerequisites(tag.prerequisites)
                for tid in ids_to_fetch:
                    if tid not in graph:
                        graph[tid] = []
            finally:
                session.close()

        for tid in ids:
            if tid in visited:
                continue
            visited.add(tid)
            depth_map[tid] = current_depth
            result.add(tid)
            prereqs = graph.get(tid, [])
            if prereqs:
                result.update(resolveRecursive(prereqs, current_depth + 1))
        return result

    return list(resolveRecursive(list(tag_ids), 0))

def validate_prerequisites(tag_ids: List[str], max_depth: int = 10) -> Dict[str, List[str]]:
    """
    验证标签列表的 prerequisites 是否全部满足。

    Args:
        tag_ids: 待验证的标签 ID 列表
        max_depth: 最大递归深度限制

    Returns:
        {tag_id: [missing_prerequisites]}，空字典表示全部满足
    """
    if not tag_ids:
        return {}

    # 1. 环形检测（max_depth 内的环视为无效）
    cycles = detect_circular_dependencies(tag_ids, max_depth)
    if cycles:
        raise CircularDependencyError(cycles[0])

    # 2. 递归展开所有 prerequisites（用于环形检测）
    resolve_all_prerequisites(tag_ids, max_depth)
    # all_tag_set: 仅用户提供的标签（不去递归展开）
    all_tag_set = set(tag_ids)

    # 3. 检查每个原始标签的 prerequisites 是否在展开集合中
    missing: Dict[str, List[str]] = {}
    session = get_db_session()
    try:
        tags = session.query(IndustryCapabilityTag).filter(
            IndustryCapabilityTag.id.in_(tag_ids)
        ).all()
        for tag in tags:
            prereqs = _parse_prerequisites(tag.prerequisites)
            missing_list = [p for p in prereqs if p not in all_tag_set]
            if missing_list:
                missing[tag.id] = missing_list
    finally:
        session.close()

    return missing

def check_deprecated_tags(tag_ids: List[str]) -> List[dict]:
    """
    检查标签列表中是否有 deprecated 或 replaced_by 的标签。

    Args:
        tag_ids: 待检查的标签 ID 列表

    Returns:
        警告列表：[{"tag_id": "...", "status": "deprecated", "replaced_by": "..."}]
    """
    if not tag_ids:
        return []

    session = get_db_session()
    try:
        tags = session.query(IndustryCapabilityTag).filter(
            IndustryCapabilityTag.id.in_(tag_ids)
        ).all()
    finally:
        session.close()

    warnings = []
    for tag in tags:
        if tag.status == "deprecated" or tag.replaced_by:
            warnings.append({
                "tag_id": tag.id,
                "status": tag.status,
                "replaced_by": tag.replaced_by or "",
            })
    return warnings

def suggest_replacements(deprecated_tags: List[str]) -> Dict[str, str]:
    """
    为已废弃的标签推荐替代标签。

    Args:
        deprecated_tags: 已废弃的标签 ID 列表

    Returns:
        {old_tag_id: new_tag_id}
    """
    if not deprecated_tags:
        return {}

    session = get_db_session()
    try:
        tags = session.query(IndustryCapabilityTag).filter(
            IndustryCapabilityTag.id.in_(deprecated_tags)
        ).all()
    finally:
        session.close()

    suggestions = {}
    for tag in tags:
        if tag.replaced_by:
            suggestions[tag.id] = tag.replaced_by
    return suggestions
