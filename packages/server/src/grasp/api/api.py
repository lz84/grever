"""
Grasp HTTP API Server
提供 Grasp 认知服务的 HTTP 接口，供所有 Agent 远程调用

后端：GraphRAG（增量索引 + local/global search）
"""
import sys
import asyncio
import json
import hashlib
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn

# Add project root and src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasp.common.models import CognitionInput, CognitionType, SourceInfo
from grasp.common.graphrag_adapter import GraspGraphRAGAdapter

app = FastAPI(title="Grasp API", version="1.0.0")

# GraphRAG workspace
WORKSPACE_ROOT = Path(__file__).parent.parent.parent / "graphrag_workspace"


def get_adapter() -> GraspGraphRAGAdapter:
    """每次请求创建新的 adapter 实例"""
    return GraspGraphRAGAdapter(workspace_root=str(WORKSPACE_ROOT))


# === Pydantic Models ===

class QueryRequest(BaseModel):
    question: str
    mode: str = "local"  # local | global
    max_results: int = 10


class InjectRequest(BaseModel):
    type: str  # fact | pattern | lesson | meta
    content: str
    tags: List[str] = []
    confidence: float = 0.95
    source: Optional[dict] = None


class UpdateRequest(BaseModel):
    cognition_id: str
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    confidence: Optional[float] = None


class AnalysisRequest(BaseModel):
    """综合研判请求"""
    query: str
    context: Optional[dict] = None
    limit: int = 10
    min_merge_score: float = 0.2
    generate_report: bool = True


class ApplicabilityRequest(BaseModel):
    """适用性分析请求"""
    query: str
    context: Optional[dict] = None
    limit: int = 10


class MergeRequest(BaseModel):
    """步骤合并请求"""
    query: str
    context: Optional[dict] = None
    limit: int = 10
    min_score: float = 0.2


# === API Routes ===

@app.post("/api/query")
async def query_cognitions(req: QueryRequest):
    """从 GraphRAG 检索认知（local_search 或 global_search）"""
    try:
        adapter = get_adapter()
        results = await adapter.async_retrieve(
            query=req.question,
            mode=req.mode,
            limit=req.max_results,
        )
        return {
            "results": [
                {
                    "cognition_id": r.cognition_id,
                    "content": r.content,
                    "type": r.type.value if hasattr(r.type, 'value') else str(r.type),
                    "tags": r.tags,
                    "confidence": r.confidence,
                    "quality_score": r.quality_score,
                }
                for r in results.items
            ],
            "total": results.total,
            "has_more": results.has_more,
        }
    except Exception as e:
        import traceback
        import sys
        tb = traceback.format_exc()
        sys.stderr.write(tb)
        sys.stderr.flush()
        return {"error": str(e), "traceback": tb, "results": [], "total": 0, "has_more": False}


@app.post("/api/inject")
async def inject_cognition(req: InjectRequest):
    """注入认知到 GraphRAG（写入文档 + 增量索引）"""
    type_map = {
        "fact": CognitionType.FACT,
        "pattern": CognitionType.PATTERN,
        "lesson": CognitionType.LESSON,
        "meta": CognitionType.META,
    }
    cognition_type = type_map.get(req.type, CognitionType.FACT)

    source = None
    if req.source:
        source = SourceInfo(
            agent_id=req.source.get("agent_id", "api"),
            task_id=req.source.get("task_id", "api"),
            channel=req.source.get("channel", "http"),
        )
    else:
        source = SourceInfo(agent_id="api", task_id="http", channel="http")

    inp = CognitionInput(
        type=cognition_type,
        content=req.content,
        source=source,
        tags=req.tags,
        confidence=req.confidence,
    )

    adapter = get_adapter()
    result = await adapter.async_inject(inp)
    return {
        "cognition_id": result.cognition_id,
        "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
        "quality_score": result.quality_score,
    }


@app.post("/api/update")
def update_cognition(req: UpdateRequest):
    """更新认知 - GraphRAG 不支持原地更新，返回错误"""
    return {
        "status": "error",
        "error": "GraphRAG does not support in-place updates. Re-inject required.",
    }


@app.post("/api/analysis")
async def comprehensive_analysis(req: AnalysisRequest):
    """综合研判分析：匹配预案 + 适用性分析 + 步骤合并 + 报告生成"""
    try:
        from grasp.analysis.analysis import get_analysis_service
        service = get_analysis_service()
        result = service.comprehensive_analysis(
            query=req.query,
            context=req.context,
            limit=req.limit,
            min_merge_score=req.min_merge_score,
            generate_report=req.generate_report,
        )
        return result
    except Exception as e:
        import traceback
        import sys
        tb = traceback.format_exc()
        sys.stderr.write(tb)
        sys.stderr.flush()
        return {"error": str(e), "traceback": tb, "status": "error"}


@app.post("/api/analysis/applicability")
async def analyze_applicability(req: ApplicabilityRequest):
    """预案适用性分析"""
    try:
        from grasp.analysis.analysis import get_analysis_service
        service = get_analysis_service()
        results = service.analyze_applicability(
            query=req.query,
            context=req.context,
            limit=req.limit,
        )
        return {
            "status": "success",
            "query": req.query,
            "plan_applicabilities": [pa.to_dict() for pa in results],
            "count": len(results),
        }
    except Exception as e:
        import traceback
        import sys
        tb = traceback.format_exc()
        sys.stderr.write(tb)
        sys.stderr.flush()
        return {"error": str(e), "traceback": tb, "status": "error"}


