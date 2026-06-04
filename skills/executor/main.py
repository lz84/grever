"""
Nexus Agent Skill - Main Entry Point

主执行入口，整合 trigger 和 executor。
当 Agent 心跳时调用此模块。
"""

import os
import sys
import json
from typing import Dict, Any

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trigger import NexusTaskTrigger, trigger_handler
from executor import NexusTaskExecutor, executor_handler


def main_handler() -> Dict[str, Any]:
    """
    主处理函数
    
    执行流程：
    1. trigger.py: 检查 heartbeat 并获取 assigned_tasks
    2. executor.py: 执行任务并上报结果
    """
    print("=" * 60)
    print("Nexus Agent Skill - Starting execution")
    print("=" * 60)
    
    # Step 1: Trigger - 检查并获取任务
    print("\n[Step 1] Trigger: Checking for assigned tasks...")
    trigger_result = trigger_handler()
    
    if not trigger_result.get("triggered", False):
        return {
            "status": "no_tasks",
            "message": trigger_result.get("message", "No tasks assigned"),
            "tasks_count": 0
        }
    
    tasks = trigger_result.get("tasks", [])
    print(f"Found {len(tasks)} task(s) to execute")
    
    if not tasks:
        return {
            "status": "no_tasks",
            "message": "No tasks found in trigger result",
            "tasks_count": 0
        }
    
    # Step 2: Executor - 执行任务
    print(f"\n[Step 2] Executor: Starting task execution...")
    executor_result = executor_handler(tasks)
    
    # 汇总结果
    executed = executor_result.get("executed", 0)
    success = executor_result.get("success", 0)
    failed = executor_result.get("failed", 0)
    
    # Step 3: 返回最终结果
    final_result = {
        "status": "completed",
        "summary": {
            "total_tasks": len(tasks),
            "executed": executed,
            "success": success,
            "failed": failed,
            "success_rate": success / executed * 100 if executed > 0 else 0
        },
        "details": executor_result.get("results", [])
    }
    
    print("\n" + "=" * 60)
    print("Nexus Agent Skill - Execution completed")
    print(f"Total: {executed}, Success: {success}, Failed: {failed}")
    print("=" * 60)
    
    return final_result


if __name__ == "__main__":
    result = main_handler()
    print(json.dumps(result, indent=2, ensure_ascii=False))
