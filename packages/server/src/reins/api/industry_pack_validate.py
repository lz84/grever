"""Industry Pack Validate API

Sprint 113: 包完整性校验
"""
import json
import os
import hashlib
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models import IndustryPack
from reins.common.database import get_db

router = APIRouter(prefix="/api/v1/industry-packs", tags=["industry-pack-validate"])

# Resolve DB file path from the same logic as server.py
def _get_db_path() -> str:
    """Get the database file path."""
    db_path = os.environ.get("SQLITE_PATH")
    if db_path:
        return db_path
    # Default: project root data/reins.db
    # This file is at: packages/server/src/reins/api/industry_pack_validate.py
    # DB is at: {project_root}/data/reins.db
    current = Path(__file__).resolve()
    # Walk up: api -> reins -> src -> server -> packages -> project_root
    project_root = current.parent.parent.parent.parent.parent.parent
    return str(project_root / "data" / "reins.db")

@router.post("/{pack_id}/validate")
async def validate_pack(
    pack_id: str,
    body: Optional[dict] = {},
    db: Session = Depends(get_db),
):
    """校验包完整性。

    校验项:
    1. manifest 存在且有效 JSON（检查 import_source_file）
    2. checksum 校验通过（对比 source_checksum）
    3. 内容完整性（industry_pack_contents 中存在内容）
    4. 依赖包存在性（dependencies 中引用的包都存在）
    5. 兼容性检查（格式版本兼容性）

    返回: {valid: bool, checks: [...], issues: [...]}
    """
    # Verify pack exists - converted to ORM
    pack = db.query(IndustryPack).filter(IndustryPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    # Access pack fields directly from ORM model
    p_id = pack.id
    p_name = pack.name
    p_industry = pack.industry
    p_version = pack.version
    p_description = pack.description
    p_status = pack.status
    p_pack_type = pack.pack_type or 'standard'
    p_base_pack_id = pack.base_pack_id
    p_format_version = pack.format_version or '1.0'
    p_checksum = pack.source_checksum
    p_source_file = pack.import_source_file
    p_dependencies = pack.dependencies or '[]'

    checks = []
    issues = []
    all_valid = True

    # ── Check 1: manifest 存在且有效 JSON ──
    check_manifest = {
        "name": "manifest_valid",
        "description": "检查 manifest 文件存在且为有效 JSON",
        "passed": True,
        "detail": "",
    }

    if p_source_file:
        manifest_path = Path(p_source_file)
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                check_manifest["detail"] = f"Manifest found: {manifest_path}, keys: {list(manifest_data.keys()) if isinstance(manifest_data, dict) else 'array'}"
            except json.JSONDecodeError as e:
                check_manifest["passed"] = False
                check_manifest["detail"] = f"Invalid JSON in manifest: {str(e)}"
                issues.append({"check": "manifest_valid", "severity": "error", "message": f"Manifest JSON 解析失败: {str(e)}"})
                all_valid = False
        else:
            check_manifest["passed"] = False
            check_manifest["detail"] = f"Manifest file not found: {p_source_file}"
            issues.append({"check": "manifest_valid", "severity": "warning", "message": f"Manifest 文件不存在: {p_source_file}"})
    else:
        check_manifest["passed"] = True
        check_manifest["detail"] = "No manifest file specified (import_source='created'), skipping file check"

    checks.append(check_manifest)

    # ── Check 2: checksum 校验 ──
    check_checksum = {
        "name": "checksum_valid",
        "description": "校验 source_checksum 与文件实际 checksum 是否匹配",
        "passed": True,
        "detail": "",
    }

    if p_checksum and p_source_file:
        manifest_path = Path(p_source_file)
        if manifest_path.exists():
            try:
                with open(manifest_path, 'rb') as f:
                    actual_checksum = hashlib.sha256(f.read()).hexdigest()
                if actual_checksum == p_checksum:
                    check_checksum["detail"] = f"Checksum matches: {p_checksum[:16]}..."
                else:
                    check_checksum["passed"] = False
                    check_checksum["detail"] = f"Checksum mismatch: expected {p_checksum[:16]}..., got {actual_checksum[:16]}..."
                    issues.append({"check": "checksum_valid", "severity": "error", "message": "Checksum 校验失败"})
                    all_valid = False
            except Exception as e:
                check_checksum["passed"] = False
                check_checksum["detail"] = f"Error computing checksum: {str(e)}"
                issues.append({"check": "checksum_valid", "severity": "error", "message": f"Checksum 计算出错: {str(e)}"})
                all_valid = False
        else:
            check_checksum["passed"] = False
            check_checksum["detail"] = "Cannot verify checksum: manifest file not found"
            issues.append({"check": "checksum_valid", "severity": "warning", "message": "无法校验 checksum：源文件不存在"})
    elif p_checksum:
        check_checksum["passed"] = False
        check_checksum["detail"] = "Checksum exists but no source file specified"
        issues.append({"check": "checksum_valid", "severity": "warning", "message": "有 checksum 但未指定源文件"})
    else:
        check_checksum["passed"] = True
        check_checksum["detail"] = "No checksum set (pack created directly, not imported from file)"

    checks.append(check_checksum)

    # ── Check 3: 内容完整性 ──
    check_contents = {
        "name": "contents_integrity",
        "description": "检查包内容是否存在",
        "passed": True,
        "detail": "",
    }

    from models import Skill, KnowledgeEntry, AgentScheme
    skill_count = db.query(Skill).filter(Skill.pack_id == pack_id).count()
    knowledge_count = db.query(KnowledgeEntry).filter(KnowledgeEntry.pack_id == pack_id).count()
    agent_count = db.query(AgentScheme).filter(AgentScheme.pack_id == pack_id).count()
    total_active = skill_count + knowledge_count + agent_count

    if total_active > 0:
        check_contents["detail"] = f"Active contents: {total_active} (skills: {skill_count}, knowledge: {knowledge_count}, agent_schemes: {agent_count})"
    else:
        check_contents["passed"] = False
        check_contents["detail"] = "No active contents found in the pack"
        issues.append({"check": "contents_integrity", "severity": "warning", "message": "包中没有活跃内容"})

    checks.append(check_contents)

    # ── Check 4: 依赖包存在性 ──
    check_deps = {
        "name": "dependencies_valid",
        "description": "检查依赖包是否存在",
        "passed": True,
        "detail": "",
    }

    try:
        deps = json.loads(p_dependencies) if p_dependencies else []
    except (json.JSONDecodeError, TypeError):
        deps = []

    if deps:
        missing_deps = []
        for dep_id in deps:
            dep_exists = db.query(IndustryPack.id, IndustryPack.name, IndustryPack.version).filter(
                IndustryPack.id == dep_id
            ).first()
            if dep_exists:
                pass  # dependency exists
            else:
                missing_deps.append(dep_id)

        if missing_deps:
            check_deps["passed"] = False
            check_deps["detail"] = f"Missing dependencies: {', '.join(missing_deps)}"
            issues.append({"check": "dependencies_valid", "severity": "error", "message": f"缺少依赖包: {', '.join(missing_deps)}"})
            all_valid = False
        else:
            check_deps["detail"] = f"All {len(deps)} dependencies resolved"
    else:
        check_deps["detail"] = "No dependencies declared"

    checks.append(check_deps)

    # ── Check 5: 兼容性检查 ──
    check_compat = {
        "name": "compatibility",
        "description": "检查包的兼容性（格式版本、依赖版本范围）",
        "passed": True,
        "detail": "",
    }

    format_ver = p_format_version or '1.0'
    compat_issues = []

    # Check format version is parseable
    try:
        parts = format_ver.split('.')
        if len(parts) < 2:
            raise ValueError("Invalid format")
        int(parts[0])
        int(parts[1])
    except (ValueError, AttributeError):
        compat_issues.append(f"Invalid format_version: {format_ver}")

    # If custom pack, check base pack compatibility
    if p_pack_type == 'custom' and p_base_pack_id:
        base_pack = db.query(IndustryPack.id, IndustryPack.name, IndustryPack.version, IndustryPack.format_version).filter(
            IndustryPack.id == p_base_pack_id
        ).first()
        if not base_pack:
            compat_issues.append(f"Base pack '{p_base_pack_id}' not found")
            check_compat["passed"] = False
        else:
            base_format = base_pack[3] if len(base_pack) > 3 else '1.0'
            if format_ver != base_format:
                compat_issues.append(f"Format version mismatch with base pack: {format_ver} vs {base_format}")

    if compat_issues:
        check_compat["passed"] = False
        check_compat["detail"] = "; ".join(compat_issues)
        for issue_msg in compat_issues:
            issues.append({"check": "compatibility", "severity": "error", "message": issue_msg})
        all_valid = False
    else:
        check_compat["detail"] = f"Compatible (format_version: {format_ver})"

    checks.append(check_compat)

    # ── Check 6: 基本元数据检查 ──
    check_meta = {
        "name": "metadata_valid",
        "description": "检查包的基本元数据是否完整",
        "passed": True,
        "detail": "",
    }

    meta_issues = []
    if not p_name:
        meta_issues.append("Missing name")
    if not p_industry:
        meta_issues.append("Missing industry")
    if not p_version:
        meta_issues.append("Missing version")

    if meta_issues:
        check_meta["passed"] = False
        check_meta["detail"] = f"Incomplete metadata: {', '.join(meta_issues)}"
        for mi in meta_issues:
            issues.append({"check": "metadata_valid", "severity": "warning", "message": mi})
    else:
        check_meta["detail"] = f"Name: {p_name}, Industry: {p_industry}, Version: {p_version}"

    checks.append(check_meta)

    return {
        "pack_id": pack_id,
        "valid": all_valid,
        "checks": checks,
        "issues": issues,
        "summary": {
            "total_checks": len(checks),
            "passed_checks": sum(1 for c in checks if c["passed"]),
            "failed_checks": sum(1 for c in checks if not c["passed"]),
            "issues_count": len(issues),
        },
    }
