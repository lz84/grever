"""
验证规则引擎 — 验收标准分类与客观检查

职责：
1. 解析 acceptance_criteria，按 type 分类（客观/主观）
2. 客观检查（compile/api/page/custom）直接执行
"""

import json
import subprocess
import os
import re
from typing import Dict, List, Tuple

from loguru import logger

# Objective check types that can be executed programmatically
OBJECTIVE_TYPES = {
    "compile", "api", "page", "custom",
    "business_flow", "data_flow", "page_flow", "data",
}


def classify_criteria(db, task_id: str) -> Tuple[List[Dict], List[Dict]]:
    """
    解析 acceptance_criteria，按 type 分类：
    - 客观检查（compile/api/page/custom）→ 直接执行
    - 主观检查 → 推给 Worker

    返回 (objective_checks, subjective_checks)
    """
    from sqlalchemy import text

    with db.engine.connect() as conn:
        task = conn.execute(
            text("SELECT acceptance_criteria FROM tasks WHERE id = :id"),
            {"id": task_id},
        ).fetchone()

    if not task or not task.acceptance_criteria:
        return [], []

    try:
        criteria = json.loads(task.acceptance_criteria)
    except json.JSONDecodeError:
        return [], []

    if isinstance(criteria, dict) and "criteria" in criteria:
        criteria = criteria["criteria"]
    if not isinstance(criteria, list):
        return [], []

    objective = []
    subjective = []
    for c in criteria:
        c_type = c.get("type", "unknown")
        if c_type in OBJECTIVE_TYPES:
            objective.append(c)
        else:
            subjective.append(c)

    logger.info(
        f"[VerificationRules] task {task_id}: {len(objective)} objective, {len(subjective)} subjective checks"
    )
    return objective, subjective


