"""
Nexus Agent Skill - Executor Module

Execution logic for reading task context, executing tasks, and reporting results.
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TaskContext:
    """任务上下文"""
    task_id: str
    title: str
    description: str
    priority: str
    goal_info: Optional[Dict[str, Any]] = None
    scenario_guide: Optional[Dict[str, Any]] = None
    related_files: List[str] = None
    previous_attempts: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.related_files is None:
            self.related_files = []
        if self.previous_attempts is None:
            self.previous_attempts = []


class NexusTaskExecutor:
    """执行器：读取上下文 → 执行任务 → 上报结果"""
    
    def __init__(self, nexus_url: Optional[str] = None, agent_id: Optional[str] = None):
        """
        初始化执行器
        
        Args:
            nexus_url: Nexus 后端 API 地址
            agent_id: Agent 唯一标识
        """
        self.nexus_url = nexus_url or os.getenv("NEXUS_URL", "http://localhost:8094")
        self.agent_id = agent_id or os.getenv("AGENT_ID", "default-agent")
        self.api_key = os.getenv("NEXUS_API_KEY")
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def get_task_context(self, task_id: str) -> Optional[TaskContext]:
        """
        获取任务上下文
        
        Args:
            task_id: 任务ID
            
        Returns:
            TaskContext 对象，如果任务不存在则返回 None
        """
        endpoint = f"{self.nexus_url}/api/v1/tasks/{task_id}/context"
        
        try:
            response = requests.get(
                endpoint,
                headers=self._build_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("success"):
                return None
            
            context_data = result.get("context", {})
            
            # 构建 TaskContext 对象
            related_files = context_data.get("related_files", [])
            previous_attempts = context_data.get("previous_attempts", [])
            
            return TaskContext(
                task_id=task_id,
                title=context_data.get("scenario_guide", {}).get("name", "Unknown Task"),
                description=context_data.get("scenario_guide", {}).get("description", ""),
                priority="medium",  # TODO: 从任务数据获取
                goal_info=context_data.get("goal_info"),
                scenario_guide=context_data.get("scenario_guide"),
                related_files=related_files,
                previous_attempts=previous_attempts
            )
            
        except requests.exceptions.RequestException as e:
            print(f"Error getting task context: {e}")
            return None
    
    def execute_task(self, context: TaskContext) -> Dict[str, Any]:
        """
        执行任务（模拟执行，实际由 Agent 的能力实现）
        
        Args:
            context: 任务上下文
            
        Returns:
            执行结果
        """
        # 这里是实际执行逻辑的占位符
        # 在实际实现中，应该调用 Agent 的能力来执行任务
        
        # 模拟执行过程
        execution_result = {
            "status": "done",
            "result": f"Task '{context.title}' executed successfully",
            "artifacts": context.related_files,
            "duration_ms": 1000,  # 模拟耗时
            "confidence": 0.95,
            "issues_encountered": []
        }
        
        return execution_result
    
    def report_complete(self, task_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        上报任务完成
        
        Args:
            task_id: 任务ID
            result: 执行结果
            
        Returns:
            上报响应
        """
        endpoint = f"{self.nexus_url}/api/v1/tasks/{task_id}/complete"
        
        duration_ms = result.get("duration_ms", 0)
        if duration_ms <= 0:
            duration_ms = 1000  # Nexus API requires > 0
        payload = {
            "status": result.get("status", "done"),
            "result": result.get("result", ""),
            "artifacts": result.get("artifacts", []),
            "duration_ms": duration_ms,
            "confidence": result.get("confidence", 0.0),
            "issues_encountered": result.get("issues_encountered", []),
            "execution_log": result.get("execution_log", {
                "steps": result.get("result", ""),
                "status": "completed"
            }),
        }
        
        try:
            response = requests.post(
                endpoint,
                headers=self._build_headers(),
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def report_fail(self, task_id: str, error_type: str, error_message: str) -> Dict[str, Any]:
        """
        上报任务失败
        
        Args:
            task_id: 任务ID
            error_type: 错误类型
            error_message: 错误详情
            
        Returns:
            上报响应
        """
        endpoint = f"{self.nexus_url}/api/v1/tasks/{task_id}/fail"
        
        payload = {
            "error_type": error_type,
            "error_message": error_message,
            "retry_count": 1,
            "max_retries": 3
        }
        
        try:
            response = requests.post(
                endpoint,
                headers=self._build_headers(),
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_single_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个任务（完整流程）
        
        Args:
            task: 任务信息（包含 task_id）
            
        Returns:
            执行结果
        """
        task_id = task.get("id")
        task_title = task.get("title", "Unknown Task")
        
        print(f"[{datetime.now()}] Starting task: {task_title} (ID: {task_id})")
        
        # 1. 获取任务上下文
        print(f"[{datetime.now()}] Getting task context...")
        context = self.get_task_context(task_id)
        
        if not context:
            print(f"[{datetime.now()}] Failed to get context for task {task_id}")
            return self.report_fail(
                task_id, 
                "context_error", 
                "Failed to retrieve task context"
            )
        
        # 2. 执行任务
        print(f"[{datetime.now()}] Executing task...")
        execution_result = self.execute_task(context)
        
        # 3. 上报结果
        print(f"[{datetime.now()}] Reporting result...")
        if execution_result.get("status") == "done":
            return self.report_complete(task_id, execution_result)
        else:
            return self.report_fail(
                task_id,
                execution_result.get("error_type", "execution_error"),
                execution_result.get("error_message", "Task execution failed")
            )
    
    def execute_all_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        执行所有任务
        
        Args:
            tasks: 任务列表
            
        Returns:
            每个任务的执行结果列表
        """
        results = []
        
        for task in tasks:
            result = self.execute_single_task(task)
            results.append({
                "task_id": task.get("id"),
                "task_title": task.get("title"),
                "result": result
            })
        
        return results


def executor_handler(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    主执行处理函数
    
    Args:
        tasks: 任务列表
        
    Returns:
        执行结果汇总
    """
    executor = NexusTaskExecutor()
    
    if not tasks:
        return {
            "executed": 0,
            "success": 0,
            "failed": 0,
            "results": []
        }
    
    results = executor.execute_all_tasks(tasks)
    
    success_count = sum(1 for r in results if r["result"].get("success", False))
    
    return {
        "executed": len(tasks),
        "success": success_count,
        "failed": len(tasks) - success_count,
        "results": results
    }


if __name__ == "__main__":
    # 本地测试
    # 模拟任务列表
    test_tasks = [
        {
            "id": "task-test-001",
            "title": "Test Task 1",
            "description": "Test description"
        }
    ]
    
    result = executor_handler(test_tasks)
    print(json.dumps(result, indent=2, ensure_ascii=False))
