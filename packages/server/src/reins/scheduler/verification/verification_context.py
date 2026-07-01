"""
Verification Context Builder — 构建 Project/Goal 级验证上下文

职责：
1. 收集所有下属 Task/Project 的产出
2. 收集 planning_sessions 的讨论历史
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from loguru import logger

from models.task import Task
from models.project import Project
from models.goal import Goal
from models.planning_session import PlanningSession


class VerificationContextBuilder:
    """验证上下文构建器"""

    def __init__(self, db: Session):
        self.db = db

    def build_context(self, target_id: str, level: str) -> Dict[str, Any]:
        """
        构建验证上下文

        Args:
            target_id: Project.id 或 Goal.id
            level: 'project' | 'goal'

        Returns:
            验证上下文字典
        """
        context: Dict[str, Any] = {
            'level': level,
            'target_id': target_id,
            'task_results': [],
            'planning_context': None,
        }

        if level == 'project':
            context.update(self._build_project_context(target_id))
        else:
            context.update(self._build_goal_context(target_id))

        return context

    def _build_project_context(self, project_id: str) -> Dict[str, Any]:
        """构建 Project 级验证上下文"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {'error': f'Project {project_id} not found'}

        tasks = (
            self.db.query(Task)
            .filter(Task.project_id == project_id, Task.status != 'canceled')
            .all()
        )

        task_results = []
        for task in tasks:
            task_results.append({
                'task_id': task.id,
                'title': task.title,
                'status': task.status,
                'result_summary': task.result_summary or '',
                'assignment': task.assigned_agent or 'unassigned',
            })

        planning_context = self._get_planning_context(project.goal_id)

        return {
            'project_info': {
                'id': project.id,
                'name': project.name,
                'description': project.description or '',
                'status': project.status,
            },
            'task_results': task_results,
            'planning_context': planning_context,
        }

    def _build_goal_context(self, goal_id: str) -> Dict[str, Any]:
        """构建 Goal 级验证上下文"""
        goal = self.db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            return {'error': f'Goal {goal_id} not found'}

        projects = (
            self.db.query(Project)
            .filter(Project.goal_id == goal_id, Project.status != 'canceled')
            .all()
        )

        project_results = []
        for proj in projects:
            task_count = (
                self.db.query(Task)
                .filter(Task.project_id == proj.id, Task.status != 'canceled')
                .count()
            )
            done_count = (
                self.db.query(Task)
                .filter(Task.project_id == proj.id, Task.status == 'done')
                .count()
            )

            project_results.append({
                'project_id': proj.id,
                'name': proj.name,
                'description': proj.description or '',
                'status': proj.status,
                'task_done': done_count,
                'task_total': task_count,
                'progress': done_count / task_count if task_count > 0 else 0,
            })

        planning_context = self._get_planning_context(goal_id)

        return {
            'goal_info': {
                'id': goal.id,
                'title': goal.title,
                'description': goal.description or '',
                'status': goal.status,
            },
            'project_results': project_results,
            'planning_context': planning_context,
        }

    def _get_planning_context(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """获取 Goal 的 planning_session 上下文"""
        planning_session = (
            self.db.query(PlanningSession)
            .filter(
                PlanningSession.goal_id == goal_id,
                PlanningSession.status == 'confirmed'
            )
            .order_by(PlanningSession.confirmed_at.desc())
            .first()
        )

        if not planning_session:
            return None

        confirmed_plan = None
        if planning_session.confirmed_plan:
            try:
                confirmed_plan = json.loads(planning_session.confirmed_plan)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            'original_request': planning_session.input_content,
            'decision_rationale': planning_session.decision_rationale,
            'confirmed_plan': confirmed_plan,
            'created_at': planning_session.created_at,
        }
