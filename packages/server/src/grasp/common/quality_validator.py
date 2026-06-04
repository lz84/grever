"""认知质量验证器 — 从 service.py 抽出的独立模块"""

from typing import List, Tuple


class QualityValidator:
    """质量验证器 — 验证认知质量"""

    MIN_CONTENT_LENGTH = 10  # 最小内容长度
    MAX_CONTENT_LENGTH = 10000  # 最大内容长度

    def validate(self, content: str, confidence: float = 0.8) -> Tuple[bool, float, List[str]]:
        """
        验证认知质量
        Returns: (is_valid, quality_score, issues)
        """
        issues = []
        score = 1.0

        # 内容长度检查
        if len(content) < self.MIN_CONTENT_LENGTH:
            issues.append("content_too_short")
            score -= 0.3

        if len(content) > self.MAX_CONTENT_LENGTH:
            issues.append("content_too_long")
            score -= 0.2

        # 置信度检查
        if confidence < 0.3:
            issues.append("low_confidence")
            score -= 0.3

        if confidence > 1.0 or confidence < 0:
            issues.append("invalid_confidence")
            score -= 0.5

        return score > 0.5, max(0, score), issues
