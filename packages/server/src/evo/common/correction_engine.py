"""
Reins Server - 对话式修正引擎

实现：
- 解析用户自然语言指令
- 实时更新执行方案（workflow/plan）
- 支持多种修正类型
"""

import asyncio
from loguru import logger
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable

# ============================================================================
# 枚举定义
# ============================================================================

class CorrectionType(str, Enum):
    """修正类型"""
    PRIORITY_RAISE = "priority_raise"        # 提升优先级
    PRIORITY_LOWER = "priority_lower"        # 降低优先级
    DELETE_STEP = "delete_step"              # 删除步骤
    ADD_STEP = "add_step"                    # 添加步骤
    REASSIGN = "reassign"                    # 重新分配Agent
    PAUSE_STEP = "pause_step"                # 暂停步骤
    RESUME_STEP = "resume_step"              # 恢复步骤
    CANCEL_STEP = "cancel_step"              # 取消步骤
    MODIFY_INPUT = "modify_input"             # 修改输入数据
    ADD_DEPENDENCY = "add_dependency"        # 添加依赖
    UNKNOWN = "unknown"                       # 未知指令

# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class CorrectionRequest:
    """修正请求"""
    original: str                              # 原始指令
    correction_type: CorrectionType            # 修正类型
    parsed_result: Dict[str, Any]             # 解析结果
    changes: Dict[str, Any]                    # 变更内容
    timestamp: datetime = field(default_factory=datetime.now)
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    agent_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "correction_type": self.correction_type.value,
            "parsed_result": self.parsed_result,
            "changes": self.changes,
            "timestamp": self.timestamp.isoformat(),
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "agent_id": self.agent_id,
        }

@dataclass
class CorrectionResult:
    """修正结果"""
    success: bool
    message: str
    correction: Optional[CorrectionRequest] = None
    workflow_changes: Optional[Dict[str, Any]] = None
    step_changes: Optional[Dict[str, Any]] = None

# ============================================================================
# 解析器
# ============================================================================

