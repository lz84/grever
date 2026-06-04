"""
任务结果校验服务
实现任务完成时的自动校验逻辑
"""

from typing import Tuple
from models.task import Task

# 定义各类别的关键词映射
CATEGORY_KEYWORDS = {
    "research": ["研究", "调研", "分析", "报告", "数据", "文献", "资料", "总结"],
    "coding": ["代码", "编程", "实现", "功能", "模块", "算法", "测试", "修复"],
    "review": ["评审", "审查", "评估", "反馈", "建议", "优化", "改进建议"],
    "testing": ["测试", "验证", "检查", "调试", "性能", "功能", "单元测试"],
    "documentation": ["文档", "说明", "指南", "教程", "手册", "描述", "规范"],
}

# 错误模式：结果中包含这些内容说明执行实际失败了
ERROR_PATTERNS = [
    "Context overflow",
    "prompt too large",
    "Traceback (most recent call last)",
    "ConnectionError",
    "Connection refused",
    "Model is not ready",
    "rate limit exceeded",
]

def validate_task_result(task: Task, result: str) -> Tuple[bool, str]:
    """
    校验任务结果
    Returns: (passed, reason)
    """
    # 1. result 不为空
    if not result or not result.strip():
        return False, "结果为空"

    # 2. 结果长度检查
    if len(result.strip()) < 10:
        return False, f"结果过短（{len(result.strip())}字符），可能执行不完整"

    # 3. 错误模式检查 — 结果中包含错误标记说明实际执行失败
    for pattern in ERROR_PATTERNS:
        if pattern in result:
            return False, f"结果包含错误模式 '{pattern}'，执行实际失败"

    # 4. 类别关键词检查（如果有 category）
    task_category = getattr(task, 'category', None)
    if task_category:
        keywords = CATEGORY_KEYWORDS.get(task_category, [])
        if keywords:
            has_keyword = any(kw in result for kw in keywords)
            if not has_keyword:
                return False, f"结果中缺少{task_category}类别关键词"

    return True, ""