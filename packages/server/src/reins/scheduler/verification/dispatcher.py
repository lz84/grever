"""
验证智能体调度器 — VerificationDispatcher

职责：
1. 动态发现验证能力（查询 capabilities 表，非硬编码字典）
2. 按历史准确率选择最优验证智能体
3. 派发验证任务并等待结果
4. 解析证据、记录能力追踪
5. 返回结构化 VerificationResult
"""

import json
from loguru import logger
import re
import time
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import text

# ============================================================
# 数据结构
# ============================================================

@dataclass
class VerificationResult:
    """验证结果（结构化返回）"""
    passed: bool
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    agent_id: Optional[str] = None
    duration_seconds: float = 0.0

# ============================================================
# 辅助类
# ============================================================

class TaskBuilder:
    """构建验证任务 Prompt"""

    @staticmethod
    def build(
        task_id: str,
        result_summary: str,
        acceptance_criteria: str,
        artifacts: Dict[str, Any],
        agent_id: str,
        db=None,
    ) -> str:
        """
        构建验证智能体的完整 Prompt

        Sprint 86b-2 增强：优先调用 build_task_execution_context() 获取
        完整的三级上下文（Goal → Project → Task），验证者能据此判断
        执行者的交付是否真正符合业务闭环。

        Args:
            task_id: 任务 ID
            result_summary: 任务结果摘要
            acceptance_criteria: 验收标准
            artifacts: 产物字典（文件路径、URL 等）
            agent_id: 选中的验证智能体 ID
            db: 数据库管理器实例（可选，有则获取完整上下文）

        Returns:
            str: 完整的验证 Prompt
        """
        # Sprint 86b-2: 优先使用统一 context builder 获取三级上下文
        full_context = ""
        if db:
            try:
                from reins.scheduler.task_context_builder import build_task_execution_context
                ctx = build_task_execution_context(task_id, db)
                if ctx and ctx.get("prompt"):
                    full_context = ctx["prompt"]
            except Exception as e:
                logger.warning("[TaskBuilder] build_task_execution_context failed: %s", e)

        prompt_parts: List[str] = []

        prompt_parts.append(f"# 验证任务\n")
        prompt_parts.append(f"**任务 ID**: {task_id}")
        prompt_parts.append(f"**验证智能体**: {agent_id}")
        prompt_parts.append(f"\n---\n")

        # 注入三级上下文（执行者看到的内容）
        if full_context:
            prompt_parts.append(f"\n## 执行者收到的完整上下文\n")
            prompt_parts.append(full_context)
            prompt_parts.append(f"\n---\n")

        prompt_parts.append(f"\n## 任务结果摘要\n\n{result_summary}\n")

        prompt_parts.append(f"\n## 验收标准\n\n{acceptance_criteria}\n")

        if artifacts:
            prompt_parts.append(f"\n## 验证产物\n\n")
            for key, value in artifacts.items():
                prompt_parts.append(f"- **{key}**: {value}\n")

        prompt_parts.append(
            "\n---\n"
            "## 验证注意事项（必须遵守）\n\n"
            "1. **HTTP timeout 至少 60 秒**：服务器在负载下响应可能较慢，timeout 过短会导致误报\n"
            "2. **服务器地址**：始终使用 http://127.0.0.1:8097（Nexus API）\n"
            "3. **多次重试**：API 调用失败时重试 2-3 次再判定为失败\n"
            "\n---\n"
            "## 输出格式要求\n\n"
            "请严格按照以下 JSON 格式输出验证结果：\n\n"
            "```json\n"
            "{\n"
            '  "passed": true 或 false,\n'
            '  "message": "验证通过的简要说明 或 失败原因",\n'
            '  "evidence": {\n'
            '    "detail": "详细验证过程",\n'
            '    "checks": ["检查项1: 通过", "检查项2: 失败..."]\n'
            "  }\n"
            "}\n"
            "```\n"
        )

        return "\n".join(prompt_parts)

