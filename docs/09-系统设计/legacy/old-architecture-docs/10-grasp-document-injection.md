# Nexus Grasp 文档注入方案

**版本**: v1.0  
**日期**: 2026-04-03  
**负责人**: 蚊子  
**状态**: 设计完成

---

## 1. 背景与目标

### 1.1 问题陈述

Grasp（悟）是 Nexus 平台的认知核心，需要注入领域知识后才能有效工作。当前 Nexus 项目积累了大量文档，但尚未形成系统化的注入机制。

**现状**：

- Nexus 文档散落在 `docs/` 目录下，共 21 个 Markdown 文件
- 文档覆盖愿景、架构、技能设计、项目管理等多个维度
- 没有统一的注入方案，文档知识无法被 Grasp 认知系统利用

**目标**：

- 建立文档分类体系，明确哪些文档需要注入
- 制定注入优先级，确保关键文档优先注入
- 设计批量注入流程，支持一次性注入大量文档

### 1.2 与 GLG Pipeline 的关系

文档注入是 Grasp 认知获取的主要途径之一。GLG Pipeline 提供三个处理阶段：

| 阶段 | 输入 | 输出 | 耗时 |
|------|------|------|------|
| Discovery | 文档集合 | 领域概念图 | 5-30 分钟 |
| Extraction | 文档 | 结构化知识 | 10-60 分钟 |
| Build | 知识碎片 | 可查询知识图谱 | 5-20 分钟 |

文档注入流程与 GLG Pipeline 的对应关系：

```
文档注入 ──→ Discovery（发现领域概念）──→ Extraction（提取知识）──→ Build（构建图谱）
              ↓
         批量注入支持
         （分批调度 + 进度跟踪）
```

### 1.3 文档分类框架

Nexus 文档分为五类，对应 Grasp 的不同认知类型：

| 文档类型 | Grasp 认知类型 | 注入后行为 |
|---------|--------------|-----------|
| **A. 元认知文档** | meta（元认知） | Grasp 自我理解，不直接响应查询 |
| **B. 领域事实文档** | fact（事实） | 回答"是什么"类问题 |
| **C. 架构模式文档** | pattern（模式） | 回答"怎么做"类问题 |
| **D. 经验教训文档** | lesson（经验） | 回答"如何做得更好"类问题 |
| **E. 外部参考文档** | fact（事实） | 参考背景知识，置信度较低 |

---

## 2. 文档清单

### 2.1 完整清单

以下为 Nexus 项目所有 Markdown 文档的完整清单，按注入批次组织。

#### 批次 0：元认知文档（最优先注入）

| # | 文件名 | 路径 | 类型 | 认知类型 | 优先级 | 注入方式 |
|---|--------|------|------|---------|--------|----------|
| 0-1 | nexus-vision.md | `docs/` | 元认知 | meta | P0 | 即时注入 |
| 0-2 | nexus-reading-guide.md | `docs/` | 元认知 | meta | P0 | 即时注入 |

#### 批次 1：Nexus 核心架构文档

| # | 文件名 | 路径 | 类型 | 认知类型 | 优先级 | 注入方式 |
|---|--------|------|------|---------|--------|----------|
| 1-1 | 00-platform-architecture.md | `docs/03-架构设计/` | 架构事实 | fact | P0 | GLG Discovery+Extraction |
| 1-2 | 01-grasp-architecture.md | `docs/03-架构设计/` | 架构模式 | pattern | P0 | GLG Discovery+Extraction |
| 1-3 | 02-reins-architecture.md | `docs/03-架构设计/` | 架构事实+模式 | fact+pattern | P0 | GLG Discovery+Extraction |
| 1-4 | 03-evo-architecture.md | `docs/03-架构设计/` | 架构事实+模式 | fact+pattern | P1 | GLG Discovery+Extraction |
| 1-5 | 04-reach-architecture.md | `docs/03-架构设计/` | 架构事实+模式 | fact+pattern | P1 | GLG Discovery+Extraction |
| 1-6 | 05-vigil-architecture.md | `docs/03-架构设计/` | 架构事实+模式 | fact+pattern | P0 | GLG Discovery+Extraction |

#### 批次 2：Grasp 核心文档

