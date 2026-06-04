"""
争议管理 (Dispute Management)
负责 Agent 间冲突的裁决和处理

2026-04-25 精简：删除内存字典，不再被 ReinsServer 使用。
ReinsServer 的争议操作已改为直接调用 DisputeRepository。
"""

from typing import List
from models import DisputeType, DisputeStatus

class DisputeManager:
    """
    争议管理器（已废弃）

    2026-04-25 重构：Dispute CRUD 全部走 DB repository。
    此类保留仅用于向后兼容，内部方法不再操作内存字典。
    """

    def __init__(self):
        pass  # 不再维护 _disputes 内存字典