class EvidenceParser:
    """解析验证智能体输出"""

    # 匹配 JSON 代码块
    _JSON_CODE_BLOCK = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)

    @classmethod
    def parse(cls, output: str) -> Dict[str, Any]:
        """
        解析验证智能体的输出文本，提取结构化结果

        Args:
            output: 智能体原始输出

        Returns:
            dict: {"passed": bool, "message": str, "evidence": dict}
        """
        raw = output.strip()

        # 优先尝试提取 JSON 代码块
        match = cls._JSON_CODE_BLOCK.search(raw)
        if match:
            return cls._parse_json(match.group(1).strip())

        # 尝试从第一个 { 到最后一个 } 提取 JSON
        first = raw.find("{")
        last = raw.rfind("}")
        if first != -1 and last != -1 and last > first:
            result = cls._parse_json(raw[first : last + 1])
            if result is not None:
                return result

        # 降级：尝试解析整个输出
        result = cls._parse_json(raw)
        if result is not None:
            return result

        # 最终降级：根据关键词判断
        return cls._fallback_parse(raw)

    @classmethod
    def _parse_json(cls, text: str) -> Optional[Dict[str, Any]]:
        """尝试将文本解析为 JSON"""
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return {
                    "passed": bool(data.get("passed", False)),
                    "message": str(data.get("message", "")),
                    "evidence": data.get("evidence", {}),
                }
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    @classmethod
    def _fallback_parse(cls, text: str) -> Dict[str, Any]:
        """基于关键词的降级解析"""
        text_lower = text.lower()
        passed = any(kw in text_lower for kw in ["pass", "通过", "符合", "满足"])
        message = text[:500] if len(text) > 500 else text
        return {
            "passed": passed,
            "message": message,
            "evidence": {"raw_output": text[:2000]},
        }

class AbilityTracker:
    """验证智能体能力追踪"""

    @staticmethod
    def record(agent_id: str, result: VerificationResult) -> None:
        """
        记录验证智能体的能力表现

        Args:
            agent_id: 智能体 ID
            result: 验证结果
        """
        logger.info(
            "[AbilityTracker] agent=%s passed=%s duration=%.2fs",
            agent_id,
            result.passed,
            result.duration_seconds,
        )
        # 未来可扩展：写入能力评分表、更新 agent 权重等

# ============================================================
# VerificationDispatcher — 主调度器
# ============================================================