| # | 文件名 | 路径 | 类型 | 认知类型 | 优先级 | 注入方式 |
|---|--------|------|------|---------|--------|----------|
| 2-1 | 09-glg-integration.md | `docs/03-架构设计/` | 集成知识 | fact | P0 | GLG Discovery+Extraction |
| 2-2 | 01-grasp-skill-design.md | `docs/03-架构设计/` | 技能设计 | fact | P0 | GLG Discovery+Extraction |
| 2-3 | 06-agent-sdk-architecture.md | `docs/03-架构设计/` | SDK 架构 | fact | P1 | GLG Discovery+Extraction |
| 2-4 | 07-interface-architecture.md | `docs/03-架构设计/` | 接口架构 | fact | P1 | GLG Discovery+Extraction |
| 2-5 | 08-logging-framework.md | `docs/03-架构设计/` | 日志框架 | fact | P2 | GLG Discovery+Extraction |

#### 批次 3：项目管理和产品文档

| # | 文件名 | 路径 | 类型 | 认知类型 | 优先级 | 注入方式 |
|---|--------|------|------|---------|--------|----------|
| 3-1 | nexus-architecture-doc-standard.md | `docs/06-项目管理/` | 流程规范 | pattern | P1 | GLG Discovery+Extraction |
| 3-2 | nexus-design-doc-standard.md | `docs/06-项目管理/` | 流程规范 | pattern | P1 | GLG Discovery+Extraction |
| 3-3 | nexus-mvp-plan.md | `docs/06-项目管理/` | 计划事实 | fact | P1 | GLG Discovery+Extraction |
| 3-4 | nexus-rtm.md | `docs/06-项目管理/` | 需求跟踪 | fact | P2 | GLG Discovery+Extraction |
| 3-5 | nexus-architecture-meeting-20260328.md | `docs/06-项目管理/` | 会议记录 | lesson | P2 | GLG Extraction（轻量） |

#### 批次 4：产品与竞争分析

| # | 文件名 | 路径 | 类型 | 认知类型 | 优先级 | 注入方式 |
|---|--------|------|------|---------|--------|----------|
| 4-1 | tianjiang-competitive-analysis.md | `docs/07-产品介绍/` | 竞争分析 | fact | P2 | GLG Extraction（轻量） |
| 4-2 | tianjiang-competitive-analysis-appendix.md | `docs/07-产品介绍/` | 竞争附录 | fact | P3 | GLG Extraction（轻量） |

#### 批次 5：待识别文档（子目录或新增）

| # | 文件名 | 路径 | 类型 | 认知类型 | 优先级 | 说明 |
|---|--------|------|------|---------|--------|------|
| 5-1 | (01-db-connection-pool.md) | `docs/04-主要模块/` | 技术细节 | fact | P2 | 需确认文件是否存在 |
| 5-2 | (其他子目录文档) | - | - | - | - | 需进一步盘点 |

### 2.2 文档统计

| 指标 | 数量 |
|------|------|
| 总 Markdown 文档数 | 21+ |
| 批次 0（P0 必注） | 2 |
| 批次 1（P0 核心） | 6 |
| 批次 2（技能相关） | 5 |
| 批次 3（项目流程） | 5 |
| 批次 4（竞争分析） | 2 |
| 待确认 | 1+ |

### 2.3 注入优先级矩阵

优先级由两个维度决定：

- **业务重要性**：文档对 Grasp 认知能力的贡献度
- **依赖关系**：某些文档的存在是其他文档发挥作用的前提

| 优先级 | 文档数 | 说明 |
|--------|--------|------|
| **P0** | 9 | 必须优先注入，核心架构和元认知 |
| **P1** | 7 | 早期注入，支持功能完善 |
| **P2** | 5 | 中期注入，丰富知识库 |
| **P3** | 1 | 按需注入，置信度较低 |

---

## 3. 注入优先级设计

### 3.1 优先级分层依据

```
文档对 Grasp 的价值
        │
        │  高
        ├─────────────────────────────┐
        │                             │
   架构类文档                    流程类文档
   (事实+模式)                   (规范+模板)
        │                             │
        │                      对 Grasp 直接
        │                      认知贡献较小
        │                             │
        └──────────┬──────────────────┘
                   │
              依赖关系
   需先注入基础文档才能理解高级文档
```

**优先级判定规则**：

