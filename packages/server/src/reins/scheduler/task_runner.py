"""
任务执行器 - 调 OpenClaw CLI 执行单个任务

职责：
1. 异步启动 OpenClaw CLI 进程执行任务
2. poll 检查进程是否完成
3. 进程结束后自动捕获输出并写 result file
4. 管理子进程生命周期
"""

import asyncio
import json
from loguru import logger
import sys
import re
from sqlalchemy import text
from pathlib import Path
from typing import Dict, Any, Optional
from asyncio.subprocess import Process

# 添加 packages/server 到 Python 路径
NEXUS_DIR = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(NEXUS_DIR / "packages" / "server"))

from shared.database.config import DB_CONFIG

# 路径配置
OPENCLAW_MJS = Path("C:/Users/liuzh/AppData/Roaming/npm/node_modules/openclaw/openclaw.mjs")
NEXUS_LOGS_DIR = Path("D:/work/research/agents-nexus/logs")

# DB path for building execution context
NEXUS_DB_PATH = str(NEXUS_DIR / "data" / "reins.db")

# Nexus Agent UUID → OpenClaw Agent Code 映射
# 来源：openclaw.json agents.list[].id 与 reins.db agents 表的 id 对应关系
AGENT_UUID_TO_CODE: dict[str, str] = {
    "fefd19b0-7c1a-4927-b294-c795c76afb9f": "main",
    "876b9322-0fbe-4cd0-97c2-9244a4e3b905": "stock-trader",
    "9d899c03-4ada-45a7-805a-b2f0fb4ebb24": "coder",
    "8817e140-2c46-40d8-9444-a6bca8a8e8fb": "wenzi",
    "3745f1f0-b67d-4287-a10b-e71b3ff17e97": "kouzi",
}

def build_task_prompt(task: Dict[str, Any], db=None) -> str:
    """
    构建任务 prompt
    
    优先使用 build_task_execution_context() 构建完整的三级上下文 prompt。
    如果 db 不可用或构建失败，回退到简化版。
    """
    # 优先使用统一构建的 prompt（来自心跳/注入器路径）
    context = task.get("context", {})
    if isinstance(context, dict) and context.get("prompt"):
        return context["prompt"]
    
    # 有 db → 调用统一 context builder 构建完整 prompt
    if db:
        try:
            task_id = task.get("id", "")
            if task_id:
                from .task_context_builder import build_task_execution_context
                ctx = build_task_execution_context(task_id, db)
                if ctx and ctx.get("prompt"):
                    return ctx["prompt"]
        except Exception as e:
            logger.warning(f"[task_runner] build_task_execution_context failed for {task.get('id')}: {e}")
    
    # 回退：简化版
    parts = []
    
    # 任务标题和描述
    parts.append(f"# 📋 当前任务（Task）")
    parts.append(f"## {task.get('title', '')}")
    desc = task.get('description', '')
    if desc:
        parts.append(desc)
    
    # 交付标准
    delivery = task.get('delivery_criteria', '')
    if delivery:
        parts.append(f"\n### 📦 交付标准")
        parts.append("*以下全部自测通过后，才可标记任务完成：*")
        if isinstance(delivery, dict):
            criteria = delivery.get('criteria', [])
        elif isinstance(delivery, list):
            criteria = delivery
        else:
            criteria = []
        for item in criteria:
            if isinstance(item, dict):
                parts.append(f"- [ ] {item.get('name', '')}: {item.get('desc', '')}")
            else:
                parts.append(f"- [ ] {item}")

    # 验收标准
    requirements = task.get('acceptance_criteria', '')
    if requirements:
        parts.append(f"\n### ✅ 验收标准")
        if isinstance(requirements, list):
            for i, criterion in enumerate(requirements, 1):
                if isinstance(criterion, dict):
                    parts.append(f"{i}. {criterion.get('desc', criterion.get('description', str(criterion)))}")
                else:
                    parts.append(f"{i}. {criterion}")
        else:
            parts.append(str(requirements))
    
    # 验证 Agent
    verifier = task.get('verifier_agent_id', '')
    if verifier:
        parts.append(f"\n### 🔍 验证 Agent\n{verifier}")
    
    return "\n\n".join(parts)

