"""
争议管理 — 业务逻辑 facade

原 DisputeLogic 类已移至 _dispute_logic_helpers.py。
此文件重新导出该类，供 dispute_manage.py 使用。
"""
from evo.api._dispute_logic_helpers import DisputeLogic

# Re-export for backwards compat (dispute_manage.py imports this)
__all__ = ["DisputeLogic"]