| 维度 | P0 条件 | P1 条件 | P2 条件 |
|------|---------|---------|---------|
| **业务重要度** | Grasp 自身或五兄弟核心架构 | 支撑性设计 | 参考背景 |
| **依赖关系** | 无前置依赖或前置文档也是 P0 | 前置为 P0 | 前置为 P1/P2 |
| **认知类型** | meta、pattern | fact（关键） | fact（参考）、lesson |
| **更新频率** | 低（核心不变） | 中 | 高或低均可 |

### 3.2 分批注入计划

#### 批次 0：元认知文档（即时注入）

**目标**：让 Grasp 首先理解"自己是什么、自己在做什么"

**注入策略**：
- 不经过 GLG Pipeline 的长流程
- 直接调用 Grasp Skill 的 `inject` 接口，类型为 `meta`
- 由人工审核确保认知正确性

**文档**：
1. `nexus-vision.md` — Nexus 产品愿景和核心信念
2. `nexus-reading-guide.md` — Nexus 文档体系和阅读路径

**预期输出**：
- Grasp 理解 Nexus 的使命、五兄弟架构、核心信念
- 后续文档注入时可参照此认知进行一致性校验

---

#### 批次 1：平台与五兄弟核心架构

**目标**：建立对 Nexus 平台整体架构和五兄弟职责的认知

**注入策略**：
- GLG Discovery（发现领域概念）→ Extraction（提取结构化知识）→ Build（构建知识图谱）
- 全量处理，确保知识图谱完整性

**文档执行顺序**：

```
Discovery 批次 1
    │
    ├── 00-platform-architecture.md  ← 平台整体架构
    ├── 01-grasp-architecture.md     ← 悟自身架构（依赖平台架构）
    ├── 02-reins-architecture.md     ← 御架构
    ├── 03-evo-architecture.md       ← 化架构
    ├── 04-reach-architecture.md     ← 达架构
    └── 05-vigil-architecture.md     ← 鉴架构
           ↓
      Discovery 完成
           ↓
Extraction 批次 1（并行）
    │
    └── [同上 6 个文档]
           ↓
      Extraction 完成
           ↓
Build 批次 1
    │
    └── 构建跨文档知识关联
```

**关键依赖**：
- `01-grasp-architecture.md` 依赖 `00-platform-architecture.md` 的 Discovery 结果
- 注入顺序遵循上述执行顺序

---

#### 批次 2：Grasp 技能与集成文档

**目标**：建立对 Grasp 自身技能设计和 GLG 集成方案的理解

**注入策略**：
- GLG 全量处理
- 重点提取接口定义、流程图、错误处理逻辑

**文档执行顺序**：

```
Discovery 批次 2
    │
    ├── 09-glg-integration.md        ← GLG 集成（最关键）
    ├── 01-grasp-skill-design.md     ← Grasp Skill 接口
    ├── 06-agent-sdk-architecture.md ← Agent SDK 架构
    ├── 07-interface-architecture.md ← 接口架构
    └── 08-logging-framework.md      ← 日志框架（最后）
           ↓
      [同批次 1 流程]
```

---

#### 批次 3-4：项目管理和产品文档

**目标**：建立对项目管理流程、竞争环境的理解

**注入策略**：
- 采用轻量 Extraction（跳过 Discovery，直接提取关键信息）
- 会议记录等半结构化文档使用较低置信度

---

### 3.3 优先级总结

```
注入顺序：批次 0 → 批次 1 → 批次 2 → 批次 3 → 批次 4
           │         │         │         │         │
        元认知    平台+五兄弟  技能+集成  项目管理   竞品分析
         (2)         (6)        (5)       (5)       (2)
          ↓          ↓          ↓         ↓         ↓
       即时注入   GLG全量    GLG全量   轻量Ext   轻量Ext
```

---

## 4. 批量注入支持

### 4.1 批量注入流程

