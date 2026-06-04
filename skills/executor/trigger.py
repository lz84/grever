"""
Nexus Agent Skill - Trigger Module

Trigger logic for checking assigned tasks during Agent heartbeat.
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional


class NexusTaskTrigger:
    """触发器：检查 heartbeat 响应中的 assigned_tasks"""
    
    def __init__(self, nexus_url: Optional[str] = None, agent_id: Optional[str] = None):
        """
        初始化触发器
        
        Args:
            nexus_url: Nexus 后端 API 地址
            agent_id: Agent 唯一标识
        """
        self.nexus_url = nexus_url or os.getenv("NEXUS_URL", "http://localhost:8000")
        self.agent_id = agent_id or os.getenv("AGENT_ID", "default-agent")
        self.api_key = os.getenv("NEXUS_API_KEY")
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def check_assigned_tasks(self, agent_status: str = "online") -> Dict[str, Any]:
        """
        执行 heartbeat 并检查分配的任务
        
        Args:
            agent_status: Agent 状态（online/idle/offline）
            
        Returns:
            包含 assigned_tasks 和负载信息的响应
        """
        endpoint = f"{self.nexus_url}/api/v1/agents/{self.agent_id}/heartbeat"
        
        payload = {
            "status": agent_status,
        }
        
        try:
            response = requests.post(
                endpoint,
                headers=self._build_headers(),
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": result.get("success", False),
                "assigned_tasks": result.get("assigned_tasks", []),
                "load_limit_warning": result.get("load_limit_warning", False),
                "error": None
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "assigned_tasks": [],
                "load_limit_warning": False,
                "error": str(e)
            }
    
    def has_new_tasks(self) -> bool:
        """
        检查是否有新任务待执行
        
        Returns:
            True 如果有新任务，False 否则
        """
        result = self.check_assigned_tasks()
        return len(result["assigned_tasks"]) > 0
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """
        获取分配的任务列表
        
        Returns:
            任务列表
        """
        result = self.check_assigned_tasks()
        return result["assigned_tasks"]


def trigger_handler() -> Dict[str, Any]:
    """
    主触发处理函数
    
    Returns:
        处理结果
    """
    trigger = NexusTaskTrigger()
    
    # 检查是否有新任务
    if not trigger.has_new_tasks():
        return {
            "triggered": False,
            "message": "No new tasks assigned",
            "tasks": []
        }
    
    # 获取任务列表
    tasks = trigger.get_tasks()
    
    return {
        "triggered": True,
        "message": f"Found {len(tasks)} new task(s)",
        "tasks": tasks
    }


if __name__ == "__main__":
    # 本地测试
    result = trigger_handler()
    print(json.dumps(result, indent=2, ensure_ascii=False))