class NaturalLanguageParser:
    """
    自然语言指令解析器

    支持的指令模式：
    - "把X任务优先级调到最高" → PRIORITY_RAISE
    - "把X任务优先级降低" → PRIORITY_LOWER
    - "去掉Y任务" / "删除Y任务" → DELETE_STEP
    - "增加Z任务" / "添加Z任务" → ADD_STEP
    - "X任务改派给A Agent" → REASSIGN
    - "暂停X任务" → PAUSE_STEP
    - "恢复X任务" → RESUME_STEP
    - "取消X任务" → CANCEL_STEP
    """

    # 能力关键词（用于推断任务名称）
    CAPABILITY_KEYWORDS = {
        'rescue': '救援',
        '搜救': 'rescue',
        '救援': 'rescue',
        '被困人员': 'rescue',
        'medical': '医疗',
        '医疗': 'medical',
        '救治': 'medical',
        '伤员': 'medical',
        'fire': '消防',
        '消防': 'fire',
        '灭火': 'fire',
        '化工': 'chemical',
        'chemical': 'chemical',
        '化工厂': 'chemical',
        'communication': '通讯',
        '通讯': 'communication',
        'transport': '运输',
        '运输': 'transport',
    }

    def __init__(self):
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> Dict[CorrectionType, List[tuple]]:
        """构建匹配模式"""
        return {
            # 优先级提升
            CorrectionType.PRIORITY_RAISE: [
                # 中文模式
                (r'把(.+?)(任务|步骤)?优先级调?(到|到最)?高', 'raise'),
                (r'把(.+?)(任务|步骤)?提到最高优先级', 'raise'),
                (r'(.+?)(任务|步骤)最重要', 'raise'),
                (r'优先处理(.+?)(任务|步骤)', 'raise'),
                (r'先做(.+?)(任务|步骤)', 'raise'),
                # 英文模式
                (r'raise priority of (.+?) to (?:the )?highest', 'raise'),
                (r'make (.+?) (?:the )?top priority', 'raise'),
            ],
            # 优先级降低
            CorrectionType.PRIORITY_LOWER: [
                (r'把(.+?)(任务|步骤)?优先级降低', 'lower'),
                (r'把(.+?)(任务|步骤)?往后排', 'lower'),
                (r'延后(.+?)(任务|步骤)', 'lower'),
                (r'低.?先(.+?)(任务|步骤)', 'lower'),
                (r'lower priority of (.+?)', 'lower'),
                (r'deprioritize (.+?)', 'lower'),
            ],
            # 删除步骤
            CorrectionType.DELETE_STEP: [
                (r'去掉(.+?)(任务|步骤)', 'delete'),
                (r'删除(.+?)(任务|步骤)', 'delete'),
                (r'不要(.+?)(任务|步骤)', 'delete'),
                (r'移除(.+?)(任务|步骤)', 'delete'),
                (r'remove (.+?) (?:task|step)', 'delete'),
                (r'delete (.+?) (?:task|step)', 'delete'),
            ],
            # 添加步骤
            CorrectionType.ADD_STEP: [
                (r'增加(.+?)(任务|步骤)', 'add'),
                (r'添加(.+?)(任务|步骤)', 'add'),
                (r'新建(.+?)(任务|步骤)', 'add'),
                (r'增加一个(.+?)(任务|步骤)', 'add'),
                (r'添加一个(.+?)(任务|步骤)', 'add'),
                (r'add (.+?) (?:task|step)', 'add'),
                (r'create (.+?) (?:task|step)', 'add'),
            ],
            # 重新分配
            CorrectionType.REASSIGN: [
                (r'(.+?)(任务|步骤)改派给(.+?)(?:Agent|代理)', 'reassign'),
                (r'(.+?)(任务|步骤)交给(.+?)(?:Agent|代理)', 'reassign'),
                (r'(.+?)(任务|步骤)由(.+?)(?:Agent|代理)负责', 'reassign'),
                (r'reassign (.+?) to ([a-zA-Z0-9_-]+)', 'reassign'),
                (r'move (.+?) to ([a-zA-Z0-9_-]+)', 'reassign'),
            ],
            # 暂停
            CorrectionType.PAUSE_STEP: [
                (r'暂停(.+?)(任务|步骤)', 'pause'),
                (r'先暂停(.+?)(任务|步骤)', 'pause'),
                (r'pause (.+?) (?:task|step)', 'pause'),
            ],
            # 恢复
            CorrectionType.RESUME_STEP: [
                (r'恢复(.+?)(任务|步骤)', 'resume'),
                (r'继续(.+?)(任务|步骤)', 'resume'),
                (r'resume (.+?) (?:task|step)', 'resume'),
            ],
            # 取消
            CorrectionType.CANCEL_STEP: [
                (r'取消(.+?)(任务|步骤)', 'cancel'),
                (r'停止(.+?)(任务|步骤)', 'cancel'),
                (r'终止(.+?)(任务|步骤)', 'cancel'),
                (r'cancel (.+?) (?:task|step)', 'cancel'),
            ],
        }

    def parse(self, text: str) -> Optional[CorrectionRequest]:
        """
        解析自然语言指令

        :param text: 用户输入的指令
        :return: CorrectionRequest 或 None
        """
        text = text.strip()

        for correction_type, patterns in self._patterns.items():
            for pattern, action in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return self._build_request(text, correction_type, match, action)

        # 无法识别
        return CorrectionRequest(
            original=text,
            correction_type=CorrectionType.UNKNOWN,
            parsed_result={"raw": text},
            changes={},
        )

    def _build_request(self, text: str, corr_type: CorrectionType,
                       match: re.Match, action: str) -> CorrectionRequest:
        """构建修正请求"""
        groups = match.groups()

        if corr_type == CorrectionType.PRIORITY_RAISE:
            step_name = self._extract_step_name(groups[0] if groups else "")
            return CorrectionRequest(
                original=text,
                correction_type=corr_type,
                parsed_result={
                    "step_name": step_name,
                    "action": action,
                },
                changes={
                    "priority_delta": 100,  # 大幅提升
                    "target_priority": "highest",
                },
            )

        elif corr_type == CorrectionType.PRIORITY_LOWER:
            step_name = self._extract_step_name(groups[0] if groups else "")
            return CorrectionRequest(
                original=text,
                correction_type=corr_type,
                parsed_result={
                    "step_name": step_name,
                    "action": action,
                },
                changes={
                    "priority_delta": -50,
                },
            )

        elif corr_type == CorrectionType.DELETE_STEP:
            step_name = self._extract_step_name(groups[0] if groups else "")
            return CorrectionRequest(
                original=text,
                correction_type=corr_type,
                parsed_result={
                    "step_name": step_name,
                    "action": action,
                },
                changes={
                    "delete": True,
                },
            )

        elif corr_type == CorrectionType.ADD_STEP:
            step_name = self._extract_step_name(groups[0] if groups else "")
            return CorrectionRequest(
                original=text,
                correction_type=corr_type,
                parsed_result={
                    "step_name": step_name,
                    "action": action,
                },
                changes={
                    "add": True,
                    "name": step_name,
                },
            )

        elif corr_type == CorrectionType.REASSIGN:
            step_name = self._extract_step_name(groups[0] if groups else "")
            agent_name = groups[2] if len(groups) > 2 else (groups[-1] if groups else "")
            return CorrectionRequest(
                original=text,
                correction_type=corr_type,
                parsed_result={
                    "step_name": step_name,
                    "agent_name": agent_name.strip(),
                    "action": action,
                },
                changes={
                    "reassign": True,
                    "new_agent": agent_name.strip(),
                },
            )

        elif corr_type in (CorrectionType.PAUSE_STEP, CorrectionType.RESUME_STEP,
                          CorrectionType.CANCEL_STEP):
            step_name = self._extract_step_name(groups[0] if groups else "")
            return CorrectionRequest(
                original=text,
                correction_type=corr_type,
                parsed_result={
                    "step_name": step_name,
                    "action": action,
                },
                changes={},
            )

        # 默认
        return CorrectionRequest(
            original=text,
            correction_type=corr_type,
            parsed_result={"groups": groups, "action": action},
            changes={},
        )

    def _extract_step_name(self, text: str) -> str:
        """提取任务/步骤名称"""
        text = text.strip()

        # 移除常见前缀
        prefixes = ['这个', '那个', '这个', 'the ', 'a ', 'an ']
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):]

        # 移除常见后缀
        suffixes = ['任务', '步骤', 'task', 'step', '的工作']
        for suffix in suffixes:
            if text.endswith(suffix):
                text = text[:-len(suffix)]

        return text.strip()