```
┌──────────────────────────────────────────────────────────────┐
│                   批量注入执行流程                            │
└──────────────────────────────────────────────────────────────┘

Step 1: 文档盘点
    │
    ├── 自动扫描 docs/ 目录
    ├── 识别所有 Markdown 文件
    ├── 按分类框架打标签
    └── 生成注入清单（批次 + 优先级）

Step 2: 预检
    │
    ├── 验证文件可读
    ├── 检查文件大小（单文件 > 10MB 则拆分）
    ├── 去重（同名文件、重复内容检测）
    └── 生成预检报告

Step 3: 分批调度
    │
    ├── 按批次顺序调度
    ├── 批次内文档并行处理
    ├── 批次间串行（等待前一批次 Build 完成）
    └── 支持中断恢复（记录断点）

Step 4: GLG Pipeline 执行
    │
    ├── Discovery（发现领域概念）
    ├── Extraction（提取结构化知识）
    └── Build（构建知识图谱）

Step 5: 注入结果验收
    │
    ├── 验证注入成功率（成功数/总数）
    ├── 抽样检查认知条目质量
    ├── 检查知识图谱关联完整性
    └── 生成注入报告

Step 6: 异常处理
    │
    ├── 单文档失败：记录并继续，批次结束后重试
    ├── 批次失败：停止并告警，人工介入
    └── 整体失败：回滚已注入的认知条目
```

### 4.2 文档扫描与清单生成

```python
# grasp_batch_inject/scanner.py

import os
import hashlib
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

class DocType(Enum):
    META = "meta"           # 元认知
    FACT = "fact"           # 事实
    PATTERN = "pattern"     # 模式
    LESSON = "lesson"       # 经验

class Priority(Enum):
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3

@dataclass
class Document:
    path: str
    filename: str
    doc_type: DocType
    priority: Priority
    batch: int
    cognition_type: str  # fact, pattern, lesson, meta
    inject_method: str   # "immediate", "glg_full", "glg_light"
    hash: str = ""
    size_bytes: int = 0
    errors: List[str] = field(default_factory=list)

class DocumentScanner:
    """扫描 docs/ 目录，生成注入清单"""

    # 文件名到类型的映射规则
    TYPE_RULES = {
        "nexus-vision": (DocType.META, Priority.P0, "immediate"),
        "nexus-reading-guide": (DocType.META, Priority.P0, "immediate"),
        "architecture": (DocType.PATTERN, Priority.P0, "glg_full"),
        "grasp": (DocType.PATTERN, Priority.P0, "glg_full"),
        "reins": (DocType.PATTERN, Priority.P0, "glg_full"),
        "vigil": (DocType.PATTERN, Priority.P0, "glg_full"),
        "evo": (DocType.PATTERN, Priority.P1, "glg_full"),
        "reach": (DocType.PATTERN, Priority.P1, "glg_full"),
        "integration": (DocType.FACT, Priority.P0, "glg_full"),
        "skill-design": (DocType.FACT, Priority.P0, "glg_full"),
        "sdk": (DocType.FACT, Priority.P1, "glg_full"),
        "interface": (DocType.FACT, Priority.P1, "glg_full"),
        "logging": (DocType.FACT, Priority.P2, "glg_full"),
        "standard": (DocType.PATTERN, Priority.P1, "glg_full"),
        "meeting": (DocType.LESSON, Priority.P2, "glg_light"),
        "competitive": (DocType.FACT, Priority.P2, "glg_light"),
        "mvp": (DocType.FACT, Priority.P1, "glg_full"),
    }

    BATCH_RULES = {
        "meta": 0,
        "platform-architecture": 1,
        "grasp-architecture": 1,
        "reins-architecture": 1,
        "vigil-architecture": 1,
        "evo-architecture": 1,
        "reach-architecture": 1,
        "integration": 2,
        "skill-design": 2,
        "sdk": 2,
        "interface": 2,
        "logging": 2,
        "standard": 3,
        "meeting": 3,
        "mvp": 3,
        "competitive": 4,
    }

    def __init__(self, docs_dir: str):
        self.docs_dir = Path(docs_dir)

    def scan(self) -> List[Document]:
        """扫描目录，返回文档清单"""
        documents = []
        for md_file in self.docs_dir.rglob("*.md"):
            doc = self._classify_file(md_file)
            if doc:
                documents.append(doc)
        return sorted(documents, key=lambda d: (d.batch, d.priority.value))

    def _classify_file(self, path: Path) -> Optional[Document]:
        """根据文件名分类文档"""
        rel_path = path.relative_to(self.docs_dir)
        filename = path.stem.lower()

        doc_type, priority, inject_method = self._match_rules(filename)

        # 确定批次
        batch = self.BATCH_RULES.get(filename, 3)

        # 计算文件哈希
        content = path.read_bytes()
        file_hash = hashlib.md5(content).hexdigest()

        return Document(
            path=str(rel_path),
            filename=filename,
            doc_type=doc_type,
            priority=priority,
            batch=batch,
            cognition_type=self._doc_type_to_cognition(doc_type),
            inject_method=inject_method,
            hash=file_hash,
            size_bytes=len(content),
        )

    def _match_rules(self, filename: str) -> tuple:
        """匹配分类规则"""
        for keyword, (doc_type, priority, method) in self.TYPE_RULES.items():
            if keyword in filename:
                return doc_type, priority, method
        return DocType.FACT, Priority.P2, "glg_light"

    def _doc_type_to_cognition(self, doc_type: DocType) -> str:
        """文档类型转认知类型"""
        return {
            DocType.META: "meta",
            DocType.FACT: "fact",
            DocType.PATTERN: "pattern",
            DocType.LESSON: "lesson",
        }[doc_type]
```

