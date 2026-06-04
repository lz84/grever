"""GRASP helpers: cognition storage + graph data loading — split from grasp_router.py"""

import json
import hashlib
from pathlib import Path
from typing import List

# === 认知数据文件路径 ===
COGNITIONS_FILE = Path("D:/work/research/agents-nexus/skills/grasp/memory/grasp/cognitions.jsonl")
if not COGNITIONS_FILE.exists():
    COGNITIONS_FILE = Path(__file__).parent.parent.parent / "data" / "cognitions.jsonl"
if not COGNITIONS_FILE.exists():
    COGNITIONS_FILE = Path("D:/work/research/agents-nexus/data/cognitions.jsonl")

# === 知识图谱数据路径 ===
GRAPHRAG_OUTPUT = Path("D:/work/research/agents-nexus/data/graphrag/output")
GRAPHRAG_UPDATE = Path("D:/work/research/agents-nexus/data/graphrag/update_output")

def _load_cognitions() -> List[dict]:
    """Load all cognitions from JSONL file."""
    if not COGNITIONS_FILE.exists():
        return []
    cognitions = []
    try:
        with open(COGNITIONS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        cognitions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return cognitions

def _save_cognitions(cognitions: List[dict]):
    """Save all cognitions back to JSONL file (atomic write)."""
    COGNITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = COGNITIONS_FILE.with_suffix(".tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            for c in cognitions:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        tmp_file.replace(COGNITIONS_FILE)
    except Exception:
        with open(COGNITIONS_FILE, "w", encoding="utf-8") as f:
            for c in cognitions:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

def _hash_position(s: str, range_min: int = 50, range_max: int = 650) -> tuple:
    """Generate deterministic x,y position from string."""
    h = hashlib.md5(s.encode()).hexdigest()
    x = range_min + int(h[:4], 16) % (range_max - range_min)
    y = range_min + int(h[4:8], 16) % (range_max - range_min)
    return x, y

def _try_load_graph_data():
    """Try to load graph nodes/edges from GraphRAG parquet files."""
    try:
        import pandas as pd
    except ImportError:
        return [], []

    entities_path = None
    relationships_path = None

    if GRAPHRAG_UPDATE.exists():
        runs = sorted(GRAPHRAG_UPDATE.iterdir(), reverse=True)
        for run_dir in runs:
            if run_dir.is_dir():
                prev = run_dir / "previous"
                if prev.exists():
                    ep = prev / "entities.parquet"
                    rp = prev / "relationships.parquet"
                    if ep.exists():
                        entities_path = ep
                    if rp.exists():
                        relationships_path = rp
                    break

    if entities_path is None:
        ep = GRAPHRAG_OUTPUT / "entities.parquet"
        if ep.exists():
            entities_path = ep
    if relationships_path is None:
        rp = GRAPHRAG_OUTPUT / "relationships.parquet"
        if rp.exists():
            relationships_path = rp

    nodes = []
    edges = []

    if entities_path and entities_path.exists():
        try:
            df = pd.read_parquet(entities_path)
            for _, row in df.iterrows():
                entity_id = str(row.get("id", row.get("human_readable_id", "")))
                label = str(row.get("name", row.get("title", entity_id)))
                category = str(row.get("type", row.get("entity_type", "概念")))
                x, y = _hash_position(entity_id)
                size = 20 + min(int(row.get("rank", 0)) * 3, 30)
                nodes.append({
                    "id": entity_id,
                    "label": label,
                    "category": category,
                    "x": x,
                    "y": y,
                    "size": size,
                })
        except Exception:
            pass

    if relationships_path and relationships_path.exists():
        try:
            df = pd.read_parquet(relationships_path)
            for _, row in df.iterrows():
                src = str(row.get("source", row.get("src", "")))
                tgt = str(row.get("target", row.get("tgt", "")))
                label = str(row.get("description", row.get("type", "关联")))
                if src and tgt:
                    edges.append({
                        "from": src,
                        "to": tgt,
                        "label": label[:50],
                    })
        except Exception:
            pass

    return nodes, edges