# ============================================================================
# 修正引擎
# ============================================================================

class CorrectionEngine:
    """
    对话式修正引擎

    功能：
    - 解析用户自然语言指令
    - 应用修正到工作流/计划
    - 通知执行引擎
    """

    def __init__(self):
        self._parser = NaturalLanguageParser()
        self._lock = threading.RLock()
        self._correction_callbacks: List[Callable[[CorrectionRequest], Awaitable[None]]] = []

    def register_callback(self, callback: Callable[[CorrectionRequest], Awaitable[None]]):
        """注册修正回调（当修正应用时被调用）"""
        self._correction_callbacks.append(callback)

    async def process(self, workflow_id: str, instruction: str,
                     workflow_context: Dict[str, Any] = None) -> CorrectionResult:
        """
        处理修正指令

        :param workflow_id: 工作流 ID
        :param instruction: 自然语言指令
        :param workflow_context: 工作流上下文（包含steps等信息）
        :return: 修正结果
        """
        # 解析指令
        correction = self._parser.parse(instruction)
        correction.workflow_id = workflow_id

        if correction.correction_type == CorrectionType.UNKNOWN:
            return CorrectionResult(
                success=False,
                message=f"无法理解的指令: {instruction}",
                correction=correction,
            )

        # 查找对应的步骤
        steps = (workflow_context or {}).get("steps", [])
        step_name = correction.parsed_result.get("step_name", "")

        matched_step = self._find_step_by_name(steps, step_name) if step_name else None

        if not matched_step and correction.correction_type not in (CorrectionType.ADD_STEP,):
            return CorrectionResult(
                success=False,
                message=f"找不到任务/步骤: {step_name}",
                correction=correction,
            )

        correction.step_id = matched_step.get("id") if matched_step else None

        # 应用修正
        try:
            result = await self._apply_correction(workflow_id, correction, workflow_context)
            return result
        except Exception as e:
            logger.error(f"Failed to apply correction: {e}")
            return CorrectionResult(
                success=False,
                message=f"应用修正失败: {str(e)}",
                correction=correction,
            )

    def _find_step_by_name(self, steps: List[Dict], name: str) -> Optional[Dict]:
        """根据名称查找步骤"""
        name_lower = name.lower()

        # 精确匹配
        for step in steps:
            step_name = (step.get("name") or "").lower()
            if step_name == name_lower:
                return step

        # 包含匹配
        for step in steps:
            step_name = (step.get("name") or "").lower()
            if name_lower in step_name or step_name in name_lower:
                return step

        # 关键词匹配
        for step in steps:
            desc = ((step.get("description") or "") + (step.get("name") or "")).lower()
            if name_lower in desc:
                return step

        return None

    async def _apply_correction(self, workflow_id: str,
                                correction: CorrectionRequest,
                                workflow_context: Dict[str, Any] = None) -> CorrectionResult:
        """应用修正到工作流"""
        step_id = correction.step_id

        if correction.correction_type == CorrectionType.PRIORITY_RAISE:
            # 提升优先级 - 更新order使其更早执行
            return await self._apply_priority_change(
                workflow_id, step_id, correction, -100  # 负数表示提前
            )

        elif correction.correction_type == CorrectionType.PRIORITY_LOWER:
            # 降低优先级
            return await self._apply_priority_change(
                workflow_id, step_id, correction, 50
            )

        elif correction.correction_type == CorrectionType.DELETE_STEP:
            return await self._apply_delete_step(workflow_id, step_id, correction)

        elif correction.correction_type == CorrectionType.ADD_STEP:
            return await self._apply_add_step(workflow_id, correction, workflow_context)

        elif correction.correction_type == CorrectionType.REASSIGN:
            return await self._apply_reassign(
                workflow_id, step_id, correction, workflow_context
            )

        elif correction.correction_type == CorrectionType.PAUSE_STEP:
            return await self._apply_pause_step(workflow_id, step_id, correction)

        elif correction.correction_type == CorrectionType.RESUME_STEP:
            return await self._apply_resume_step(workflow_id, step_id, correction)

        elif correction.correction_type == CorrectionType.CANCEL_STEP:
            return await self._apply_cancel_step(workflow_id, step_id, correction)

        return CorrectionResult(
            success=False,
            message=f"不支持的修正类型: {correction.correction_type}",
            correction=correction,
        )

    async def _apply_priority_change(self, workflow_id: str, step_id: str,
                                     correction: CorrectionRequest,
                                     order_delta: int) -> CorrectionResult:
        """修改步骤优先级（通过调整order）"""
        # 通知执行引擎
        await self._notify_correction(correction)

        return CorrectionResult(
            success=True,
            message=f"已将 {correction.parsed_result.get('step_name')} 优先级调整",
            correction=correction,
            step_changes={
                "step_id": step_id,
                "order_delta": order_delta,
                "action": "priority_changed",
            }
        )

    async def _apply_delete_step(self, workflow_id: str, step_id: str,
                                 correction: CorrectionRequest) -> CorrectionResult:
        """删除步骤"""
        await self._notify_correction(correction)

        return CorrectionResult(
            success=True,
            message=f"已删除步骤: {correction.parsed_result.get('step_name')}",
            correction=correction,
            step_changes={
                "step_id": step_id,
                "action": "deleted",
            }
        )

    async def _apply_add_step(self, workflow_id: str,
                              correction: CorrectionRequest,
                              workflow_context: Dict[str, Any] = None) -> CorrectionResult:
        """添加新步骤"""
        step_data = {
            "name": correction.parsed_result.get("step_name", "新任务"),
            "description": f"动态添加: {correction.original}",
            "capabilities": self._infer_capabilities(correction.parsed_result.get("step_name", "")),
        }

        await self._notify_correction(correction)

        return CorrectionResult(
            success=True,
            message=f"已添加新步骤: {step_data['name']}",
            correction=correction,
            step_changes={
                "action": "added",
                "step_data": step_data,
            }
        )

    async def _apply_reassign(self, workflow_id: str, step_id: str,
                              correction: CorrectionRequest,
                              workflow_context: Dict[str, Any] = None) -> CorrectionResult:
        """重新分配Agent"""
        new_agent = correction.changes.get("new_agent", "")

        await self._notify_correction(correction)

        return CorrectionResult(
            success=True,
            message=f"已将 {correction.parsed_result.get('step_name')} 改派给 {new_agent}",
            correction=correction,
            step_changes={
                "step_id": step_id,
                "action": "reassigned",
                "new_agent_id": new_agent,
            }
        )

    async def _apply_pause_step(self, workflow_id: str, step_id: str,
                                correction: CorrectionRequest) -> CorrectionResult:
        """暂停步骤"""
        await self._notify_correction(correction)

        return CorrectionResult(
            success=True,
            message=f"已暂停: {correction.parsed_result.get('step_name')}",
            correction=correction,
            step_changes={
                "step_id": step_id,
                "action": "paused",
            }
        )

    async def _apply_resume_step(self, workflow_id: str, step_id: str,
                                 correction: CorrectionRequest) -> CorrectionResult:
        """恢复步骤"""
        await self._notify_correction(correction)

        return CorrectionResult(
            success=True,
            message=f"已恢复: {correction.parsed_result.get('step_name')}",
            correction=correction,
            step_changes={
                "step_id": step_id,
                "action": "resumed",
            }
        )

    async def _apply_cancel_step(self, workflow_id: str, step_id: str,
                                correction: CorrectionRequest) -> CorrectionResult:
        """取消步骤"""
        await self._notify_correction(correction)

        return CorrectionResult(
            success=True,
            message=f"已取消: {correction.parsed_result.get('step_name')}",
            correction=correction,
            step_changes={
                "step_id": step_id,
                "action": "cancelled",
            }
        )

    def _infer_capabilities(self, step_name: str) -> List[str]:
        """从步骤名称推断能力需求"""
        text = step_name.lower()
        capabilities = []

        capability_keywords = {
            'rescue': ['rescue', '搜救', '救援', '被困'],
            'medical': ['medical', '医疗', '救治', '伤员'],
            'fire': ['fire', '消防', '灭火'],
            'chemical': ['chemical', '化工', '危化'],
            'communication': ['communication', '通讯', '通信'],
            'transport': ['transport', '运输', '转运'],
        }

        for cap, keywords in capability_keywords.items():
            if any(kw in text for kw in keywords):
                capabilities.append(cap)

        return capabilities

    async def _notify_correction(self, correction: CorrectionRequest):
        """通知所有注册的回调"""
        for callback in self._correction_callbacks:
            try:
                await callback(correction)
            except Exception as e:
                logger.error(f"Correction callback error: {e}")

# ============================================================================
# 工厂函数
# ============================================================================

_correction_engine: Optional[CorrectionEngine] = None

def get_correction_engine() -> CorrectionEngine:
    """获取全局修正引擎实例"""
    global _correction_engine
    if _correction_engine is None:
        _correction_engine = CorrectionEngine()
    return _correction_engine