### 4.3 批量注入执行器

```python
# grasp_batch_inject/executor.py

import asyncio
import json
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
from .scanner import Document, DocumentScanner, Priority

class BatchStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

@dataclass
class InjectResult:
    document: Document
    success: bool
    cognition_ids: List[str]
    error: Optional[str]
    duration_ms: int

@dataclass
class BatchResult:
    batch: int
    status: BatchStatus
    total: int
    succeeded: int
    failed: int
    results: List[InjectResult]
    total_duration_ms: int

class BatchInjector:
    """批量注入执行器"""

    def __init__(self, grasp_client, glg_client, max_parallel: int = 3):
        self.grasp = grasp_client
        self.glg = glg_client
        self.max_parallel = max_parallel
        self.checkpoint_file = "batch_inject_checkpoint.json"

    async def run(self, documents: List[Document]) -> Dict[int, BatchResult]:
        """执行批量注入，按批次组织"""
        # 按批次分组
        batches: Dict[int, List[Document]] = {}
        for doc in documents:
            batches.setdefault(doc.batch, []).append(doc)

        results = {}

        for batch_num in sorted(batches.keys()):
            batch_docs = batches[batch_num]
            print(f"\n=== 处理批次 {batch_num} ({len(batch_docs)} 个文档) ===")

            result = await self._run_batch(batch_num, batch_docs)
            results[batch_num] = result

            # 批次间串行：等待 Build 完成
            if batch_num > 0:
                await self._wait_for_build_completion(result)

        return results

    async def _run_batch(self, batch_num: int, documents: List[Document]) -> BatchResult:
        """执行单个批次"""
        start_time = time.time()
        results = []

        if documents[0].inject_method == "immediate":
            # 批次 0：即时注入
            results = await self._run_immediate_batch(documents)
        elif documents[0].inject_method == "glg_light":
            # 轻量 Extraction
            results = await self._run_glg_light_batch(documents)
        else:
            # GLG 全量处理
            results = await self._run_glg_full_batch(documents)

        succeeded = sum(1 for r in results if r.success)
        failed = len(results) - succeeded

        duration_ms = int((time.time() - start_time) * 1000)

        status = BatchStatus.COMPLETED if failed == 0 else (
            BatchStatus.PARTIAL if succeeded > 0 else BatchStatus.FAILED
        )

        return BatchResult(
            batch=batch_num,
            status=status,
            total=len(documents),
            succeeded=succeeded,
            failed=failed,
            results=results,
            total_duration_ms=duration_ms,
        )

    async def _run_glg_full_batch(self, documents: List[Document]) -> List[InjectResult]:
        """GLG 全量处理：Discovery → Extraction → Build"""
        results = []

        # 阶段 1: Discovery（并行发现概念）
        print(f"  [Discovery] 发现领域概念...")
        discovery_task = await self.glg.discovery_start(
            document_paths=[d.path for d in documents]
        )
        discovery_id = discovery_task["task_id"]

        # 轮询 Discovery 状态
        discovery_result = await self._poll_task(discovery_id, stages=["discovery"])
        if not discovery_result["success"]:
            return [self._failed_result(d, discovery_result["error"]) for d in documents]

        # 阶段 2: Extraction（并行提取）
        print(f"  [Extraction] 提取结构化知识...")
        extraction_tasks = []
        for doc in documents:
            task = await self.glg.extract_start(
                document_path=doc.path,
                schema=self._get_extraction_schema(doc),
            )
            extraction_tasks.append((doc, task["task_id"]))

        extraction_results = await self._poll_tasks(
            [tid for _, tid in extraction_tasks],
            stage="extraction"
        )

        # 收集 Extraction 结果
        for (doc, tid), result in zip(extraction_tasks, extraction_results):
            if result["success"]:
                inject_result = await self._inject_to_grasp(doc, result["data"])
                results.append(inject_result)
            else:
                results.append(self._failed_result(doc, result["error"]))

        # 阶段 3: Build（构建知识图谱）
        print(f"  [Build] 构建知识图谱...")
        build_task = await self.glg.build_start(
            discovery_id=discovery_id,
            extraction_results=[r.data for r in results if r.success]
        )
        await self._poll_task(build_task["task_id"], stages=["build"])

        return results

    async def _inject_to_grasp(self, doc: Document, data: Dict[str, Any]) -> InjectResult:
        """将提取结果注入 Grasp"""
        start = time.time()
        try:
            result = await self.grasp.inject({
                "type": doc.cognition_type,
                "content": json.dumps(data, ensure_ascii=False),
                "source": {
                    "document": doc.path,
                    "batch": doc.batch,
                },
                "tags": [doc.filename, f"batch_{doc.batch}"],
                "confidence": self._priority_to_confidence(doc.priority),
            })

            duration_ms = int((time.time() - start) * 1000)

            return InjectResult(
                document=doc,
                success=True,
                cognition_ids=[result.get("cognition_id", "")],
                error=None,
                duration_ms=duration_ms,
            )
        except Exception as e:
            return self._failed_result(doc, str(e))

    def _priority_to_confidence(self, priority: Priority) -> float:
        """优先级转初始置信度"""
        return {
            Priority.P0: 0.95,
            Priority.P1: 0.85,
            Priority.P2: 0.75,
            Priority.P3: 0.60,
        }[priority]

    async def _poll_task(self, task_id: str, stages: List[str]) -> Dict[str, Any]:
        """轮询任务状态"""
        stage_names = "+".join(stages)
        while True:
            status = await self.glg.get_task_status(task_id)
            print(f"    [{stage_names}] {status['progress']:.0%} - {status.get('current_stage', 'running')}")

            if status["state"] == "completed":
                return {"success": True, "data": status["result"]}
            elif status["state"] in ("failed", "cancelled"):
                return {"success": False, "error": status.get("error", "Unknown error")}
            elif status["state"] == "pending" and status["progress"] == 0:
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(30)

    async def _poll_tasks(self, task_ids: List[str], stage: str) -> List[Dict[str, Any]]:
        """并行轮询多个任务"""
        tasks = [self._poll_task(tid, [stage]) for tid in task_ids]
        return await asyncio.gather(*tasks)

    def _failed_result(self, doc: Document, error: str) -> InjectResult:
        """创建失败结果"""
        return InjectResult(
            document=doc,
            success=False,
            cognition_ids=[],
            error=error,
            duration_ms=0,
        )
```

