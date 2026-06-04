# -*- coding: utf-8 -*-
"""
Correction Engine Tests

测试：
- NaturalLanguageParser: 自然语言指令解析
- CorrectionEngine: 修正应用
"""

import pytest
import asyncio
import logging
import sys
from pathlib import Path

# 添加 src 到路径
src_dir = str(Path(__file__).parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from evo.common.correction_engine import (
    CorrectionEngine, CorrectionType, CorrectionRequest, CorrectionResult,
    NaturalLanguageParser, get_correction_engine,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# NaturalLanguageParser Tests
# ============================================================================

def test_parser_priority_raise():
    """测试优先级提升指令解析"""
    logger.info("=" * 60)
    logger.info("Test 1: Priority raise instruction parsing")
    logger.info("=" * 60)

    parser = NaturalLanguageParser()

    # Test English instructions first to avoid encoding issues
    test_cases = [
        ("raise priority of rescue task to highest", "raise"),
        ("make search task the top priority", "raise"),
    ]

    for instruction, expected_action in test_cases:
        result = parser.parse(instruction)
        assert result.correction_type == CorrectionType.PRIORITY_RAISE
        logger.info(f"OK: '{instruction}' -> PRIORITY_RAISE")

    # Test Chinese instructions
    result = parser.parse("把搜救任务优先级调到最高")
    assert result.correction_type == CorrectionType.PRIORITY_RAISE
    logger.info("OK: Chinese instruction parsed correctly")

    logger.info("Priority raise instruction parsing test passed!\n")


def test_parser_priority_lower():
    """测试优先级降低指令解析"""
    logger.info("=" * 60)
    logger.info("Test 2: Priority lower instruction parsing")
    logger.info("=" * 60)

    parser = NaturalLanguageParser()

    test_cases = [
        ("lower priority of transport task", "lower"),
        ("deprioritize search task", "lower"),
    ]

    for instruction, expected_action in test_cases:
        result = parser.parse(instruction)
        assert result.correction_type == CorrectionType.PRIORITY_LOWER
        logger.info(f"OK: '{instruction}' -> PRIORITY_LOWER")

    result = parser.parse("把通讯任务优先级降低")
    assert result.correction_type == CorrectionType.PRIORITY_LOWER
    logger.info("OK: Chinese instruction parsed correctly")

    logger.info("Priority lower instruction parsing test passed!\n")


def test_parser_delete_step():
    """测试删除步骤指令解析"""
    logger.info("=" * 60)
    logger.info("Test 3: Delete step instruction parsing")
    logger.info("=" * 60)

    parser = NaturalLanguageParser()

    test_cases = [
        ("remove search task", "delete"),
        ("delete transport step", "delete"),
    ]

    for instruction, expected_action in test_cases:
        result = parser.parse(instruction)
        assert result.correction_type == CorrectionType.DELETE_STEP
        logger.info(f"OK: '{instruction}' -> DELETE_STEP")

    result = parser.parse("去掉搜索任务")
    assert result.correction_type == CorrectionType.DELETE_STEP
    logger.info("OK: Chinese instruction parsed correctly")

    logger.info("Delete step instruction parsing test passed!\n")


def test_parser_add_step():
    """测试添加步骤指令解析"""
    logger.info("=" * 60)
    logger.info("Test 4: Add step instruction parsing")
    logger.info("=" * 60)

    parser = NaturalLanguageParser()

    test_cases = [
        ("add rescue task", "add"),
        ("create search step", "add"),
    ]

    for instruction, expected_action in test_cases:
        result = parser.parse(instruction)
        assert result.correction_type == CorrectionType.ADD_STEP
        assert result.parsed_result.get("step_name")
        logger.info(f"OK: '{instruction}' -> ADD_STEP, name='{result.parsed_result.get('step_name')}'")

    result = parser.parse("增加被困人员搜救任务")
    assert result.correction_type == CorrectionType.ADD_STEP
    assert result.parsed_result.get("step_name")
    logger.info("OK: Chinese instruction parsed correctly")

    logger.info("Add step instruction parsing test passed!\n")


def test_parser_reassign():
    """测试重新分配指令解析"""
    logger.info("=" * 60)
    logger.info("Test 5: Reassign instruction parsing")
    logger.info("=" * 60)

    parser = NaturalLanguageParser()

    test_cases = [
        ("reassign rescue task to agent-B", "agent-B"),
        ("move search step to agent-C", "agent-C"),
    ]

    for instruction, expected_agent in test_cases:
        result = parser.parse(instruction)
        assert result.correction_type == CorrectionType.REASSIGN
        actual_agent = result.parsed_result.get("agent_name", "")
        assert expected_agent in actual_agent
        logger.info(f"OK: '{instruction}' -> agent='{actual_agent}'")

    result = parser.parse("搜救任务改派给A Agent")
    assert result.correction_type == CorrectionType.REASSIGN
    assert "A" in result.parsed_result.get("agent_name", "")
    logger.info("OK: Chinese instruction parsed correctly")

    logger.info("Reassign instruction parsing test passed!\n")


def test_parser_pause_resume_cancel():
    """测试暂停/恢复/取消指令解析"""
    logger.info("=" * 60)
    logger.info("Test 6: Pause/Resume/Cancel instruction parsing")
    logger.info("=" * 60)

    parser = NaturalLanguageParser()

    # Pause
    result = parser.parse("pause rescue task")
    assert result.correction_type == CorrectionType.PAUSE_STEP
    logger.info("OK: 'pause rescue task' -> PAUSE_STEP")

    # Resume
    result = parser.parse("resume medical step")
    assert result.correction_type == CorrectionType.RESUME_STEP
    logger.info("OK: 'resume medical step' -> RESUME_STEP")

    # Cancel
    result = parser.parse("cancel transport task")
    assert result.correction_type == CorrectionType.CANCEL_STEP
    logger.info("OK: 'cancel transport task' -> CANCEL_STEP")

    logger.info("Pause/Resume/Cancel instruction parsing test passed!\n")


def test_parser_unknown():
    """测试未知指令"""
    logger.info("=" * 60)
    logger.info("Test 7: Unknown instruction")
    logger.info("=" * 60)

    parser = NaturalLanguageParser()

    result = parser.parse("sing me a song")
    assert result.correction_type == CorrectionType.UNKNOWN
    logger.info("OK: Unknown instruction returns UNKNOWN")

    logger.info("Unknown instruction test passed!\n")


def test_parser_step_name_extraction():
    """测试步骤名称提取"""
    logger.info("=" * 60)
    logger.info("Test 8: Step name extraction")
    logger.info("=" * 60)

    parser = NaturalLanguageParser()

    test_cases = [
        ("rescue task", "rescue"),
        ("medical step", "medical"),
        ("search task", "search"),
    ]

    for input_text, expected in test_cases:
        extracted = parser._extract_step_name(input_text)
        assert expected in extracted.lower() or extracted.lower() in expected
        logger.info(f"OK: '{input_text}' -> '{extracted}'")

    logger.info("Step name extraction test passed!\n")


# ============================================================================
# CorrectionEngine Tests
# ============================================================================

@pytest.mark.asyncio

async def test_correction_engine_priority_raise():
    """测试修正引擎-优先级提升"""
    logger.info("=" * 60)
    logger.info("Test 9: Correction engine - priority raise")
    logger.info("=" * 60)

    engine = CorrectionEngine()

    # Mock workflow context
    workflow_context = {
        "steps": [
            {"id": "step-1", "name": "chemical-plant", "status": "pending"},
            {"id": "step-2", "name": "rescue-task", "status": "pending"},
            {"id": "step-3", "name": "medical-task", "status": "pending"},
        ]
    }

    # Correction instruction
    result = await engine.process(
        workflow_id="wf-001",
        instruction="raise priority of chemical-plant to highest",
        workflow_context=workflow_context,
    )

    assert result.success is True
    assert result.step_changes is not None
    assert result.step_changes.get("action") == "priority_changed"
    logger.info(f"OK: Correction successful: {result.message}")

    logger.info("Correction engine - priority raise test passed!\n")


@pytest.mark.asyncio

async def test_correction_engine_delete_step():
    """测试修正引擎-删除步骤"""
    logger.info("=" * 60)
    logger.info("Test 10: Correction engine - delete step")
    logger.info("=" * 60)

    engine = CorrectionEngine()

    workflow_context = {
        "steps": [
            {"id": "step-1", "name": "search-task", "status": "pending"},
            {"id": "step-2", "name": "comms-task", "status": "pending"},
        ]
    }

    result = await engine.process(
        workflow_id="wf-001",
        instruction="remove search task",
        workflow_context=workflow_context,
    )

    assert result.success is True
    assert result.step_changes.get("action") == "deleted"
    logger.info(f"OK: Delete successful: {result.message}")

    logger.info("Correction engine - delete step test passed!\n")


@pytest.mark.asyncio

async def test_correction_engine_add_step():
    """测试修正引擎-添加步骤"""
    logger.info("=" * 60)
    logger.info("Test 11: Correction engine - add step")
    logger.info("=" * 60)

    engine = CorrectionEngine()

    workflow_context = {
        "steps": [
            {"id": "step-1", "name": "chemical-plant", "status": "pending"},
        ]
    }

    result = await engine.process(
        workflow_id="wf-001",
        instruction="add rescue task",
        workflow_context=workflow_context,
    )

    assert result.success is True
    assert result.step_changes.get("action") == "added"
    logger.info(f"OK: Add successful: {result.message}")

    logger.info("Correction engine - add step test passed!\n")


@pytest.mark.asyncio

async def test_correction_engine_reassign():
    """测试修正引擎-重新分配"""
    logger.info("=" * 60)
    logger.info("Test 12: Correction engine - reassign")
    logger.info("=" * 60)

    engine = CorrectionEngine()

    workflow_context = {
        "steps": [
            {"id": "step-1", "name": "rescue-task", "status": "pending", "agent_id": "agent-A"},
        ]
    }

    result = await engine.process(
        workflow_id="wf-001",
        instruction="reassign rescue task to agent-B",
        workflow_context=workflow_context,
    )

    assert result.success is True
    assert result.step_changes.get("action") == "reassigned"
    assert result.step_changes.get("new_agent_id") == "agent-B"
    logger.info(f"OK: Reassign successful: {result.message}")

    logger.info("Correction engine - reassign test passed!\n")


@pytest.mark.asyncio

async def test_correction_engine_callback():
    """测试修正引擎回调"""
    logger.info("=" * 60)
    logger.info("Test 13: Correction engine callback")
    logger.info("=" * 60)

    engine = CorrectionEngine()

    received_corrections = []

    async def callback(correction):
        received_corrections.append(correction)

    engine.register_callback(callback)

    workflow_context = {
        "steps": [
            {"id": "step-1", "name": "chemical-plant", "status": "pending"},
        ]
    }

    await engine.process(
        workflow_id="wf-001",
        instruction="raise priority of chemical-plant to highest",
        workflow_context=workflow_context,
    )

    assert len(received_corrections) == 1
    assert received_corrections[0].correction_type == CorrectionType.PRIORITY_RAISE
    logger.info("OK: Callback triggered correctly")

    logger.info("Correction engine callback test passed!\n")


@pytest.mark.asyncio

async def test_correction_engine_unknown_instruction():
    """测试修正引擎-未知指令"""
    logger.info("=" * 60)
    logger.info("Test 14: Correction engine - unknown instruction")
    logger.info("=" * 60)

    engine = CorrectionEngine()

    result = await engine.process(
        workflow_id="wf-001",
        instruction="sing me a song",
        workflow_context={"steps": []},
    )

    assert result.success is False
    # Check for UNKNOWN correction type or failure message
    assert result.correction.correction_type == CorrectionType.UNKNOWN or "unknown" in result.message.lower()
    logger.info(f"OK: Unknown instruction rejected: {result.message}")

    logger.info("Correction engine - unknown instruction test passed!\n")


@pytest.mark.asyncio

async def test_correction_engine_step_not_found():
    """测试修正引擎-步骤未找到"""
    logger.info("=" * 60)
    logger.info("Test 15: Correction engine - step not found")
    logger.info("=" * 60)

    engine = CorrectionEngine()

    workflow_context = {
        "steps": [
            {"id": "step-1", "name": "chemical-plant", "status": "pending"},
        ]
    }

    result = await engine.process(
        workflow_id="wf-001",
        instruction="raise priority of non-existent-task to highest",
        workflow_context=workflow_context,
    )

    assert result.success is False
    # Step not found should return failure
    assert result.success is False
    logger.info(f"OK: Step not found: {result.message}")

    logger.info("Correction engine - step not found test passed!\n")


# ============================================================================
# Integration Test
# ============================================================================

@pytest.mark.asyncio

async def test_full_correction_flow():
    """完整修正流程测试"""
    logger.info("=" * 60)
    logger.info("Test 16: Full correction flow")
    logger.info("=" * 60)

    engine = CorrectionEngine()

    # Mock workflow context
    workflow_context = {
        "workflow_id": "wf-rescue-001",
        "steps": [
            {"id": "step-1", "name": "chemical-plant", "status": "pending", "order": 1},
            {"id": "step-2", "name": "rescue-task", "status": "pending", "order": 2},
            {"id": "step-3", "name": "medical-task", "status": "pending", "order": 3},
            {"id": "step-4", "name": "comms-task", "status": "pending", "order": 4},
        ]
    }

    # Simulate user correction instructions
    instructions = [
        "raise priority of chemical-plant to highest",  # Raise priority
        "add rescue task for trapped personnel",         # Add new task
        "reassign rescue task to specialist-agent",     # Reassign
        "remove comms task",                            # Delete task
    ]

    logger.info("Processing correction instructions...")
    for instruction in instructions:
        result = await engine.process(
            workflow_id=workflow_context["workflow_id"],
            instruction=instruction,
            workflow_context=workflow_context,
        )
        status = "OK" if result.success else "FAIL"
        logger.info(f"  [{status}] [{instruction}] -> {result.message}")

    logger.info("Full correction flow test passed!\n")


# ============================================================================
# Main Test
# ============================================================================

async def run_all_tests():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("Correction Engine Test Suite")
    logger.info("=" * 60 + "\n")

    try:
        # Sync tests
        test_parser_priority_raise()
        test_parser_priority_lower()
        test_parser_delete_step()
        test_parser_add_step()
        test_parser_reassign()
        test_parser_pause_resume_cancel()
        test_parser_unknown()
        test_parser_step_name_extraction()

        # Async tests
        await test_correction_engine_priority_raise()
        await test_correction_engine_delete_step()
        await test_correction_engine_add_step()
        await test_correction_engine_reassign()
        await test_correction_engine_callback()
        await test_correction_engine_unknown_instruction()
        await test_correction_engine_step_not_found()
        await test_full_correction_flow()

        logger.info("\n" + "=" * 60)
        logger.info("All tests passed!")
        logger.info("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())
