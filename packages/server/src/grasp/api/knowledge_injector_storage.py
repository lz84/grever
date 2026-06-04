"""知识注入 API - 存储层（注入历史 + 认知持久化）"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List
from pathlib import Path

# ========== 注入历史存储 ==========

INJECTION_HISTORY_FILE = "data/knowledge_injections.jsonl"

def _get_history_path() -> Path:
    """获取注入历史文件路径"""
    p = Path(__file__).parent.parent.parent / "data" / "knowledge_injections.jsonl"
    if not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _load_history() -> List[Dict]:
    """加载注入历史"""
    path = _get_history_path()
    if not path.exists():
        return []
    results = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return results

def _save_history(record: Dict) -> None:
    """追加注入历史"""
    path = _get_history_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

# ========== 认知存储 ==========

COGNITIONS_FILE = "skills/grasp/memory/grasp/cognitions.jsonl"

def _get_cognitions_path() -> Path:
    """获取认知文件路径"""
    paths = [
        Path(__file__).parent.parent.parent.parent.parent.parent.parent / "skills" / "grasp" / "memory" / "grasp" / "cognitions.jsonl",
        Path(__file__).parent.parent.parent / "data" / "cognitions.jsonl",
        Path("D:/work/research/agents-nexus/skills/grasp/memory/grasp/cognitions.jsonl"),
    ]
    for p in paths:
        if p.exists():
            return p
    fallback = paths[-1]
    if not fallback.parent.exists():
        fallback.parent.mkdir(parents=True, exist_ok=True)
    return fallback

def _inject_cognition(cognition: Dict) -> str:
    """
    注入认知到知识库文件，返回 cognition_id
    """
    cognition_id = str(uuid.uuid4())[:8]
    record = {
        "cognition_id": cognition_id,
        "type": cognition["type"],
        "content": cognition["content"],
        "tags": cognition.get("tags", []),
        "source": cognition.get("source", {}),
        "confidence": cognition.get("confidence", 0.9),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path = _get_cognitions_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return cognition_id
