"""
Remediation Task Creator — 根据统筹验证结果创建补救任务

职责：
1. 根据 remedial_tasks 列表创建新的 Task 记录
2. 设置正确的依赖关系和继承属性
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from loguru import logger

from models.task import Task
from models.project import Project


class RemediationTaskCreator:
    """补救任务创建器"""

    def __init__(self, db: Session):
        self.db = db

    def create_remediation_tasks(
        self, target_id: str, level: str, tasks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        根据 remedial_tasks 创建补救 Task

        Args:
            target_id: Project.id 或 Goal.id
            level: 'project' | 'goal'
            tasks: [{'title', 'description', 'priority', 'depends_on', ...}]

        Returns:
            创建的 Task ID 列表
        """
        task_ids = []

        for task_data in tasks:
            task_id = self._create_single_task(target_id, level, task_data)
            if task_id:
                task_ids.append(task_id)

        self.db.commit()

        logger.info(
            f"[RemediationTaskCreator] Created {len(task_ids)} remediation tasks "
            f"for {level} {target_id}"
        )

        return task_ids

    def _create_single_task(
        self, target_id: str, level: str, task_data: Dict[str, Any]
    ) -> str:
        """创建单个补救任务"""
        task_id = task_data.get('id') or f"rem-{uuid.uuid4().hex[:12]}"

        task = Task(
            id=task_id,
            title=task_data.get('title', '补救任务'),
            description=task_data.get('description', ''),
            status='todo',
            priority=task_data.get('priority', 'medium'),
            project_id=target_id if level == 'project' else None,
            goal_id=target_id if level == 'goal' else None,
            assigned_agent=task_data.get('assigned_agent'),
            created_at=int(datetime.utcnow().timestamp()),
            updated_at=int(datetime.utcnow().timestamp()),
        )

        # 继承 Project 的 capability_tags
        if level == 'project' and task_data.get('capability_tags'):
            task.capability_tags = json.dumps(
                task_data['capability_tags'], ensure_ascii=False
            )
        elif level == 'project':
            project = self.db.query(Project).filter(
                Project.id == target_id
            ).first()
            if project and project.capability_tags:
                task.capability_tags = project.capability_tags

        # 设置 depends_on
        if task_data.get('depends_on'):
            task.depends_on = json.dumps(
                task_data['depends_on'], ensure_ascii=False
            )

        self.db.add(task)
        return task_id
