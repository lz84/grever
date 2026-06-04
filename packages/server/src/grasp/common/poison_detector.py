"""认知投毒检测器 — 从 service.py 抽出的独立模块"""

import re
from typing import List, Tuple


class PoisonDetector:
    """毒药检测器 — 检测恶意注入"""

    # 敏感词/模式（可根据需要扩展）
    DANGEROUS_PATTERNS = [
        r'\b(?:execute|system|eval|exec)\s*\(',  # 代码注入
        r'<script[^>]*>',  # XSS
        r'--\s*drop\s+table',  # SQL 注入
        r'\.\./\.\.',  # 路径遍历
    ]

    def detect(self, content: str) -> Tuple[bool, List[str]]:
        """
        检测内容是否包含危险模式
        Returns: (is_poison, risk_factors)
        """
        risk_factors = []
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                risk_factors.append(pattern)
        return len(risk_factors) > 0, risk_factors
