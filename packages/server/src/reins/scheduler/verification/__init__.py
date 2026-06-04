"""
验证模块 — 结果验证

- rules: 验证规则引擎（分类、客观检查）
- engine: 验证引擎（ResultVerifier 主类）
- arbitration: 仲裁逻辑（争议升级、redispatch）
- reporter: 报告生成（comment 写入、飞书通知）
"""

from .engine import ResultVerifier

__all__ = ["ResultVerifier"]