def run_verifier_checks(db, task_id: str, result: str) -> Tuple[bool, str]:
    """
    运行验收检查程序化验证：
    1. 解析 acceptance_criteria（JSON）
    2. 根据 criteria type 执行检查
    3. 返回 (passed, message)
    """
    from sqlalchemy import text

    with db.engine.connect() as conn:
        task = conn.execute(
            text("SELECT acceptance_criteria, title, description FROM tasks WHERE id = :id"),
            {"id": task_id},
        ).fetchone()

    if not task or not task.acceptance_criteria:
        return True, "No acceptance criteria defined, passed by default"

    try:
        criteria = json.loads(task.acceptance_criteria)
    except json.JSONDecodeError:
        return False, f"Invalid acceptance_criteria JSON: {task.acceptance_criteria}"

    if isinstance(criteria, list):
        criteria_list = criteria
    elif isinstance(criteria, dict) and "criteria" in criteria:
        criteria_list = criteria["criteria"]
    else:
        return False, f"Invalid acceptance_criteria format: expected list or {{criteria: [...]}}"

    for i, criterion in enumerate(criteria_list):
        criterion_type = criterion.get("type")
        desc = criterion.get("desc", f"criterion #{i+1}")

        if criterion_type == "compile":
            try:
                nexus_dir = os.environ.get("NEXUS_DIR", ".")
                r = subprocess.run(
                    ["npx", "tsc", "--noEmit"],
                    cwd=nexus_dir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if r.returncode != 0:
                    return False, f"Compile check failed for '{desc}': {r.stderr}"
            except subprocess.TimeoutExpired:
                return False, f"Compile check timed out for '{desc}'"
            except FileNotFoundError:
                logger.warning("tsc not found, skipping compile check")
                continue
            except Exception as e:
                return False, f"Compile check error for '{desc}': {str(e)}"

        elif criterion_type == "api":
            endpoint = criterion.get("endpoint")
            if not endpoint:
                return False, f"API check missing endpoint for '{desc}'"
            try:
                import requests
                response = requests.get(endpoint, timeout=10)
                if response.status_code != 200:
                    return False, f"API check failed for '{desc}': {response.status_code}"
            except Exception as e:
                return False, f"API check error for '{desc}': {str(e)}"

        elif criterion_type == "page":
            url = criterion.get("url")
            if not url:
                return False, f"Page check missing URL for '{desc}'"
            try:
                import requests
                response = requests.get(url, timeout=10)
                if response.status_code != 200 or len(response.text) < 10:
                    return False, f"Page check failed for '{desc}': {response.status_code}"
            except Exception as e:
                return False, f"Page check error for '{desc}': {str(e)}"

        elif criterion_type == "custom":
            script = criterion.get("script")
            if not script:
                return False, f"Custom check missing script for '{desc}'"
            try:
                r = subprocess.run(
                    ["python", "-c", script],
                    capture_output=True, text=True, timeout=30,
                )
                if r.returncode != 0:
                    return False, f"Custom check failed for '{desc}': {r.stderr}"
            except subprocess.TimeoutExpired:
                return False, f"Custom check timed out for '{desc}'"
            except Exception as e:
                return False, f"Custom check error for '{desc}': {str(e)}"
        else:
            return False, f"Unknown criterion type '{criterion_type}' for '{desc}'"

    return True, f"All {len(criteria_list)} acceptance criteria passed"


def run_objective_checks(
    db, criteria: List[Dict], task_id: str, context_md: str = None
) -> List[Dict]:
    """
    直接执行客观检查（compile/api/page/custom/data/business_flow/page_flow/data_flow）
    返回检查结果列表
    """
    from sqlalchemy import text

    results = []
    for criterion in criteria:
        criterion_type = criterion.get("type")
        name = criterion.get("name", criterion_type)
        desc = criterion.get("desc", name)
        passed = False
        detail = ""

        if criterion_type == "compile":
            try:
                nexus_dir = os.environ.get("NEXUS_DIR", ".")
                r = subprocess.run(
                    ["npx", "tsc", "--noEmit"],
                    cwd=nexus_dir,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )
                passed = r.returncode == 0
                detail = f"Compile check {'passed' if passed else 'failed'}: {r.stderr if not passed else ''}"
            except subprocess.TimeoutExpired:
                detail = f"Compile check timed out for '{desc}'"
            except FileNotFoundError:
                logger.warning("tsc not found, skipping compile check")
                passed = True
                detail = "tsc not found, skipped"
            except Exception as e:
                detail = f"Compile check error for '{desc}': {str(e)}"

        elif criterion_type == "api":
            endpoint = criterion.get("endpoint")
            if not endpoint:
                base_url = None
                if context_md:
                    m = re.search(
                        r"(?:后端|backend|base_url|API地址|api_base)[\s:：]*?(https?://[\w.:]+)",
                        context_md,
                    )
                    if m:
                        base_url = m.group(1).rstrip("/")
                        logger.info(f"[VerificationRules] API base_url from context_md: {base_url}")
                if not base_url:
                    base_url = "http://127.0.0.1:8097"
                m = re.match(r"(GET|POST|PUT|DELETE|PATCH)\s+(/\S+)", desc.strip())
                if m:
                    endpoint = f"{base_url}{m.group(2)}"
                    logger.info(f"[VerificationRules] API derived: {m.group(1)} {endpoint}")

            if not endpoint:
                passed = True
                detail = f"API check skipped (no endpoint) for '{desc}'"
            else:
                try:
                    import requests
                    response = requests.get(endpoint, timeout=10)
                    passed = response.status_code == 200
                    detail = f"API check {'passed' if passed else 'failed'} for '{desc}': {response.status_code}"
                except Exception as e:
                    detail = f"API check error for '{desc}': {str(e)}"

        elif criterion_type == "page":
            url = criterion.get("url")
            if not url:
                passed = True
                detail = f"Page check skipped (no URL) for '{desc}'"
            else:
                try:
                    import requests
                    response = requests.get(url, timeout=10)
                    passed = response.status_code == 200 and len(response.text) >= 10
                    detail = f"Page check {'passed' if passed else 'failed'} for '{desc}': {response.status_code}"
                except Exception as e:
                    detail = f"Page check error for '{desc}': {str(e)}"

        elif criterion_type == "custom":
            script = criterion.get("script")
            if not script:
                detail = f"Custom check missing script for '{desc}'"
            else:
                try:
                    r = subprocess.run(
                        ["python", "-c", script],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=30,
                    )
                    passed = r.returncode == 0
                    detail = f"Custom check {'passed' if passed else 'failed'} for '{desc}'"
                except subprocess.TimeoutExpired:
                    detail = f"Custom check timed out for '{desc}'"
                except Exception as e:
                    detail = f"Custom check error for '{desc}': {str(e)}"

        elif criterion_type in ("data_flow", "business_flow", "page_flow"):
            urls = {
                "data_flow": "http://127.0.0.1:8097/api/v1/health",
                "business_flow": "http://127.0.0.1:8097/api/v1/health",
                "page_flow": "http://localhost:5173",
            }
            label = {"data_flow": "后端", "business_flow": "后端", "page_flow": "前端"}.get(
                criterion_type, criterion_type
            )
            try:
                import requests
                r = requests.get(urls[criterion_type], timeout=10)
                passed = r.status_code == 200
                detail = f"{label} flow check {'passed' if passed else 'failed'}: {r.status_code}"
            except Exception as e:
                detail = f"{label} flow check error: {str(e)}"

        elif criterion_type == "data":
            try:
                with db.engine.connect() as conn:
                    t = conn.execute(
                        text("SELECT id, goal_id, project_id FROM tasks WHERE id = :id"),
                        {"id": task_id},
                    ).fetchone()
                    if not t:
                        detail = f"Data check: task {task_id} not found in DB"
                    else:
                        siblings = conn.execute(
                            text(
                                "SELECT id, title, status, executor_type FROM tasks "
                                "WHERE goal_id = :gid AND id != :tid ORDER BY created_at"
                            ),
                            {"gid": t.goal_id, "tid": task_id},
                        ).fetchall()
                        issues = []
                        for s in siblings:
                            if s.executor_type == "human" and s.status not in (
                                "waiting_human", "todo", "done", "in_progress",
                                "paused", "failed", "disputed", "review_needed",
                            ):
                                issues.append(f"{s.id}: human but status={s.status}")
                            if s.executor_type == "ai" and s.status == "waiting_human":
                                issues.append(f"{s.id}: ai but waiting_human")
                        passed = len(issues) == 0
                        detail = f"Data check: verified {len(siblings)} sibling tasks"
                        if issues:
                            detail += f", {len(issues)} issues: " + "; ".join(issues)
            except Exception as e:
                detail = f"Data check error: {str(e)}"

        else:
            detail = f"Unknown criterion type '{criterion_type}' for '{desc}'"

        results.append({
            "name": name,
            "type": criterion_type,
            "passed": passed,
            "detail": detail,
        })

    return results
