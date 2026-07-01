"""
OpenClaw Adapter — 调用 openclaw CLI 进行注册、派发、心跳

逻辑迁移自 reins/scheduler/task_runner.py：
- dispatch: subprocess.run(["node", "openclaw.mjs", "agent", "--local", "--agent", ...])
- heartbeat: subprocess.run(["openclaw", "gateway", "status"])
- register: 验证 agent_code 在 openclaw.json 中存在
"""

from __future__ import annotations

import json
import subprocess
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from agent_service.adapters.base import (
    BaseAgentAdapter, FieldDef, DispatchResult, TaskDispatch, TaskResult,
)

# ── Paths ──
OPENCLAW_MJS = Path("C:/Users/liuzh/AppData/Roaming/npm/node_modules/openclaw/openclaw.mjs")
GREVER_DIR = Path(__file__).resolve().parents[5]
GREVER_LOGS_DIR = GREVER_DIR / "logs"


class OpenClawAdapter(BaseAgentAdapter):

    @property
    def platform_type(self) -> str:
        return "openclaw"

    @property
    def platform_label(self) -> str:
        return "OpenClaw"

    def get_registration_fields(self) -> List[FieldDef]:
        return [
            FieldDef(
                key="agent_code", label="Agent Code", type="string",
                required=True, placeholder="main",
                description="OpenClaw 配置文件中的 agent code",
            ),
            FieldDef(
                key="model", label="模型", type="string",
                required=False, placeholder="minimax/MiniMax-M2.7",
                description="使用的 LLM 模型（可选）",
            ),
            FieldDef(
                key="workspace", label="工作区", type="string",
                required=True, placeholder="workspace",
                description="Agent 的工作区路径（OpenClaw workspace 目录名）",
            ),
        ]

    def is_async_native(self) -> bool:
        return False

    def is_session_based(self) -> bool:
        return False

    async def register(self, agent_id: str, name: str,
                       config: Dict[str, Any]) -> str:
        """
        注册 OpenClaw Agent
        验证 agent_code 在 openclaw.json 中存在
        """
        agent_code = config.get("agent_code", "")
        if not agent_code:
            raise ValueError("agent_code 是必填字段")

        # 验证 openclaw CLI 是否可用
        try:
            result = subprocess.run(
                ["node", str(OPENCLAW_MJS), "--version"],
                capture_output=True, text=True, timeout=10,
            )
            logger.info(f"[OpenClawAdapter] CLI version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise RuntimeError("openclaw CLI 未安装或不在 PATH 中")
        except subprocess.TimeoutExpired:
            raise RuntimeError("openclaw CLI 响应超时")

        # 尝试验证 agent_code 是否存在于 openclaw.json
        # 通过调用 openclaw agent --list 或类似命令
        try:
            result = subprocess.run(
                ["node", str(OPENCLAW_MJS), "agent", "--list"],
                capture_output=True, text=True, timeout=10,
                cwd=str(GREVER_DIR),
            )
            output = result.stdout + result.stderr
            # 简单检查 agent_code 是否在输出中
            if agent_code not in output:
                logger.warning(
                    f"[OpenClawAdapter] agent_code '{agent_code}' not found in openclaw agent list, "
                    f"but registration will proceed (list format may vary)"
                )
        except Exception as e:
            logger.warning(f"[OpenClawAdapter] Could not verify agent_code '{agent_code}': {e}")

        return agent_id

    async def unregister(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """注销 OpenClaw Agent（无需特殊操作，仅从 DB 移除）"""
        logger.info(f"[OpenClawAdapter] Unregistering agent {agent_id}")
        return True

    async def heartbeat(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """
        心跳检测 — 使用 openclaw gateway status
        """
        try:
            result = subprocess.run(
                ["node", str(OPENCLAW_MJS), "gateway", "status"],
                capture_output=True, text=True, timeout=15,
                cwd=str(GREVER_DIR),
            )
            alive = result.returncode == 0
            if alive:
                logger.debug(f"[OpenClawAdapter] Heartbeat OK for {agent_id}")
            else:
                logger.warning(f"[OpenClawAdapter] Heartbeat failed for {agent_id}: {result.stderr}")
            return alive
        except subprocess.TimeoutExpired:
            logger.warning(f"[OpenClawAdapter] Heartbeat timeout for {agent_id}")
            return False
        except FileNotFoundError:
            logger.error(f"[OpenClawAdapter] openclaw CLI not found for heartbeat")
            return False
        except Exception as e:
            logger.error(f"[OpenClawAdapter] Heartbeat error for {agent_id}: {e}")
            return False

    async def dispatch(self, agent_id: str, config: Dict[str, Any],
                       task: TaskDispatch) -> DispatchResult:
        """
        派发任务到 OpenClaw Agent
        
        使用: node openclaw.mjs agent --local --agent <code> --session-id <id> -m <prompt>
        
        这是同步调用：等待进程完成，捕获 stdout，写入 result file。
        """
        task_id = task.task_id
        agent_code = config.get("agent_code", "main")
        session_id = f"grever-{task_id}"

        # 构建 prompt
        prompt = self._build_prompt(task)

        # 确保 logs 目录存在
        GREVER_LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # 构建命令
        cmd = [
            "node",
            str(OPENCLAW_MJS),
            "agent",
            "--local",
            "--agent",
            agent_code,
            "--session-id",
            session_id,
            "-m",
            prompt,
        ]

        logger.info(f"[OpenClawAdapter] Dispatching task {task_id} with agent_code={agent_code}")
        logger.debug(f"[OpenClawAdapter] Command: {' '.join(cmd[:8])} ...")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=task.timeout_seconds,
                cwd=str(GREVER_DIR),
            )

            output = result.stdout
            exit_code = result.returncode

            # 判断成功/失败
            success = self._is_successful(output, exit_code)

            # 提取摘要
            summary = self._extract_summary(output)

            # 写入 result file
            self._write_result_file(task_id, output, exit_code, success, summary)

            if success:
                return DispatchResult(
                    dispatch_id=task_id,
                    status="completed",
                    result=summary,
                    estimated_seconds=0,
                )
            else:
                return DispatchResult(
                    dispatch_id=task_id,
                    status="failed",
                    error=summary or f"exit_code={exit_code}",
                    result=output[:500] if output else None,
                    estimated_seconds=0,
                )

        except subprocess.TimeoutExpired:
            logger.error(f"[OpenClawAdapter] Dispatch timeout for task {task_id}")
            return DispatchResult(
                dispatch_id=task_id,
                status="failed",
                error=f"Timeout after {task.timeout_seconds}s",
            )
        except FileNotFoundError:
            logger.error(f"[OpenClawAdapter] openclaw CLI not found")
            return DispatchResult(
                dispatch_id=task_id,
                status="failed",
                error="openclaw CLI not installed",
            )
        except Exception as e:
            logger.error(f"[OpenClawAdapter] Dispatch error for task {task_id}: {e}")
            return DispatchResult(
                dispatch_id=task_id,
                status="failed",
                error=str(e),
            )

    async def get_result(self, dispatch_id: str,
                         config: Dict[str, Any]) -> Optional[TaskResult]:
        """OpenClaw 是同步模式，此方法从 result file 读取结果"""
        result_file = GREVER_LOGS_DIR / f"nexus_result_{dispatch_id.replace('-', '_')}.json"
        if not result_file.exists():
            return None

        try:
            content = result_file.read_text(encoding='utf-8')
            data = json.loads(content)
            return TaskResult(
                task_id=dispatch_id,
                status=data.get("status", "failed"),
                result=data.get("summary"),
                error=None if data.get("status") == "success" else f"exit_code={data.get('exit_code')}",
            )
        except Exception as e:
            logger.error(f"[OpenClawAdapter] Failed to read result for {dispatch_id}: {e}")
            return None

    # ── Internal helpers ──

    @staticmethod
    def _build_prompt(task: TaskDispatch) -> str:
        """构建任务 prompt"""
        parts = [f"# 📋 当前任务（Task）", f"## {task.title}"]
        if task.description:
            parts.append(task.description)
        if task.acceptance_criteria:
            parts.append(f"\n### ✅ 验收标准\n{task.acceptance_criteria}")
        return "\n\n".join(parts)

    @staticmethod
    def _is_successful(output: str, exit_code: int) -> bool:
        """判断执行是否成功"""
        if not output or len(output) < 500:
            return False
        success_indicators = [
            "✅", "已完成", "已验收通过", "编译", "API", "页面",
            "run_completed", "run done", "task completed",
            "ts编译", "py_compile", "migration", "验证通过",
        ]
        output_lower = output.lower()
        return any(ind.lower() in output_lower for ind in success_indicators)

    @staticmethod
    def _extract_summary(output: str) -> str:
        """从输出中提取摘要"""
        if not output:
            return "任务执行完成（无摘要输出）"

        lines = output.strip().split('\n')
        meaningful = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if re.match(r'\d{2}:\d{2}:\d{2}', line):
                continue
            if line.startswith('[') and ']' in line:
                continue
            if len(line) > 5:
                meaningful.append(line)

        last_lines = meaningful[-3:] if len(meaningful) >= 3 else meaningful
        if last_lines:
            return ' | '.join(last_lines)[:500]
        return output[-200:] if len(output) > 200 else output

    @staticmethod
    def _write_result_file(task_id: str, output: str, exit_code: int,
                           success: bool, summary: str):
        """写入 result file"""
        GREVER_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        result_file = GREVER_LOGS_DIR / f"nexus_result_{task_id.replace('-', '_')}.json"

        result_data = {
            "task_id": task_id,
            "status": "success" if success else "failed",
            "summary": summary,
            "exit_code": exit_code,
            "output_length": len(output),
            "source": "agent_service_openclaw_adapter",
        }

        try:
            result_file.write_text(
                json.dumps(result_data, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            logger.info(f"[OpenClawAdapter] Wrote result file: {result_file}")
        except Exception as e:
            logger.error(f"[OpenClawAdapter] Failed to write result file: {e}")