@app.post("/api/analysis/merge")
async def merge_steps(req: MergeRequest):
    """步骤合并"""
    try:
        from grasp.analysis.analysis import get_analysis_service
        service = get_analysis_service()
        applicabilities = service.analyze_applicability(
            query=req.query,
            context=req.context,
            limit=req.limit,
        )
        merged = service.merge_steps(applicabilities, min_score=req.min_score)
        return {
            "status": "success",
            "query": req.query,
            "merged_plan": merged.to_dict(),
        }
    except Exception as e:
        import traceback
        import sys
        tb = traceback.format_exc()
        sys.stderr.write(tb)
        sys.stderr.flush()
        return {"error": str(e), "traceback": tb, "status": "error"}


# ============================================================
# Nexus Sprint3: 认知底座 API
# ============================================================

# Cognitions data file
COGNITIONS_FILE = Path(__file__).parent.parent.parent.parent.parent.parent.parent / "skills" / "grasp" / "memory" / "grasp" / "cognitions.jsonl"
# Fallback path
if not COGNITIONS_FILE.exists():
    COGNITIONS_FILE = Path(__file__).parent.parent / "data" / "cognitions.jsonl"
if not COGNITIONS_FILE.exists():
    COGNITIONS_FILE = Path("D:/work/research/agents-nexus/skills/grasp/memory/grasp/cognitions.jsonl")

# GraphRAG output directory
GRAPHRAG_OUTPUT = Path(__file__).parent.parent.parent / "data" / "graphrag" / "output"
if not GRAPHRAG_OUTPUT.exists():
    GRAPHRAG_OUTPUT = Path("D:/work/research/agents-nexus/data/graphrag/output")
GRAPHRAG_UPDATE = Path(__file__).parent.parent.parent / "data" / "graphrag" / "update_output"
if not GRAPHRAG_UPDATE.exists():
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


def _hash_position(s: str, range_min: int = 50, range_max: int = 650) -> tuple:
    """Generate deterministic x,y position from string."""
    h = hashlib.md5(s.encode()).hexdigest()
    x = range_min + int(h[:4], 16) % (range_max - range_min)
    y = range_min + int(h[4:8], 16) % (range_max - range_min)
    return x, y


def _try_load_graph_data():
    """Try to load graph nodes/edges from GraphRAG parquet files.
    Returns (nodes, edges) or ([], []) if unavailable."""
    try:
        import pandas as pd
    except ImportError:
        return [], []

    # Look for entities/relationships in update_output (most recent)
    entities_path = None
    relationships_path = None

    # Search update_output for the latest run
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

    # Fallback: check main output
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

    # Load nodes from entities
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

    # Load edges from relationships
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
                        "label": label[:50],  # Truncate long labels
                    })
        except Exception:
            pass

    return nodes, edges


@app.get("/api/v1/grasp/knowledge")
def list_knowledge(
    type: Optional[str] = Query(None, description="Filter by cognition type: fact, pattern, lesson, meta"),
    tag: Optional[List[str]] = Query(None, description="Filter by tag(s). Support multiple: ?tag=a&tag=b"),
):
    """列出所有认知，支持按类型和标签过滤。"""
    try:
        cognitions = _load_cognitions()

        # Filter by type
        if type:
            cognitions = [c for c in cognitions if c.get("type") == type]

        # Filter by tag(s)
        if tag:
            tag_set = set(t.lower() for t in tag)
            cognitions = [c for c in cognitions if any(
                t.lower() in tag_set for t in c.get("tags", [])
            )]

        return {
            "status": "success",
            "total": len(cognitions),
            "cognitions": cognitions,
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        sys.stderr.write(tb)
        sys.stderr.flush()
        return {"status": "error", "error": str(e), "total": 0, "cognitions": []}


@app.get("/api/v1/grasp/graph")
def get_graph(q: Optional[str] = Query(None, description="Search keyword to filter nodes")):
    """返回知识图谱数据（nodes/edges），支持关键词搜索。"""
    try:
        nodes, edges = _try_load_graph_data()

        # Filter by keyword if provided
        if q:
            q_lower = q.lower()
            nodes = [n for n in nodes if q_lower in n["label"].lower() or q_lower in n.get("category", "").lower()]
            # Also filter edges to only include those connecting visible nodes
            visible_ids = {n["id"] for n in nodes}
            edges = [e for e in edges if e["from"] in visible_ids and e["to"] in visible_ids]

        return {
            "status": "success",
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        sys.stderr.write(tb)
        sys.stderr.flush()
        return {"status": "error", "error": str(e), "nodes": [], "edges": []}


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "grasp", "backend": "graphrag"}


@app.get("/api/v1/grasp/cognition-assessment/{agent_id}")
async def cognition_assessment(agent_id: str):
    """
    4 维度认知评估：检索质量、上下文利用率、注入准确率、知识新鲜度
    从 cognitions.jsonl + trace reports 计算
    """
    try:
        from grasp.analysis.cognitive_assessment import get_assessment_service
        service = get_assessment_service()
        result = service.assess(agent_id=agent_id)
        return result.to_dict()
    except Exception as e:
        import traceback
        import sys
        tb = traceback.format_exc()
        sys.stderr.write(tb)
        sys.stderr.flush()
        return {"error": str(e), "traceback": tb, "agent_id": agent_id}


@app.get("/")
def root():
    return {"service": "Grasp API", "version": "1.0.0", "backend": "graphrag", "docs": "/docs"}


# === Main ===

def main():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    main()
