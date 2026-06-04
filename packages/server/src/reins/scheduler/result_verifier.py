"""
结果验证器 — 薄分发层（向后兼容重导出）

Phase 2.3: 实际实现已迁移到 verification/ 子模块：
- verification/rules.py — 验证规则引擎
- verification/engine.py — 验证引擎
- verification/arbitration.py — 仲裁逻辑
- verification/reporter.py — 报告生成
"""

from reins.scheduler.verification.engine import ResultVerifier

__all__ = ["ResultVerifier"]
