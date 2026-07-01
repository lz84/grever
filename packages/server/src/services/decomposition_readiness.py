# -*- coding: utf-8 -*-
"""Evaluation Decomposition Readiness Service — E-1~E-4 评估分解就绪服务

实现文档 23 号 8.3 节的 E-1~E-4 评估分解流程：

E-1: Initial decomposition message → send to Coordinator Agent
E-2: Agent responds with decomposition OR insufficient + Tier 0 questions
E-3: Grever sends user answers back to Agent
E-4: Agent sends final result (sufficient + decomposition OR insufficient with default)

核心职责：
1. 分解就绪状态管理（ready / not_ready / hitl）
2. Tier 0 问题管理
3. 默认分解提取逻辑（from industry_pack scenario_templates）
4. E-1~E-4 流程状态机
"""
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import select

from loguru import logger


class DecompositionReadiness(str, Enum):
    """分解就绪状态"""
    READY = "ready"          # AI 理解充分，可直接分解
    NOT_READY = "not_ready"  # 缺乏关键信息，需 HITL
    HYBRID = "hybrid"         # 部分理解，混合模式


class EPhase(str, Enum):
    """E-1~E-4 流程阶段"""
    E1_SENDING = "e1_sending"
    E2_WAITING = "e2_waiting"
    E3_ANSWERING = "e3_answering"
    E4_FINAL = "e4_final"


@dataclass
class Tier0Question:
    """Tier 0 问题（缺乏的关键信息）"""
    question_id: str
    question_text: str
    question_type: str  # text | choice | number | boolean
    options: Optional[List[str]] = None
    default_answer: Optional[str] = None
    category: str = "general"  # scope | constraint | resource | quality
    answered: bool = False
    answer: Optional[str] = None


@dataclass
class DecompositionResult:
    """分解结果"""
    readiness: DecompositionReadiness
    projects: List[Dict[str, Any]] = field(default_factory=list)
    tier0_questions: List[Tier0Question] = field(default_factory=list)
    agent_message: str = ""
    default_applied: bool = False
    assumptions: List[str] = field(default_factory=list)


# ============================================================================
# E-1~E-4 Service
# ============================================================================