### 4.4 断点恢复机制

```python
# grasp_batch_inject/checkpoint.py

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

@dataclass
class Checkpoint:
    """注入检查点"""
    batch: int
    completed_documents: List[str]  # 已完成文档的 hash 列表
    failed_documents: Dict[str, str]  # hash -> error
    total_duration_ms: int
    timestamp: float

    def save(self, path: str = "batch_inject_checkpoint.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False)

    @classmethod
    def load(cls, path: str = "batch_inject_checkpoint.json") -> Optional["Checkpoint"]:
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def is_document_done(self, doc_hash: str) -> bool:
        """检查文档是否已完成"""
        return doc_hash in self.completed_documents

    def mark_completed(self, doc_hash: str):
        """标记文档完成"""
        if doc_hash not in self.completed_documents:
            self.completed_documents.append(doc_hash)

    def mark_failed(self, doc_hash: str, error: str):
        """标记文档失败"""
        self.failed_documents[doc_hash] = error

# 使用示例
class ResumableBatchInjector(BatchInjector):
    """支持断点恢复的批量注入器"""

    async def run(self, documents: List[Document]) -> Dict[int, BatchResult]:
        checkpoint = Checkpoint.load()
        documents_to_skip = set()

        if checkpoint:
            print(f"检测到检查点，跳过 {len(checkpoint.completed_documents)} 个已完成文档")
            documents_to_skip = set(checkpoint.completed_documents)

        # 过滤待处理文档
        pending = [d for d in documents if d.hash not in documents_to_skip]

        results = await super().run(pending)

        # 更新检查点
        for batch_result in results.values():
            for r in batch_result.results:
                if r.success:
                    checkpoint.mark_completed(r.document.hash)
                else:
                    checkpoint.mark_failed(r.document.hash, r.error)
                checkpoint.total_duration_ms += r.duration_ms

        checkpoint.save()
        return results
```

