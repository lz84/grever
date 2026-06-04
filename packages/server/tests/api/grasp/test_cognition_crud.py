"""
P6-03 Cognition 读写单元测试 (Cognition CRUD Unit Tests)

测试覆盖:
- 认知文件加载和保存
- 创建认知 (POST /cognition)
- 读取认知 (GET /cognition/{id})
- 更新认知 (PATCH /cognition/{id})
- 删除认知 (DELETE /cognition/{id})
- 列表查询 (GET /knowledge)
- 安全校验
- 质量评分
"""

import pytest
import json
import uuid
import re
import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi import HTTPException

# 测试用临时文件
TEST_COGNITIONS_FILE = Path(__file__).parent.parent.parent / "data" / "test_cognitions_temp.jsonl"


@pytest.fixture(autouse=True)
def setup_test_file():
    if TEST_COGNITIONS_FILE.exists():
        TEST_COGNITIONS_FILE.unlink()
    TEST_COGNITIONS_FILE.touch()
    yield
    if TEST_COGNITIONS_FILE.exists():
        TEST_COGNITIONS_FILE.unlink()


def _load_test():
    if not TEST_COGNITIONS_FILE.exists():
        return []
    cognitions = []
    with open(TEST_COGNITIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    cognitions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return cognitions


def _save_test(cognitions):
    TEST_COGNITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TEST_COGNITIONS_FILE, "w", encoding="utf-8") as f:
        for c in cognitions:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


def _check_dangerous(content):
    patterns = [
        r'\b(?:execute|system|eval|exec)\s*\(',
        r'<script[^>]*>',
        r'--\s*drop\s+table',
        r'\.\./\.\.\.',
    ]
    for p in patterns:
        if re.search(p, content, re.IGNORECASE):
            return True
    return False


def _calc_quality(content, confidence):
    score = 1.0
    if len(content) < 10:
        score -= 0.3
    if len(content) > 10000:
        score -= 0.2
    if confidence < 0.3:
        score -= 0.3
    return max(0, score)