async def launch(task: Dict[str, Any], agent_id: str, nexus_url: str = "", db=None) -> Process:
    """
    异步启动 OpenClaw CLI 执行任务
    
    使用 asyncio.create_subprocess_exec（非阻塞）
    
    参数：
        task: 任务字典
        agent_id: Agent UUID
        nexus_url: Nexus 服务器 URL
        db: 数据库管理器实例（用于构建完整执行上下文）
    """
    task_id = task.get('id', '')
    session_id = f"nexus-{task_id}"
    
    # 确保 logs 目录存在
    NEXUS_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 构建 prompt（使用统一 context builder，如果有 db）
    prompt = build_task_prompt(task, db=db)
    
    # 【Sprint 90 修复】：同时将执行上下文写入 DB，供验证链路使用
    # 即使 executor 完成时不传 context_md，验证时也能从 DB 读到
    # 注意：build_task_prompt 内部已调用 build_task_execution_context，
    # 这里直接复用其结果（prompt 变量）写入 DB
    if db and task_id and prompt and len(prompt) > 50:
        try:
            ctx_summary = prompt[:8000]  # prompt 就是完整的执行上下文
            with db.engine.connect() as conn:
                conn.execute(
                    text("UPDATE tasks SET context_md = :cmd, updated_at = CURRENT_TIMESTAMP WHERE id = :tid"),
                    {"cmd": ctx_summary, "tid": task_id}
                )
                conn.commit()
            logger.info(f"[task_runner] Wrote context_md ({len(ctx_summary)} chars) to DB for task {task_id}")
        except Exception as e:
            logger.warning(f"[task_runner] Failed to write context_md for {task_id}: {e}")
    
    # 从 agent UUID 解析 OpenClaw agent code
    agent_name = AGENT_UUID_TO_CODE.get(agent_id)
    if not agent_name:
        logger.warning(f"[task_runner] Unknown agent UUID {agent_id}, falling back to 'main'")
        agent_name = 'main'
    
    # 构建命令
    cmd = [
        "node",
        str(OPENCLAW_MJS),
        "agent",
        "--local",
        "--agent",
        agent_name,
        "--session-id",
        session_id,
        "-m",
        prompt,
    ]
    
    logger.info(f"[task_runner] Launching task {task_id} with agent name={agent_name} (id={agent_id})")
    logger.debug(f"[task_runner] Command: {' '.join(cmd)}")
    
    # 启动子进程（非阻塞）
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(NEXUS_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    logger.info(f"[task_runner] Started process {process.pid} for task {task_id}")
    
    return process

def check_completed(process: Process) -> bool:
    """
    检查进程是否完成
    
    asyncio.subprocess.Process 用 returncode 判断，没有 poll() 方法
    """
    return process.returncode is not None

def _extract_summary_from_output(output: str) -> str:
    """
    从 agent 输出中提取摘要
    
    策略：
    1. 找最后几行有意义的文本（agent 通常在最后总结）
    2. 过滤掉日志行和时间戳
    """
    if not output:
        return "任务执行完成（无摘要输出）"
    
    lines = output.strip().split('\n')
    
    # 过滤掉日志行（带时间戳的、带 [plugins] 的等）
    meaningful = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 跳过日志行
        if re.match(r'\d{2}:\d{2}:\d{2}', line):
            continue
        if line.startswith('[') and ']' in line:
            continue
        if len(line) > 5:
            meaningful.append(line)
    
    # 取最后 3 行有意义的内容
    last_lines = meaningful[-3:] if len(meaningful) >= 3 else meaningful
    
    if last_lines:
        return ' | '.join(last_lines)[:500]
    
    return output[-200:] if len(output) > 200 else output

def write_result_file(task_id: str, output: str, exit_code: int) -> Dict[str, Any]:
    """
    从进程输出构建结果并写入文件
    
    参数：
        task_id: 任务 ID
        output: agent stdout 内容
        exit_code: 进程退出码
    
    返回：
        结果字典
    """
    NEXUS_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    result_file = NEXUS_LOGS_DIR / f"nexus_result_{task_id.replace('-', '_')}.json"
    
    # 判断成功/失败
    # OpenClaw agent 退出码不准确（总是 0 或 1）
    # 成功标准：输出包含有意义的执行结果
    # 失败模式：output ~7583 字符且只有 "eueSize=0\n...embedded run start..."
    # 成功模式：output 包含 ✅、API 验证、编译等关键词
    if not output or len(output) < 500:
        success = False
    else:
        # 检查是否包含有意义的执行结果
        success_indicators = [
            "✅", "已完成", "已验收通过", "编译", "API", "页面",
            "run_completed", "run done", "task completed",
            "ts编译", "py_compile", "migration", "验证通过",
        ]
        output_lower = output.lower()
        # 如果包含任何成功指标 → 成功
        success = any(ind.lower() in output_lower for ind in success_indicators)
    
    # 提取摘要
    summary = _extract_summary_from_output(output)
    
    result_data = {
        "task_id": task_id,
        "status": "success" if success else "failed",
        "summary": summary,
        "exit_code": exit_code,
        "output_length": len(output),
        "source": "task_runner_captured",
    }
    
    # 写入文件
    try:
        result_file.write_text(
            json.dumps(result_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        logger.info(f"[task_runner] Wrote result file: {result_file} (status={result_data['status']})")
    except Exception as e:
        logger.error(f"[task_runner] Failed to write result file: {e}")
    
    return result_data

async def read_result(task_id: str) -> Optional[Dict[str, Any]]:
    """
    读取任务执行结果 JSON 文件
    """
    result_file = NEXUS_LOGS_DIR / f"nexus_result_{task_id.replace('-', '_')}.json"
    
    if not result_file.exists():
        logger.warning(f"[task_runner] Result file not found: {result_file}")
        return None
    
    try:
        content = result_file.read_text(encoding='utf-8')
        result_data = json.loads(content)
        logger.info(f"[task_runner] Read result for task {task_id}, success={result_data.get('status')}")
        return result_data
    except json.JSONDecodeError as e:
        logger.error(f"[task_runner] Failed to parse result file for task {task_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"[task_runner] Failed to read result file for task {task_id}: {e}")
        return None