class EvaluationDecompositionService:
    """E-1~E-4 评估分解服务"""

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # E-1: 创建规划会话，发送初始分解消息给 Coordinator Agent
    # -------------------------------------------------------------------------
    def e1_start_decomposition(
        self,
        goal_id: str,
        goal_title: str,
        goal_description: str,
        coordinator_agent_id: Optional[str] = None,
        decomposition_mode: str = "auto",
    ) -> Tuple[str, str]:
        """
        E-1: 启动分解流程，创建 planning_session 和 goal_session

        Returns:
            (planning_session_id, goal_session_id)

        Raises:
            ValueError: goal_id 不存在
        """
        from models.goal import Goal
        from models.planning_session import PlanningSession
        from models.goal_session import GoalSession

        # 验证 goal 存在
        goal = self.db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        # 创建 planning_session
        planning_session = PlanningSession(
            id=f"ps-{uuid.uuid4().hex[:12]}",
            goal_id=goal_id,
            trigger_type="goal_creation",
            input_type="mixed",
            input_content=f"Title: {goal_title}\n\nDescription: {goal_description}",
            status="drafting",
            created_at=datetime.utcnow().isoformat(),
        )
        self.db.add(planning_session)

        # 创建 goal_session
        # session_id 由 Coordinator Agent 响应后更新，初始用空字符串满足 NOT NULL 约束
        goal_session = GoalSession(
            id=f"gs-{uuid.uuid4().hex[:12]}",
            goal_id=goal_id,
            session_type="decomposition",
            platform="openclaw",
            status="active",
            created_at=datetime.utcnow().isoformat(),
            messages=json.dumps([], ensure_ascii=False),
            session_id="",  # NOT NULL in DB，真实 session_id 由 Agent 响应后更新
        )
        self.db.add(goal_session)
        self.db.commit()

        logger.info(
            f"E-1: Started decomposition for goal {goal_id}, "
            f"planning_session={planning_session.id}, goal_session={goal_session.id}"
        )

        return planning_session.id, goal_session.id

    # -------------------------------------------------------------------------
    # E-2: 解析 Agent 响应，判断是否充分 + 提取 Tier 0 问题
    # -------------------------------------------------------------------------
    def e2_parse_agent_response(
        self,
        planning_session_id: str,
        agent_response: Dict[str, Any],
    ) -> DecompositionResult:
        """
        E-2: 解析 Coordinator Agent 的响应

        Args:
            planning_session_id: 规划会话 ID
            agent_response: Agent 返回的响应，格式：
                {
                    "sufficient": bool,
                    "decomposition": {...} | null,
                    "tier0_questions": [...] | null,
                    "message": str
                }

        Returns:
            DecompositionResult
        """
        from models.planning_session import PlanningSession

        planning = self.db.query(PlanningSession).filter(
            PlanningSession.id == planning_session_id
        ).first()
        if not planning:
            raise ValueError(f"PlanningSession {planning_session_id} not found")

        sufficient = agent_response.get("sufficient", False)
        decomposition = agent_response.get("decomposition")
        tier0_raw = agent_response.get("tier0_questions") or []
        message = agent_response.get("message", "")

        # 解析 Tier 0 问题
        tier0_questions = []
        for q in tier0_raw:
            tier0_questions.append(Tier0Question(
                question_id=q.get("question_id") or f"q-{uuid.uuid4().hex[:8]}",
                question_text=q.get("question_text", ""),
                question_type=q.get("question_type", "text"),
                options=q.get("options"),
                default_answer=q.get("default_answer"),
                category=q.get("category", "general"),
            ))

        # 构建结果
        result = DecompositionResult(
            readiness=DecompositionReadiness.READY if sufficient else DecompositionReadiness.NOT_READY,
            projects=decomposition.get("projects", []) if decomposition else [],
            tier0_questions=tier0_questions,
            agent_message=message,
        )

        # 更新 planning_session 状态
        if sufficient:
            planning.status = "pending_review"
            planning.confirmed_plan = json.dumps(decomposition, ensure_ascii=False)
            planning.decision_rationale = message
        else:
            planning.status = "drafting"
            # 保存 Tier 0 问题到 discussion_log
            existing = json.loads(planning.discussion_log or "[]")
            existing.append({
                "role": "agent",
                "content": message,
                "timestamp": datetime.utcnow().isoformat(),
                "tier0_questions": [q.__dict__ for q in tier0_questions],
            })
            planning.discussion_log = json.dumps(existing, ensure_ascii=False)

        self.db.commit()

        logger.info(
            f"E-2: Parsed agent response for planning {planning_session_id}, "
            f"sufficient={sufficient}, tier0_count={len(tier0_questions)}"
        )

        return result

    # -------------------------------------------------------------------------
    # E-3: 提交用户答案，继续分解流程
    # -------------------------------------------------------------------------
    def e3_submit_user_answers(
        self,
        planning_session_id: str,
        answers: Dict[str, str],
    ) -> str:
        """
        E-3: 用户提交 HITL 问题的答案

        Args:
            planning_session_id: 规划会话 ID
            answers: {question_id: answer} 格式的答案

        Returns:
            更新后的 planning_session 状态描述
        """
        from models.planning_session import PlanningSession

        planning = self.db.query(PlanningSession).filter(
            PlanningSession.id == planning_session_id
        ).first()
        if not planning:
            raise ValueError(f"PlanningSession {planning_session_id} not found")

        # 将答案追加到 discussion_log
        existing = json.loads(planning.discussion_log or "[]")
        existing.append({
            "role": "user",
            "content": json.dumps(answers, ensure_ascii=False),
            "timestamp": datetime.utcnow().isoformat(),
            "type": "hitl_answers",
        })
        planning.discussion_log = json.dumps(existing, ensure_ascii=False)

        planning.status = "e3_answered"
        self.db.commit()

        logger.info(
            f"E-3: User submitted {len(answers)} answers for planning {planning_session_id}"
        )

        return planning.status

    # -------------------------------------------------------------------------
    # E-4: 获取最终结果（含默认分解提取）
    # -------------------------------------------------------------------------
    def e4_get_final_result(
        self,
        planning_session_id: str,
        agent_final_response: Optional[Dict[str, Any]] = None,
    ) -> DecompositionResult:
        """
        E-4: 获取最终分解结果

        如果 Agent 仍返回 insufficient，则使用默认分解提取逻辑。
        """
        from models.planning_session import PlanningSession

        planning = self.db.query(PlanningSession).filter(
            PlanningSession.id == planning_session_id
        ).first()
        if not planning:
            raise ValueError(f"PlanningSession {planning_session_id} not found")

        # 如果有 Agent 最终响应，优先使用
        if agent_final_response:
            return self.e2_parse_agent_response(planning_session_id, agent_final_response)

        # 否则使用默认分解提取逻辑
        return self._extract_default_decomposition(planning)

    # -------------------------------------------------------------------------
    # 默认分解提取逻辑（文档 23 号 8.3 节）
    # -------------------------------------------------------------------------
    def _extract_default_decomposition(
        self,
        planning,
    ) -> DecompositionResult:
        """
        默认分解提取逻辑（文档 23 号 8.3 节）：

        1. 从 goals.matched_scenario_id 找到对应的 scenario
        2. 从 scenario.fullset 或 scenario.template_dag 提取模板
        3. 提取 default_projects 和 assumptions
        4. Fallback: 从 goal.context_md 解析

        Fallback: 如果都没有，创建单一默认项目
        """
        from models.goal import Goal
        from models.scenario import Scenario

        goal = self.db.query(Goal).filter(Goal.id == planning.goal_id).first()
        if not goal:
            return DecompositionResult(
                readiness=DecompositionReadiness.NOT_READY,
                default_applied=False,
            )

        projects = []
        assumptions = []

        # 优先从 matched_scenario 的 fullset 提取
        if goal.matched_scenario_id:
            scenario = self.db.query(Scenario).filter(
                Scenario.id == goal.matched_scenario_id
            ).first()
            if scenario:
                # scenario.fullset 存储 JSON: {default_projects: [...], assumptions: [...]}
                fullset_data = {}
                if scenario.fullset:
                    try:
                        fullset_data = json.loads(scenario.fullset)
                    except Exception:
                        pass
                if not fullset_data and scenario.template_dag:
                    try:
                        fullset_data = json.loads(scenario.template_dag)
                    except Exception:
                        pass
                projects = fullset_data.get("default_projects", fullset_data.get("projects", []))
                assumptions = fullset_data.get("assumptions", [])

        # Fallback: 从 goal.context_md 解析
        if not projects and goal.context_md:
            projects = self._parse_context_md(goal.context_md)

        # 最终 Fallback: 创建单一默认项目
        if not projects:
            projects = [{
                "name": goal.title or "Default Project",
                "description": goal.description or "",
                "priority": "medium",
                "category": "other",
                "depends_on": [],
                "deliverables": ["交付物1"],
                "estimated_effort": "M",
            }]
            assumptions = [
                "使用默认分解结构（信息不充分）",
            ]

        result = DecompositionResult(
            readiness=DecompositionReadiness.HYBRID,
            projects=projects,
            tier0_questions=[],
            agent_message="Applied default decomposition (insufficient information from agent)",
            default_applied=True,
            assumptions=assumptions,
        )

        # 更新 planning_session
        planning.confirmed_plan = json.dumps({"projects": projects, "assumptions": assumptions}, ensure_ascii=False)
        planning.status = "confirmed"

        self.db.commit()

        logger.info(
            f"Applied default decomposition for goal {planning.goal_id}, "
            f"projects={len(projects)}, default_applied=True"
        )

        return result

    def _parse_context_md(self, context_md: str) -> List[Dict[str, Any]]:
        """从 context_md 解析默认项目结构（简单实现）"""
        projects = []
        lines = context_md.split("\n")
        current_project = None

        for line in lines:
            line = line.strip()
            if line.startswith("## Project:"):
                if current_project:
                    projects.append(current_project)
                current_project = {
                    "name": line.replace("## Project:", "").strip(),
                    "tasks": [],
                }
            elif line.startswith("- [ ] ") or line.startswith("- [x] "):
                task_title = line[6:].strip()
                if current_project is None:
                    current_project = {"name": "Implied Project", "tasks": []}
                current_project["tasks"].append({
                    "title": task_title,
                    "type": "task",
                })

        if current_project:
            projects.append(current_project)

        return projects

    # -------------------------------------------------------------------------
    # 辅助方法
    # -------------------------------------------------------------------------
    def get_planning_session(self, planning_session_id: str):
        """获取 planning session"""
        from models.planning_session import PlanningSession
        return self.db.query(PlanningSession).filter(
            PlanningSession.id == planning_session_id
        ).first()

    def get_goal_session(self, goal_session_id: str):
        """获取 goal session"""
        from models.goal_session import GoalSession
        return self.db.query(GoalSession).filter(
            GoalSession.id == goal_session_id
        ).first()

    def update_goal_decomposition_status(
        self,
        goal_id: str,
        status: str,
        coordinator_agent_id: Optional[str] = None,
    ):
        """更新 goal 的分解状态"""
        from models.goal import Goal
        goal = self.db.query(Goal).filter(Goal.id == goal_id).first()
        if goal:
            goal.decomposition_status = status  # type: ignore
            if coordinator_agent_id:
                goal.coordinator_agent_id = coordinator_agent_id  # type: ignore
            self.db.commit()

    def mark_default_decomposition_used(self, goal_id: str):
        """标记 goal 使用了默认分解"""
        from models.goal import Goal
        goal = self.db.query(Goal).filter(Goal.id == goal_id).first()
        if goal:
            goal.default_decomposition_used = 1  # type: ignore
            self.db.commit()