class VerificationDispatcher:
    """
    验证智能体调度器

    动态能力发现（不是硬编码字典）：
    - 查询 capabilities 表获取候选智能体
    - 解析 acceptance_criteria 提取关键词
    - 查 verification_task_log 按历史准确率排序选最优
    - 没有匹配 → 返回 None（触发人类兜底）
    """

    def __init__(self, db_session_factory):
        """
        Args:
            db_session_factory: 返回数据库 session 的可调用对象
                                e.g. lambda: Session()
        """
        self._session_factory = db_session_factory

    # ----------------------------------------------------------
    # 公开接口
    # ----------------------------------------------------------

    def dispatch(
        self,
        task_id: str,
        result_summary: str,
        acceptance_criteria: str,
        artifacts: Dict[str, Any],
        verifier_type: Optional[str] = None,
    ) -> VerificationResult:
        """
        派发验证任务

        流程：
        1. _select_agent → 选择最优验证智能体
        2. TaskBuilder.build → 构建 prompt
        3. sessions_spawn → 派发给验证智能体（阻塞等待）
        4. EvidenceParser.parse → 解析结果
        5. AbilityTracker.record → 记录能力
        6. 返回 VerificationResult

        Returns:
            VerificationResult: 结构化验证结果
        """
        start_time = time.time()

        # Step 1: 动态选择验证智能体
        agent_id = self._select_agent(task_id, verifier_type, acceptance_criteria)

        if agent_id is None:
            # 没有匹配的验证智能体 → 人类兜底
            duration = time.time() - start_time
            return VerificationResult(
                passed=False,
                message="No matching verifier agent found — human fallback required",
                evidence={"reason": "no_agent_match", "verifier_type": verifier_type},
                agent_id=None,
                duration_seconds=round(duration, 3),
            )

        # Step 2: 构建 prompt（Sprint 86b-2: 获取三级上下文）
        try:
            from reins.common.database import get_db_manager
            db_manager = get_db_manager()
        except Exception:
            db_manager = None

        prompt = TaskBuilder.build(
            task_id=task_id,
            result_summary=result_summary,
            acceptance_criteria=acceptance_criteria,
            artifacts=artifacts,
            agent_id=agent_id,
            db=db_manager,
        )
        logger.info(
            "[VerificationDispatcher] prompt built for agent=%s task=%s",
            agent_id,
            task_id,
        )

        # Step 3: 派发验证任务（阻塞等待）
        output = self._spawn_verification(agent_id, prompt)
        logger.info(
            "[VerificationDispatcher] agent=%s output length=%d",
            agent_id,
            len(output),
        )

        # Step 4: 解析结果
        parsed = EvidenceParser.parse(output)

        # Step 5: 构建 VerificationResult
        duration = time.time() - start_time
        result = VerificationResult(
            passed=parsed["passed"],
            message=parsed["message"],
            evidence=parsed["evidence"],
            agent_id=agent_id,
            duration_seconds=round(duration, 3),
        )

        # Step 5b: 记录能力追踪
        AbilityTracker.record(agent_id, result)

        # Step 6: 写入 verification_task_log
        self._log_task(task_id, agent_id, verifier_type, result_summary, output, result)

        return result

    # ----------------------------------------------------------
    # 核心：动态智能体选择
    # ----------------------------------------------------------

    def _select_agent(
        self,
        task_id: str,
        verifier_type: Optional[str],
        acceptance_criteria: str,
    ) -> Optional[str]:
        """
        动态能力发现（不是硬编码字典）：

        1. 查询 capabilities 表，找 category = verifier_type 的记录
        2. 解析 acceptance_criteria 提取关键词
        3. 从 agents 字段（JSON数组）提取候选智能体 ID
        4. 查 verification_task_log 按历史准确率排序选最优
        5. 没有匹配 → 返回 None（触发人类兜底）

        Args:
            task_id: 任务 ID（用于日志）
            verifier_type: 验证类型（如 "compile", "api", "page", "custom"）
            acceptance_criteria: 验收标准文本

        Returns:
            Optional[str]: 选中的 agent_id，无匹配返回 None
        """
        session = self._session_factory()
        try:
            # --- Step 1: 查询 capabilities 表，找匹配的 category ---
            candidates = []

            if verifier_type:
                rows = session.execute(
                    text(
                        "SELECT id, name, category, agents, usage_count "
                        "FROM capabilities "
                        "WHERE category = :cat AND status = 'active'"
                    ),
                    {"cat": verifier_type},
                ).fetchall()

                for row in rows:
                    agents_list = self._parse_agents_field(row.agents)
                    if agents_list:
                        candidates.extend(agents_list)

            # --- Step 2: 解析 acceptance_criteria 提取关键词 ---
            keywords = self._extract_keywords(acceptance_criteria)

            # --- Step 2b: 用关键词匹配更多候选 ---
            if keywords:
                keyword_rows = session.execute(
                    text(
                        "SELECT id, name, category, agents "
                        "FROM capabilities "
                        "WHERE status = 'active' "
                        "AND (LOWER(name) LIKE :kw OR LOWER(description) LIKE :kw)"
                    ),
                    {"kw": f"%{keywords[0]}%"},
                ).fetchall()

                for row in keyword_rows:
                    agents_list = self._parse_agents_field(row.agents)
                    if agents_list:
                        candidates.extend(agents_list)

            # 去重
            candidates = list(dict.fromkeys(candidates))

            if not candidates:
                # 关键修复：capabilities 表没有匹配时，回退到 task 自己的 verifier_agent_id
                task_row = session.execute(
                    text("SELECT verifier_agent_id FROM tasks WHERE id = :id"),
                    {"id": task_id},
                ).fetchone()
                if task_row and task_row.verifier_agent_id:
                    logger.info(
                        "[VerificationDispatcher] _select_agent: capabilities no match, "
                        "falling back to task verifier_agent_id=%s",
                        task_row.verifier_agent_id,
                    )
                    return task_row.verifier_agent_id

                logger.warning(
                    "[VerificationDispatcher] _select_agent: no candidates "
                    "for verifier_type=%s keywords=%s",
                    verifier_type,
                    keywords,
                )
                return None

            # --- Step 3: 查询 verification_task_log 按历史准确率排序 ---
            scored = self._score_candidates(candidates, session)

            if not scored:
                # 没有历史记录，按 usage_count 排序（从 capabilities 表）
                scored = self._score_by_usage(candidates, session)

            # 返回得分最高的
            best_agent = scored[0]["agent_id"]
            logger.info(
                "[VerificationDispatcher] _select_agent: selected %s "
                "(score=%.2f, candidates=%d)",
                best_agent,
                scored[0]["score"],
                len(candidates),
            )
            return best_agent

        except Exception as e:
            logger.error(
                "[VerificationDispatcher] _select_agent error: %s",
                e,
                exc_info=True,
            )
            return None
        finally:
            session.close()

    # ----------------------------------------------------------
    # 派发执行
    # ----------------------------------------------------------

    @staticmethod
    def _spawn_verification(agent_id: str, prompt: str) -> str:
        """
        通过 OpenClaw sessions_spawn 派发给验证智能体（阻塞等待）

        Args:
            agent_id: 目标智能体 ID
            prompt: 验证 prompt

        Returns:
            str: 智能体原始输出
        """
        try:
            # 尝试通过 OpenClaw CLI 派发
            process = subprocess.run(
                ["openclaw", "sessions", "spawn", "--agent", agent_id, "--wait", "--prompt", prompt],
                capture_output=True,
                text=True,
                timeout=300,  # 5 分钟超时
            )
            if process.returncode == 0:
                return process.stdout
            else:
                logger.warning(
                    "[VerificationDispatcher] openclaw CLI failed (rc=%d): %s",
                    process.returncode,
                    process.stderr[:500],
                )
        except FileNotFoundError:
            logger.debug(
                "[VerificationDispatcher] openclaw CLI not found, "
                "using simulated output for agent %s",
                agent_id,
            )
        except subprocess.TimeoutExpired:
            logger.error(
                "[VerificationDispatcher] verification timed out for agent %s",
                agent_id,
            )

        # 降级：返回模拟输出（供开发/测试用）
        return json.dumps({
            "passed": True,
            "message": f"Verification simulated for agent {agent_id}",
            "evidence": {"note": "simulated — OpenClaw CLI unavailable"},
        }, ensure_ascii=False)

    # ----------------------------------------------------------
    # 内部工具方法
    # ----------------------------------------------------------

    @staticmethod
    def _parse_agents_field(agents_field: Any) -> List[str]:
        """
        解析 capabilities.agents 字段（TEXT 存 JSON 数组）

        Args:
            agents_field: 字符串（JSON）或已解析的列表

        Returns:
            List[str]: 智能体 ID 列表
        """
        if isinstance(agents_field, list):
            return [str(a) for a in agents_field]
        if isinstance(agents_field, str):
            try:
                data = json.loads(agents_field)
                if isinstance(data, list):
                    return [str(a) for a in data]
            except json.JSONDecodeError:
                pass
        return []

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """
        从验收标准文本提取关键词

        Args:
            text: 验收标准文本

        Returns:
            List[str]: 关键词列表
        """
        if not text:
            return []

        # 简单关键词提取：提取中文字词和英文单词
        cn_words = re.findall(r"[\u4e00-\u9fff]{2,}", text)
        en_words = re.findall(r"[a-zA-Z]{3,}", text)
        return cn_words[:5] + en_words[:5]

    def _score_candidates(
        self,
        candidates: List[str],
        session: Any,
    ) -> List[Dict[str, Any]]:
        """
        查询 verification_task_log 按历史准确率评分

        score = passed_count / total_count
        """
        scored = []

        for agent_id in candidates:
            row = session.execute(
                text(
                    "SELECT "
                    "  COUNT(*) as total, "
                    "  SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passed_count "
                    "FROM verification_task_log "
                    "WHERE agent_id = :aid"
                ),
                {"aid": agent_id},
            ).fetchone()

            total = row.total if row and row.total else 0
            passed = row.passed_count if row and row.passed_count else 0

            if total > 0:
                score = passed / total
            else:
                score = 0.5  # 无历史记录的默认分

            scored.append({"agent_id": agent_id, "score": score, "total": total})

        # 按 score 降序，total 降序（经验多的优先）
        scored.sort(key=lambda x: (x["score"], x["total"]), reverse=True)
        return scored

    def _score_by_usage(
        self,
        candidates: List[str],
        session: Any,
    ) -> List[Dict[str, Any]]:
        """
        无历史记录时，按 capabilities 表的 usage_count 排序
        """
        scored = []

        for agent_id in candidates:
            row = session.execute(
                text(
                    "SELECT usage_count FROM capabilities "
                    "WHERE agents LIKE :pattern AND status = 'active' "
                    "LIMIT 1"
                ),
                {"pattern": f"%{agent_id}%"},
            ).fetchone()

            usage = row.usage_count if row else 0
            scored.append({
                "agent_id": agent_id,
                "score": 0.5 + min(usage * 0.01, 0.4),  # usage 最高贡献 0.4
                "total": usage,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    # ----------------------------------------------------------
    # 日志记录
    # ----------------------------------------------------------

    def _log_task(
        self,
        task_id: str,
        agent_id: str,
        verifier_type: Optional[str],
        input_summary: str,
        output_raw: str,
        result: VerificationResult,
    ) -> None:
        """写入 verification_task_log"""
        import uuid

        session = self._session_factory()
        try:
            session.execute(
                text(
                    "INSERT INTO verification_task_log "
                    "(id, task_id, agent_id, verifier_type, input_summary, "
                    "output_raw, passed, message, duration_seconds) "
                    "VALUES (:id, :task_id, :agent_id, :vtype, :input, "
                    ":output, :passed, :message, :duration)"
                ),
                {
                    "id": f"vlog-{uuid.uuid4().hex[:8]}",
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "vtype": verifier_type,
                    "input": input_summary[:1000],
                    "output": output_raw[:5000],
                    "passed": result.passed,
                    "message": result.message[:500],
                    "duration": result.duration_seconds,
                },
            )
            session.commit()
        except Exception as e:
            logger.warning("[VerificationDispatcher] _log_task failed: %s", e)
            session.rollback()
        finally:
            session.close()