### 4.5 注入报告

```python
# grasp_batch_inject/report.py

from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime
import json

@dataclass
class InjectReport:
    total_documents: int
    total_batches: int
    succeeded: int
    failed: int
    total_duration_ms: int
    batch_results: Dict[int, dict]
    failed_documents: List[dict]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def print_summary(self):
        print("\n" + "=" * 60)
        print("  文档注入报告")
        print("=" * 60)
        print(f"  总文档数：{self.total_documents}")
        print(f"  总批次数：{self.total_batches}")
        print(f"  成功：{self.succeeded} ({self.succeeded/self.total_documents*100:.1f}%)")
        print(f"  失败：{self.failed} ({self.failed/self.total_documents*100:.1f}%)")
        print(f"  总耗时：{self.total_duration_ms/1000:.1f}s")
        print()

        for batch_num, br in self.batch_results.items():
            status_icon = {"completed": "✅", "partial": "⚠️", "failed": "❌"}[br["status"]]
            print(f"  批次 {batch_num} {status_icon}: {br['succeeded']}/{br['total']} 成功 ({br['duration_ms']/1000:.1f}s)")

        if self.failed_documents:
            print("\n  失败文档：")
            for fd in self.failed_documents:
                print(f"    - {fd['path']}: {fd['error']}")

        print("=" * 60)
```

---

## 5. 执行计划

### 5.1 注入时间估算

| 批次 | 文档数 | 预估耗时 | 说明 |
|------|--------|----------|------|
| 批次 0 | 2 | < 1 分钟 | 即时注入，无 GLG 处理 |
| 批次 1 | 6 | 40-90 分钟 | GLG 全量，Discovery 5-30min + Extraction 10-30min + Build 5-20min |
| 批次 2 | 5 | 30-60 分钟 | GLG 全量，类似批次 1 但文档较少 |
| 批次 3 | 5 | 10-20 分钟 | 轻量 Extraction，无 Discovery |
| 批次 4 | 2 | 5-10 分钟 | 轻量 Extraction |
| **合计** | **20+** | **约 2 小时** | - |

### 5.2 执行前提条件

- [ ] GLG Pipeline 服务正常运行
- [ ] Grasp Skill 接口可用（inject/retrieve/update）
- [ ] 待注入文档已同步到工作目录
- [ ] 检查点文件目录可写（用于断点恢复）

### 5.3 执行步骤

```
1. 前置检查
   $ python grasp_batch_inject/check.py

2. 扫描文档
   $ python -m grasp_batch_inject scan --docs-dir docs/ --output inject_manifest.json

3. 预检
   $ python -m grasp_batch_inject preflight --manifest inject_manifest.json

4. 执行批量注入
   $ python -m grasp_batch_inject run --manifest inject_manifest.json [--resume]

5. 生成报告
   $ python -m grasp_batch_inject report --output inject_report.json
```

---

## 6. 待明确事项

1. **批次 1 Discovery 的并行上限**：GLG Discovery 阶段对大文档集合的处理能力上限待确认
2. **批次 0 即时注入的具体接口**：Grasp Skill 的 `inject` 接口是否支持 `meta` 类型，待确认
3. **置信度校准**：文档来源的初始置信度是否需要根据文档状态（已发布/草稿）调整
4. **PDF 文档处理**：部分文档为 PDF 格式（`产品介绍投标.pdf`、`天工智能体实现.pdf`），是否纳入注入范围

---

## 📅 更新日志

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-04-03 | v1.0 | 初始版本。包含文档清单、优先级设计、批量注入流程代码框架。 |

---

## 参考文档

1. `nexus-vision.md` — Nexus 产品愿景（锚点文档）
2. `nexus-reading-guide.md` — Nexus 文档阅读指南
3. `01-grasp-architecture.md` — Grasp 架构设计
4. `09-glg-integration.md` — GLG 集成方案
5. `01-grasp-skill-design.md` — Grasp Skill 接口设计