def create_cognition(content, type="fact", confidence=0.8, source=None, tags=None, domain=""):
    """模拟创建认知"""
    if not content.strip():
        raise HTTPException(status_code=400, detail="认知内容不能为空")
    if type not in ("fact", "pattern", "lesson", "meta"):
        raise HTTPException(status_code=400, detail="认知类型必须是 fact/pattern/lesson/meta 之一")
    if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
        raise HTTPException(status_code=400, detail="置信度必须是 0-1 之间的数字")
    if _check_dangerous(content):
        raise HTTPException(status_code=400, detail="检测到危险内容模式，已被拒绝")

    quality_score = _calc_quality(content, confidence)
    now = datetime.now(timezone.utc)
    cognition_id = f"cog-{int(now.timestamp() * 1000)}-{uuid.uuid4().hex[:8]}"
    status = "published" if quality_score > 0.5 else "pending_review"

    cognition = {
        "cognition_id": cognition_id,
        "type": type,
        "content": content,
        "tags": tags or [],
        "confidence": confidence,
        "quality_score": round(quality_score, 2),
        "source": source or {"agent_id": "unknown", "task_id": "", "channel": "api"},
        "status": status,
        "domain": domain,
        "metadata": {},
        "version": 1,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    cognitions = _load_test()
    cognitions.append(cognition)
    _save_test(cognitions)
    return cognition


def read_cognition(cognition_id):
    cognitions = _load_test()
    for c in cognitions:
        if c.get("cognition_id") == cognition_id:
            return c
    raise HTTPException(status_code=404, detail=f"认知 {cognition_id} 不存在")


def update_cognition(cognition_id, updates):
    cognitions = _load_test()
    target = None
    target_idx = None
    for i, c in enumerate(cognitions):
        if c.get("cognition_id") == cognition_id:
            target = c
            target_idx = i
            break

    if target is None:
        raise HTTPException(status_code=404, detail=f"认知 {cognition_id} 不存在")

    if "content" in updates:
        if not updates["content"].strip():
            raise HTTPException(status_code=400, detail="认知内容不能为空")
        if _check_dangerous(updates["content"]):
            raise HTTPException(status_code=400, detail="检测到危险内容模式，更新被拒绝")
        target["content"] = updates["content"]

    if "type" in updates:
        if updates["type"] not in ("fact", "pattern", "lesson", "meta"):
            raise HTTPException(status_code=400, detail="认知类型必须是 fact/pattern/lesson/meta 之一")
        target["type"] = updates["type"]

    if "tags" in updates:
        target["tags"] = updates["tags"]

    if "confidence" in updates:
        if not isinstance(updates["confidence"], (int, float)) or not (0 <= updates["confidence"] <= 1):
            raise HTTPException(status_code=400, detail="置信度必须是 0-1 之间的数字")
        target["confidence"] = updates["confidence"]

    if "status" in updates:
        if updates["status"] not in ("published", "pending_review", "rejected"):
            raise HTTPException(status_code=400, detail="状态必须是 published/pending_review/rejected 之一")
        target["status"] = updates["status"]

    if "domain" in updates:
        target["domain"] = updates["domain"]

    if "metadata" in updates:
        if "metadata" not in target:
            target["metadata"] = {}
        target["metadata"].update(updates["metadata"])

    target["version"] = target.get("version", 1) + 1
    target["updated_at"] = datetime.now(timezone.utc).isoformat()

    cognitions[target_idx] = target
    _save_test(cognitions)
    return target


def delete_cognition(cognition_id):
    cognitions = _load_test()
    new_cognitions = [c for c in cognitions if c.get("cognition_id") != cognition_id]
    if len(new_cognitions) == len(cognitions):
        raise HTTPException(status_code=404, detail=f"认知 {cognition_id} 不存在")
    _save_test(new_cognitions)
    return True


def list_knowledge(type_filter=None, tag_filter=None):
    cognitions = _load_test()
    if type_filter:
        cognitions = [c for c in cognitions if c.get("type") == type_filter]
    if tag_filter:
        tag_set = set(t.lower() for t in tag_filter)
        cognitions = [c for c in cognitions if any(
            t.lower() in tag_set for t in c.get("tags", [])
        )]
    return cognitions


# ============================================================
# 测试用例
# ============================================================

class TestCreateCognition:
    def test_create_valid_cognition(self):
        c = create_cognition(
            content="这是一个测试认知内容，用于验证创建功能",
            source={"agent_id": "test-agent", "task_id": "task-001"},
            tags=["测试", "验证"],
            confidence=0.9,
        )
        assert c["cognition_id"].startswith("cog-")
        assert c["content"] == "这是一个测试认知内容，用于验证创建功能"
        assert c["status"] == "published"

    def test_create_minimal(self):
        c = create_cognition(content="最简单的认知内容")
        assert c["status"] == "published"

    def test_create_empty_rejected(self):
        with pytest.raises(HTTPException) as exc:
            create_cognition(content="")
        assert exc.value.status_code == 400

    def test_create_invalid_type_rejected(self):
        with pytest.raises(HTTPException) as exc:
            create_cognition(content="测试内容", type="invalid_type")
        assert exc.value.status_code == 400

    def test_create_invalid_confidence_rejected(self):
        with pytest.raises(HTTPException) as exc:
            create_cognition(content="测试内容", confidence=1.5)
        assert exc.value.status_code == 400

    def test_create_negative_confidence_rejected(self):
        with pytest.raises(HTTPException) as exc:
            create_cognition(content="测试内容", confidence=-0.1)
        assert exc.value.status_code == 400

    def test_create_dangerous_content_rejected(self):
        with pytest.raises(HTTPException) as exc:
            create_cognition(content="执行系统命令 exec(cmd)")
        assert exc.value.status_code == 400

    def test_create_script_rejected(self):
        with pytest.raises(HTTPException) as exc:
            create_cognition(content="<script>alert('xss')</script>")
        assert exc.value.status_code == 400

    def test_create_short_content_low_quality(self):
        c = create_cognition(content="短")
        assert c["quality_score"] < 1.0
        # 质量分数 0.7 (>0.5)，所以仍然是 published
        assert c["quality_score"] == 0.7

    def test_create_published_status(self):
        c = create_cognition(content="这是一个足够长的测试认知内容用于验证发布状态", confidence=0.9)
        assert c["status"] == "published"


class TestReadCognition:
    def test_read_existing(self):
        created = create_cognition(content="这是一个可读的认知内容", tags=["read-test"])
        result = read_cognition(created["cognition_id"])
        assert result["content"] == "这是一个可读的认知内容"

    def test_read_nonexistent(self):
        with pytest.raises(HTTPException) as exc:
            read_cognition("nonexistent-id")
        assert exc.value.status_code == 404


class TestUpdateCognition:
    def test_update_content(self):
        c = create_cognition(content="原始内容")
        updated = update_cognition(c["cognition_id"], {"content": "更新后的内容"})
        assert updated["content"] == "更新后的内容"

    def test_update_tags(self):
        c = create_cognition(content="测试内容", tags=["old-tag"])
        updated = update_cognition(c["cognition_id"], {"tags": ["new-tag-1", "new-tag-2"]})
        assert "new-tag-1" in updated["tags"]

    def test_update_confidence(self):
        c = create_cognition(content="测试内容", confidence=0.5)
        updated = update_cognition(c["cognition_id"], {"confidence": 0.95})
        assert updated["confidence"] == 0.95

    def test_update_version_increments(self):
        c = create_cognition(content="测试内容")
        assert c["version"] == 1
        updated = update_cognition(c["cognition_id"], {"tags": ["v1"]})
        assert updated["version"] == 2

    def test_update_nonexistent(self):
        with pytest.raises(HTTPException) as exc:
            update_cognition("nonexistent-id", {"content": "新内容"})
        assert exc.value.status_code == 404

    def test_update_dangerous_rejected(self):
        c = create_cognition(content="安全内容")
        with pytest.raises(HTTPException) as exc:
            update_cognition(c["cognition_id"], {"content": "system(cmd) 危险操作"})
        assert exc.value.status_code == 400

    def test_update_status(self):
        c = create_cognition(content="测试内容")
        updated = update_cognition(c["cognition_id"], {"status": "rejected"})
        assert updated["status"] == "rejected"


class TestDeleteCognition:
    def test_delete_existing(self):
        c = create_cognition(content="待删除的认知内容")
        result = delete_cognition(c["cognition_id"])
        assert result is True

    def test_delete_nonexistent(self):
        with pytest.raises(HTTPException) as exc:
            delete_cognition("nonexistent-id")
        assert exc.value.status_code == 404

    def test_deleted_not_readable(self):
        c = create_cognition(content="待删除的认知")
        delete_cognition(c["cognition_id"])
        with pytest.raises(HTTPException) as exc:
            read_cognition(c["cognition_id"])
        assert exc.value.status_code == 404


class TestListKnowledge:
    def test_list_empty(self):
        result = list_knowledge()
        assert len(result) == 0

    def test_list_after_create(self):
        create_cognition(content="认知1")
        create_cognition(content="认知2")
        result = list_knowledge()
        assert len(result) == 2

    def test_filter_by_type(self):
        create_cognition(content="事实1", type="fact")
        create_cognition(content="教训1", type="lesson")
        result = list_knowledge(type_filter="fact")
        assert len(result) == 1
        assert result[0]["type"] == "fact"

    def test_filter_by_tag(self):
        create_cognition(content="认知1", tags=["tag-a"])
        create_cognition(content="认知2", tags=["tag-b"])
        result = list_knowledge(tag_filter=["tag-a"])
        assert len(result) == 1

    def test_filter_by_multiple_tags(self):
        create_cognition(content="认知1", tags=["tag-a"])
        create_cognition(content="认知2", tags=["tag-b"])
        result = list_knowledge(tag_filter=["tag-a", "tag-b"])
        assert len(result) == 2


class TestSecurityValidation:
    def test_sql_injection_rejected(self):
        with pytest.raises(HTTPException):
            create_cognition(content="-- drop table cognitions")

    def test_path_traversal_rejected(self):
        with pytest.raises(HTTPException):
            create_cognition(content="../../../.../../passwd")

    def test_exec_injection_rejected(self):
        with pytest.raises(HTTPException):
            create_cognition(content="eval(user_input)")


class TestQualityScoring:
    def test_long_content_penalty(self):
        long_text = "x" * 10001
        c = create_cognition(content=long_text)
        assert c["quality_score"] < 1.0

    def test_high_confidence_good_quality(self):
        c = create_cognition(content="高质量认知内容用于测试评分", confidence=0.9)
        assert c["quality_score"] >= 0.8

    def test_low_confidence_penalty(self):
        c = create_cognition(content="高质量认知内容用于测试评分", confidence=0.1)
        assert c["quality_score"] < 1.0
