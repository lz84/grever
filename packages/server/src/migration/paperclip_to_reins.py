"""
Paperclip → Reins 数据迁移脚本

将 Paperclip 中的 Goal/Issue/Project/Agent 历史数据迁移到 Reins。
支持一次性迁移 + 增量同步（基于 updatedAt 时间戳）。

用法:
    # 一次性全量迁移
    python -m reins.migration.paperclip_to_reins --paperclip-url http://127.0.0.1:3100 --company-id <id> --api-key <key>

    # 增量同步（只迁移上次之后更新的数据）
    python -m reins.migration.paperclip_to_reins --incremental --since 2026-04-14T00:00:00Z

    # 指定 Reins DB 路径
    python -m reins.migration.paperclip_to_reins --reins-db data/reins.db
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import requests
from sqlalchemy import create_engine, insert, select, update, text

logger = logging.getLogger(__name__)

# ========== 常量 ==========

# Paperclip → Reins 状态映射
GOAL_STATUS_MAP = {
    "draft": "created",
    "planned": "created",
    "in_progress": "active",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}

ISSUE_STATUS_MAP = {
    "backlog": "todo",
    "todo": "todo",
    "in_progress": "in_progress",
    "in_review": "in_progress",
    "done": "done",
    "blocked": "blocked",
    "cancelled": "cancelled",
}

# Paperclip priority (string) → Reins priority (int)
PRIORITY_MAP = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "urgent": 4,
}

# ID 截断长度（Reins 使用 String(32)）
ID_MAX_LENGTH = 32


# ========== 工具函数 ==========


def truncate_id(uuid_str: str) -> str:
    """将 UUID 截断为 32 字符以内（Reins ID 限制）"""
    if not uuid_str:
        return ""
    # UUID 标准格式是 36 字符（含连字符），去掉连字符后 32 字符
    cleaned = uuid_str.replace("-", "")
    return cleaned[:ID_MAX_LENGTH]


def parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    """解析 ISO 8601 时间戳"""
    if not ts_str:
        return None
    try:
        # Handle various formats
        ts_str = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def map_goal_status(pc_status: str) -> str:
    """映射 Goal 状态"""
    return GOAL_STATUS_MAP.get(pc_status, "created")


def map_issue_status(pc_status: str) -> str:
    """映射 Issue 状态"""
    return ISSUE_STATUS_MAP.get(pc_status, "todo")


def map_priority(pc_priority: str) -> int:
    """映射优先级为整数"""
    return PRIORITY_MAP.get(pc_priority, 2)


# ========== Paperclip API 客户端 ==========


class PaperclipClient:
    """Paperclip API 客户端，用于获取源数据"""

    def __init__(self, base_url: str, company_id: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.company_id = company_id
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def get_goals(self) -> list[dict]:
        """获取所有 Goals"""
        resp = self.session.get(f"{self.base_url}/api/companies/{self.company_id}/goals")
        resp.raise_for_status()
        return resp.json()

    def get_issues(self, status: str = "all", limit: int = 500) -> list[dict]:
        """获取 Issues（支持分页）"""
        params = {"limit": limit}
        if status != "all":
            params["status"] = status
        resp = self.session.get(f"{self.base_url}/api/companies/{self.company_id}/issues", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_projects(self) -> list[dict]:
        """获取所有 Projects"""
        resp = self.session.get(f"{self.base_url}/api/companies/{self.company_id}/projects")
        resp.raise_for_status()
        return resp.json()

    def get_agents(self) -> list[dict]:
        """获取所有 Agents"""
        resp = self.session.get(f"{self.base_url}/api/companies/{self.company_id}/agents")
        resp.raise_for_status()
        return resp.json()


# ========== Reins 数据库操作 ==========


class ReinsDB:
    """Reins 数据库操作封装"""

    def __init__(self, db_path: str = r"D:\work\research\agents-nexus\data\reins.db"):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)

    def create_tables(self):
        """创建 Reins 表结构"""
        from persistence.tables import metadata
        metadata.create_all(self.engine)

    def upsert_goal(self, goal: dict) -> str:
        """插入或更新 Goal"""
        goal_id = truncate_id(goal["id"])
        created_at = parse_timestamp(goal.get("createdAt"))
        updated_at = parse_timestamp(goal.get("updatedAt"))

        with self.engine.begin() as conn:
            # Check if exists
            existing = conn.execute(
                text("SELECT id FROM goals WHERE id = :id"),
                {"id": goal_id},
            ).fetchone()

            if existing:
                conn.execute(
                    text("""
                        UPDATE goals SET
                            title = :title,
                            description = :description,
                            parent_id = :parent_id,
                            status = :status,
                            updated_at = :updated_at
                        WHERE id = :id
                    """),
                    {
                        "id": goal_id,
                        "title": goal.get("title", ""),
                        "description": (goal.get("description") or "")[:2000],
                        "parent_id": truncate_id(goal["parentId"]) if goal.get("parentId") else None,
                        "status": map_goal_status(goal.get("status", "draft")),
                        "updated_at": updated_at,
                    },
                )
                return goal_id, "updated"
            else:
                conn.execute(
                    text("""
                        INSERT INTO goals (id, title, description, parent_id, status, progress, task_ids, created_at, updated_at)
                        VALUES (:id, :title, :description, :parent_id, :status, 0.0, '[]', :created_at, :updated_at)
                    """),
                    {
                        "id": goal_id,
                        "title": goal.get("title", ""),
                        "description": (goal.get("description") or "")[:2000],
                        "parent_id": truncate_id(goal["parentId"]) if goal.get("parentId") else None,
                        "status": map_goal_status(goal.get("status", "draft")),
                        "created_at": created_at,
                        "updated_at": updated_at,
                    },
                )
                return goal_id, "inserted"

    def upsert_project(self, project: dict) -> str:
        """插入或更新 Project"""
        project_id = truncate_id(project["id"])
        created_at = parse_timestamp(project.get("createdAt"))
        updated_at = parse_timestamp(project.get("updatedAt"))

        with self.engine.begin() as conn:
            existing = conn.execute(
                text("SELECT id FROM projects WHERE id = :id"),
                {"id": project_id},
            ).fetchone()

            if existing:
                conn.execute(
                    text("""
                        UPDATE projects SET
                            name = :name,
                            description = :description,
                            goal_id = :goal_id,
                            status = :status,
                            updated_at = :updated_at
                        WHERE id = :id
                    """),
                    {
                        "id": project_id,
                        "name": project.get("name", ""),
                        "description": (project.get("description") or "")[:2000],
                        "goal_id": truncate_id(project["goalId"]) if project.get("goalId") else None,
                        "status": project.get("status", "active"),
                        "updated_at": updated_at,
                    },
                )
                return project_id, "updated"
            else:
                conn.execute(
                    text("""
                        INSERT INTO projects (id, name, description, goal_id, status, members, task_ids, created_at, updated_at)
                        VALUES (:id, :name, :description, :goal_id, :status, '[]', '[]', :created_at, :updated_at)
                    """),
                    {
                        "id": project_id,
                        "name": project.get("name", ""),
                        "description": (project.get("description") or "")[:2000],
                        "goal_id": truncate_id(project["goalId"]) if project.get("goalId") else None,
                        "status": project.get("status", "active"),
                        "created_at": created_at,
                        "updated_at": updated_at,
                    },
                )
                return project_id, "inserted"

    def upsert_task(self, issue: dict) -> str:
        """将 Paperclip Issue 插入为 Reins Task"""
        task_id = truncate_id(issue["id"])
        created_at = parse_timestamp(issue.get("createdAt"))
        updated_at = parse_timestamp(issue.get("updatedAt"))
        started_at = parse_timestamp(issue.get("startedAt"))
        completed_at = parse_timestamp(issue.get("completedAt"))

        pc_status = issue.get("status", "todo")
        reins_status = map_issue_status(pc_status)

        # 如果 Issue 被 cancelled，在 Reins 中标记为 done（Reins 没有 cancelled 状态）
        if pc_status == "cancelled":
            reins_status = "done"

        with self.engine.begin() as conn:
            existing = conn.execute(
                text("SELECT id FROM tasks WHERE id = :id"),
                {"id": task_id},
            ).fetchone()

            result_text = None
            if pc_status == "done":
                result_text = "Task completed (migrated from Paperclip)"
            elif pc_status == "cancelled":
                result_text = "Task cancelled (migrated from Paperclip)"

            if existing:
                conn.execute(
                    text("""
                        UPDATE tasks SET
                            title = :title,
                            description = :description,
                            project_id = :project_id,
                            goal_id = :goal_id,
                            assigned_agent = :assigned_agent,
                            status = :status,
                            priority = :priority,
                            started_at = :started_at,
                            completed_at = :completed_at,
                            result = :result,
                            updated_at = :updated_at
                        WHERE id = :id
                    """),
                    {
                        "id": task_id,
                        "title": issue.get("title", ""),
                        "description": (issue.get("description") or "")[:5000],
                        "project_id": truncate_id(issue["projectId"]) if issue.get("projectId") else None,
                        "goal_id": truncate_id(issue["goalId"]) if issue.get("goalId") else None,
                        "assigned_agent": truncate_id(issue["assigneeAgentId"]) if issue.get("assigneeAgentId") else None,
                        "status": reins_status,
                        "priority": map_priority(issue.get("priority", "medium")),
                        "started_at": started_at,
                        "completed_at": completed_at,
                        "result": result_text,
                        "updated_at": updated_at,
                    },
                )
                return task_id, "updated"
            else:
                conn.execute(
                    text("""
                        INSERT INTO tasks (id, title, description, project_id, goal_id, assigned_agent,
                                          status, priority, dependencies, depends_on, created_at, updated_at,
                                          started_at, completed_at, estimated_hours, actual_hours, result)
                        VALUES (:id, :title, :description, :project_id, :goal_id, :assigned_agent,
                                :status, :priority, '[]', '[]', :created_at, :updated_at,
                                :started_at, :completed_at, NULL, NULL, :result)
                    """),
                    {
                        "id": task_id,
                        "title": issue.get("title", ""),
                        "description": (issue.get("description") or "")[:5000],
                        "project_id": truncate_id(issue["projectId"]) if issue.get("projectId") else None,
                        "goal_id": truncate_id(issue["goalId"]) if issue.get("goalId") else None,
                        "assigned_agent": truncate_id(issue["assigneeAgentId"]) if issue.get("assigneeAgentId") else None,
                        "status": reins_status,
                        "priority": map_priority(issue.get("priority", "medium")),
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "started_at": started_at,
                        "completed_at": completed_at,
                        "result": result_text,
                    },
                )
                return task_id, "inserted"

    def upsert_agent(self, agent: dict) -> str:
        """插入或更新 Agent"""
        agent_id = truncate_id(agent["id"])
        created_at = parse_timestamp(agent.get("createdAt"))
        updated_at = parse_timestamp(agent.get("updatedAt"))

        # 解析 capabilities
        capabilities_raw = agent.get("capabilities", "")
        if isinstance(capabilities_raw, str) and capabilities_raw:
            capabilities = capabilities_raw.split(",")
        elif isinstance(capabilities_raw, list):
            capabilities = capabilities_raw
        else:
            capabilities = []

        # 映射 agent 状态
        pc_status = agent.get("status", "idle")
        reins_status = "online" if pc_status in ("idle", "active", "running") else "offline"
        if pc_status == "terminated":
            reins_status = "offline"

        # 提取 adapter 地址
        adapter_config = agent.get("adapterConfig", {})
        address = adapter_config.get("url", "") if isinstance(adapter_config, dict) else ""

        # 触发模式
        trigger_mode = "sse"  # 默认 SSE
        if isinstance(adapter_config, dict):
            if adapter_config.get("adapterType") == "polling" or adapter_config.get("polling"):
                trigger_mode = "polling"

        metadata_json = json.dumps({
            "paperclip_role": agent.get("role"),
            "paperclip_title": agent.get("title"),
            "paperclip_adapter_type": agent.get("adapterType"),
            "migrated_from": "paperclip",
            "migrated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

        with self.engine.begin() as conn:
            existing = conn.execute(
                text("SELECT id FROM agents WHERE id = :id"),
                {"id": agent_id},
            ).fetchone()

            if existing:
                conn.execute(
                    text("""
                        UPDATE agents SET
                            name = :name,
                            capabilities = :capabilities,
                            status = :status,
                            address = :address,
                            metadata = :metadata,
                            trigger_mode = :trigger_mode,
                            last_heartbeat = :last_heartbeat
                        WHERE id = :id
                    """),
                    {
                        "id": agent_id,
                        "name": agent.get("name", ""),
                        "capabilities": json.dumps(capabilities, ensure_ascii=False),
                        "status": reins_status,
                        "address": address,
                        "metadata": metadata_json,
                        "trigger_mode": trigger_mode,
                        "last_heartbeat": updated_at,
                    },
                )
                return agent_id, "updated"
            else:
                conn.execute(
                    text("""
                        INSERT INTO agents (id, name, capabilities, status, address, metadata, load, current_tasks,
                                           trigger_mode, poll_interval_seconds, registered_at, last_heartbeat)
                        VALUES (:id, :name, :capabilities, :status, :address, :metadata, 0, 0,
                                :trigger_mode, 10, :registered_at, :last_heartbeat)
                    """),
                    {
                        "id": agent_id,
                        "name": agent.get("name", ""),
                        "capabilities": json.dumps(capabilities, ensure_ascii=False),
                        "status": reins_status,
                        "address": address,
                        "metadata": metadata_json,
                        "trigger_mode": trigger_mode,
                        "registered_at": created_at,
                        "last_heartbeat": updated_at,
                    },
                )
                return agent_id, "inserted"

    def get_stats(self) -> dict:
        """获取数据库统计"""
        with self.engine.connect() as conn:
            stats = {}
            for table in ["goals", "projects", "tasks", "agents"]:
                row = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                stats[table] = row[0] if row else 0
            return stats


# ========== 迁移编排 ==========


class PaperclipToReinsMigrator:
    """迁移编排器"""

    def __init__(
        self,
        paperclip_url: str,
        company_id: str,
        api_key: str,
        reins_db_path: str = r"D:\work\research\agents-nexus\data\reins.db",
        incremental: bool = False,
        since: Optional[str] = None,
    ):
        self.client = PaperclipClient(paperclip_url, company_id, api_key)
        self.db = ReinsDB(reins_db_path)
        self.incremental = incremental
        self.since = since  # ISO 8601 时间戳

        # 统计
        self.stats = {
            "goals": {"inserted": 0, "updated": 0, "skipped": 0},
            "projects": {"inserted": 0, "updated": 0, "skipped": 0},
            "tasks": {"inserted": 0, "updated": 0, "skipped": 0},
            "agents": {"inserted": 0, "updated": 0, "skipped": 0},
        }

    def _should_migrate(self, item: dict) -> bool:
        """检查是否应该迁移（增量模式）"""
        if not self.incremental:
            return True
        if not self.since:
            return True

        cutoff = parse_timestamp(self.since)
        if not cutoff:
            return True

        item_updated = parse_timestamp(item.get("updatedAt"))
        if not item_updated:
            return True

        return item_updated >= cutoff

    def migrate_goals(self):
        """迁移 Goals"""
        logger.info("Fetching goals from Paperclip...")
        goals = self.client.get_goals()
        logger.info(f"Found {len(goals)} goals")

        for goal in goals:
            if not self._should_migrate(goal):
                self.stats["goals"]["skipped"] += 1
                continue

            goal_id, action = self.db.upsert_goal(goal)
            self.stats["goals"][action] += 1
            logger.debug(f"  Goal {action}: {goal.get('title')} ({goal_id})")

        logger.info(f"Goals migrated: {self.stats['goals']}")

    def migrate_projects(self):
        """迁移 Projects"""
        logger.info("Fetching projects from Paperclip...")
        try:
            projects = self.client.get_projects()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning("Projects endpoint not found, skipping")
                return
            raise

        logger.info(f"Found {len(projects)} projects")

        for project in projects:
            if not self._should_migrate(project):
                self.stats["projects"]["skipped"] += 1
                continue

            project_id, action = self.db.upsert_project(project)
            self.stats["projects"][action] += 1
            logger.debug(f"  Project {action}: {project.get('name')} ({project_id})")

        logger.info(f"Projects migrated: {self.stats['projects']}")

    def migrate_tasks(self):
        """迁移 Issues → Tasks"""
        logger.info("Fetching issues from Paperclip...")
        issues = self.client.get_issues(status="all", limit=1000)
        logger.info(f"Found {len(issues)} issues")

        for issue in issues:
            if not self._should_migrate(issue):
                self.stats["tasks"]["skipped"] += 1
                continue

            task_id, action = self.db.upsert_task(issue)
            self.stats["tasks"][action] += 1
            logger.debug(f"  Task {action}: {issue.get('title', '')[:50]} ({task_id})")

        logger.info(f"Tasks migrated: {self.stats['tasks']}")

    def migrate_agents(self):
        """迁移 Agents"""
        logger.info("Fetching agents from Paperclip...")
        try:
            agents = self.client.get_agents()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning("Agents endpoint not found, skipping")
                return
            raise

        logger.info(f"Found {len(agents)} agents")

        for agent in agents:
            if not self._should_migrate(agent):
                self.stats["agents"]["skipped"] += 1
                continue

            agent_id, action = self.db.upsert_agent(agent)
            self.stats["agents"][action] += 1
            logger.debug(f"  Agent {action}: {agent.get('name')} ({agent_id})")

        logger.info(f"Agents migrated: {self.stats['agents']}")

    def run(self):
        """执行完整迁移"""
        logger.info("=" * 60)
        logger.info("Paperclip → Reins 数据迁移开始")
        mode = "增量" if self.incremental else "全量"
        logger.info(f"迁移模式: {mode}")
        if self.since:
            logger.info(f"增量起点: {self.since}")
        logger.info("=" * 60)

        # 确保表存在
        self.db.create_tables()

        # 按依赖顺序迁移：Agents → Goals → Projects → Tasks
        self.migrate_agents()
        self.migrate_goals()
        self.migrate_projects()
        self.migrate_tasks()

        # 最终统计
        logger.info("=" * 60)
        logger.info("迁移完成！")
        logger.info(f"数据库统计: {json.dumps(self.db.get_stats(), indent=2, ensure_ascii=False)}")
        logger.info(f"迁移统计:")
        for entity, counts in self.stats.items():
            logger.info(f"  {entity}: inserted={counts['inserted']}, updated={counts['updated']}, skipped={counts['skipped']}")
        logger.info("=" * 60)

        return self.stats


# ========== CLI 入口 ==========


def main():
    parser = argparse.ArgumentParser(description="Paperclip → Reins 数据迁移")
    parser.add_argument("--paperclip-url", default="http://127.0.0.1:3100", help="Paperclip API URL")
    parser.add_argument("--company-id", required=True, help="Company ID")
    parser.add_argument("--api-key", required=True, help="Paperclip API Key")
    parser.add_argument("--reins-db", default=r"D:\work\research\agents-nexus\data\reins.db", help="Reins 数据库路径")
    parser.add_argument("--incremental", action="store_true", help="增量同步模式")
    parser.add_argument("--since", help="增量同步起点 (ISO 8601)")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    migrator = PaperclipToReinsMigrator(
        paperclip_url=args.paperclip_url,
        company_id=args.company_id,
        api_key=args.api_key,
        reins_db_path=args.reins_db,
        incremental=args.incremental,
        since=args.since,
    )

    migrator.run()


if __name__ == "__main__":
    main()
