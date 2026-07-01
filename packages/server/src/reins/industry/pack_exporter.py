"""
PackExporter - Industry Pack Export Module

Exports industry packs as .grever-pack (zip) or .json format.
Includes manifest.json with integrity hashes, checksum.json with SHA256,
and all pack contents.

Sprint 109: B109-1
"""

import hashlib
import json
import time
import zipfile
from io import BytesIO
from typing import Optional

from models import IndustryPack
from sqlalchemy.orm import Session


# Supported export formats
SUPPORTED_FORMATS = {"grever-pack", "json"}

# Manifest schema version
MANIFEST_VERSION = "1.0"


class PackNotFoundError(Exception):
    """Raised when the requested pack does not exist."""
    pass


class UnsupportedFormatError(Exception):
    """Raised when the requested format is not supported."""
    pass


class PackExporter:
    """
    Exports an industry pack to .grever-pack (zip) or .json format.

    Usage:
        exporter = PackExporter(db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1")
        # data is bytes of the zip file

        data = exporter.export_pack("pack-id", format="json")
        # data is bytes of JSON string
    """

    def __init__(self, db: Session):
        self.db = db

    def export_pack(
        self,
        pack_id: str,
        format: str = "grever-pack",
        include_assets: bool = True,
    ) -> bytes:
        """
        Export an industry pack.

        Args:
            pack_id: The pack ID to export.
            format: Export format - "grever-pack" (zip) or "json".
            include_assets: Whether to include actual content data in the export.

        Returns:
            bytes: The exported pack data.

        Raises:
            PackNotFoundError: If the pack doesn't exist.
            UnsupportedFormatError: If the format is not supported.
        """
        if format not in SUPPORTED_FORMATS:
            raise UnsupportedFormatError(
                f"Unsupported format '{format}'. Supported: {SUPPORTED_FORMATS}"
            )

        pack_meta = self._get_pack_metadata(pack_id)
        if pack_meta is None:
            raise PackNotFoundError(f"Pack '{pack_id}' not found")

        contents = self._get_pack_contents(pack_id)

        if format == "json":
            return self._export_json(pack_meta, contents, include_assets)
        else:
            return self._export_zip(pack_meta, contents, include_assets)

    # ------------------------------------------------------------------
    # Internal: DB queries
    # ------------------------------------------------------------------

    def _get_pack_metadata(self, pack_id: str) -> Optional[dict]:
        """Fetch pack metadata from industry_packs table."""
        pack = self.db.query(IndustryPack).filter(IndustryPack.id == pack_id).first()

        if pack is None:
            return None

        meta = {
            "id": pack.id,
            "name": pack.name,
            "industry": pack.industry,
            "version": pack.version,
            "description": pack.description or "",
            "tags_count": pack.tags_count or 0,
            "scenarios_count": pack.scenarios_count or 0,
            "skills_count": pack.skills_count or 0,
            "status": pack.status,
            "created_at": pack.created_at,
            "updated_at": pack.updated_at,
            "pack_type": pack.pack_type or "standard",
            "base_pack_id": pack.base_pack_id,
            "format_version": getattr(pack, "format_version", "1.0") or "1.0",
            "author": getattr(pack, "author", "") or "",
            "license": getattr(pack, "license", "proprietary") or "proprietary",
            "compatibility_min_version": getattr(pack, "compatibility_min_version", None),
            "compatibility_max_version": getattr(pack, "compatibility_max_version", None),
            "source_checksum": getattr(pack, "source_checksum", None),
            "source_signature": getattr(pack, "source_signature", None),
            "import_source": getattr(pack, "import_source", None),
            "import_source_file": getattr(pack, "import_source_file", None),
            "dependencies": self._parse_json_field(getattr(pack, "dependencies", None)),
        }

        return meta

    @staticmethod
    def _parse_json_field(val):
        """Parse a JSON string field, returning empty list on failure."""
        if val is None:
            return []
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return []
        return val

    def _get_pack_contents(self, pack_id: str) -> list[dict]:
        """Fetch all content entries for a pack by querying business tables directly."""
        from models import Skill, KnowledgeEntry, AgentScheme
        
        contents = []
        
        # Skills
        skills = self.db.query(Skill.id, Skill.pack_id).filter(Skill.pack_id == pack_id).all()
        for sid, _ in skills:
            contents.append({"pack_id": pack_id, "content_type": "skill", "content_id": sid})
            
        # Knowledge
        knowledge = self.db.query(KnowledgeEntry.id, KnowledgeEntry.pack_id).filter(KnowledgeEntry.pack_id == pack_id).all()
        for kid, _ in knowledge:
            contents.append({"pack_id": pack_id, "content_type": "knowledge", "content_id": kid})
            
        # Agent Schemes
        agents = self.db.query(AgentScheme.id, AgentScheme.pack_id).filter(AgentScheme.pack_id == pack_id).all()
        for aid, _ in agents:
            contents.append({"pack_id": pack_id, "content_type": "agent_scheme", "content_id": aid})
            
        return contents

    # ------------------------------------------------------------------
    # Internal: manifest & checksum generation
    # ------------------------------------------------------------------

    def _build_manifest(self, pack_meta: dict, contents: list[dict], file_entries: list[str]) -> dict:
        """Build manifest.json with integrity hashes for all files."""
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "pack_id": pack_meta["id"],
            "pack_name": pack_meta["name"],
            "industry": pack_meta["industry"],
            "version": pack_meta["version"],
            "pack_type": pack_meta.get("pack_type", "standard"),
            "exported_at": now_iso,
            "format_version": pack_meta.get("format_version", "1.0"),
            "description": pack_meta.get("description", ""),
            "author": pack_meta.get("author", ""),
            "license": pack_meta.get("license", "proprietary"),
            "contents": contents,
            "files": {},
        }

        # Add integrity hash for each file in the export
        for filepath in sorted(file_entries):
            manifest["files"][filepath] = {
                "integrity": f"sha256:<computed>",
            }

        return manifest

    @staticmethod
    def _sha256(data: bytes) -> str:
        """Compute SHA256 hex digest of bytes."""
        return hashlib.sha256(data).hexdigest()

    # ------------------------------------------------------------------
    # Internal: JSON export
    # ------------------------------------------------------------------

    def _export_json(
        self, pack_meta: dict, contents: list[dict], include_assets: bool
    ) -> bytes:
        """Export as a single JSON document."""
        knowledge_entries = self._get_knowledge_entries(pack_meta["id"])
        agent_schemes = self._get_agent_schemes(pack_meta["id"])
        skills = self._get_skills(pack_meta["id"])
        export_data = {
            "pack": pack_meta,
            "contents": contents,
            "knowledge": knowledge_entries,
            "agent_schemes": agent_schemes,
            "skills": skills,
            "export_format": "json",
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        raw = json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")
        checksum = self._sha256(raw)

        export_data["checksum"] = {
            "algorithm": "SHA256",
            "value": checksum,
        }

        return json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")

    # ------------------------------------------------------------------
    # Internal: Zip export (.grever-pack)
    # ------------------------------------------------------------------

    def _export_zip(
        self, pack_meta: dict, contents: list[dict], include_assets: bool
    ) -> bytes:
        """
        Export as a .grever-pack (zip) file containing:
        - manifest.json (with integrity hashes for all files)
        - checksum.json (SHA256 hashes)
        - contents.json (content associations)
        - pack_meta.json (full pack metadata)
        - knowledge.json (knowledge entries, Sprint 75 Phase 2)
        - agent_schemes.json (Agent方案, Sprint 75 Phase 3)
        - skills.json (skills, Sprint 116)
        """
        buffer = BytesIO()

        # 1. Build all file contents first
        meta_bytes = json.dumps(pack_meta, ensure_ascii=False, indent=2).encode("utf-8")
        contents_bytes = json.dumps(contents, ensure_ascii=False, indent=2).encode("utf-8")

        # 2. Fetch knowledge entries for this pack (Sprint 75 Phase 2)
        knowledge_entries = self._get_knowledge_entries(pack_meta["id"])
        knowledge_bytes = json.dumps(knowledge_entries, ensure_ascii=False, indent=2).encode("utf-8")

        # 3. Fetch agent schemes for this pack (Sprint 75 Phase 3)
        agent_schemes = self._get_agent_schemes(pack_meta["id"])
        agent_schemes_bytes = json.dumps(agent_schemes, ensure_ascii=False, indent=2).encode("utf-8")

        # 3b. Fetch skills for this pack
        skills = self._get_skills(pack_meta["id"])
        skills_bytes = json.dumps(skills, ensure_ascii=False, indent=2).encode("utf-8")

        # 4. File list
        file_entries = [
            "pack_meta.json", "contents.json", "knowledge.json", "agent_schemes.json",
            "skills.json",
            "manifest.json", "checksum.json",
        ]

        # 4. Build initial manifest
        manifest = self._build_manifest(pack_meta, contents, file_entries)

        # 5. Compute hashes for content files
        file_hashes = {
            "pack_meta.json": self._sha256(meta_bytes),
            "contents.json": self._sha256(contents_bytes),
            "knowledge.json": self._sha256(knowledge_bytes),
            "agent_schemes.json": self._sha256(agent_schemes_bytes),
            "skills.json": self._sha256(skills_bytes),
        }

        # 6. Serialize manifest with placeholder, then compute its hash
        #    (manifest can't contain its own hash, so we leave it as placeholder)
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        file_hashes["manifest.json"] = self._sha256(manifest_bytes)

        # 7. Update manifest with real hashes for pack_meta, contents, knowledge, agent_schemes, skills
        for filepath in ["pack_meta.json", "contents.json", "knowledge.json", "agent_schemes.json", "skills.json", "manifest.json"]:
            if filepath in manifest.get("files", {}):
                manifest["files"][filepath]["integrity"] = f"sha256:{file_hashes[filepath]}"

        # Re-serialize updated manifest
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        file_hashes["manifest.json"] = self._sha256(manifest_bytes)

        # 8. Build checksum.json (excludes manifest.json and checksum.json to avoid circular dependency)
        checksum_content_hashes = {
            name: f"sha256:{h}" for name, h in sorted(file_hashes.items())
            if name not in ("manifest.json", "checksum.json")
        }
        checksum_data = {
            "algorithm": "SHA256",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "files": checksum_content_hashes,
            "pack_id": pack_meta["id"],
        }
        checksum_bytes = json.dumps(checksum_data, ensure_ascii=False, indent=2).encode("utf-8")

        # 9. Update manifest with checksum.json hash
        if "checksum.json" in manifest.get("files", {}):
            manifest["files"]["checksum.json"]["integrity"] = f"sha256:{self._sha256(checksum_bytes)}"

        # Final manifest write (don't recompute manifest hash - it's the final version)
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

        # 10. Write all to zip
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("pack_meta.json", meta_bytes)
            zf.writestr("contents.json", contents_bytes)
            zf.writestr("knowledge.json", knowledge_bytes)
            zf.writestr("agent_schemes.json", agent_schemes_bytes)
            zf.writestr("skills.json", skills_bytes)
            zf.writestr("manifest.json", manifest_bytes)
            zf.writestr("checksum.json", checksum_bytes)

        buffer.seek(0)
        return buffer.getvalue()

    def _get_knowledge_entries(self, pack_id: str) -> list[dict]:
        """Fetch knowledge entries for a pack, serializing JSON fields."""
        from models import KnowledgeEntry
        rows = self.db.query(KnowledgeEntry).filter(
            KnowledgeEntry.pack_id == pack_id
        ).all()
        result = []
        for row in rows:
            tags = row.tags
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except (json.JSONDecodeError, TypeError):
                    tags = []
            result.append({
                "id": row.id,
                "pack_id": row.pack_id,
                "name": row.name,
                "category": row.category,
                "content": row.content,
                "file_path": row.file_path,
                "version": row.version,
                "tags": tags or [],
                "created_at": row.created_at,
            })
        return result

    def _get_agent_schemes(self, pack_id: str) -> list[dict]:
        """Fetch agent schemes and their roles for a pack."""
        from models import AgentScheme, AgentSchemeRole

        schemes = self.db.query(AgentScheme).filter(
            AgentScheme.pack_id == pack_id
        ).all()

        result = []
        for scheme in schemes:
            roles = self.db.query(AgentSchemeRole).filter(
                AgentSchemeRole.scheme_id == scheme.id
            ).order_by(AgentSchemeRole.priority.desc()).all()

            scheme_roles = []
            for role in roles:
                tags = role.required_tags
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except (json.JSONDecodeError, TypeError):
                        tags = []
                scheme_roles.append({
                    "id": role.id,
                    "scheme_id": role.scheme_id,
                    "role_name": role.role_name,
                    "required_tags": tags or [],
                    "priority": role.priority,
                })

            result.append({
                "id": scheme.id,
                "pack_id": scheme.pack_id,
                "name": scheme.name,
                "description": scheme.description,
                "roles": scheme_roles,
                "created_at": scheme.created_at,
            })
        return result

    def _get_skills(self, pack_id: str) -> list[dict]:
        """Fetch skills for a pack, serializing JSON fields."""
        from models import Skill
        rows = self.db.query(Skill).filter(
            Skill.pack_id == pack_id
        ).order_by(Skill.name).all()
        result = []
        for row in rows:
            input_schema = row.input_schema
            if isinstance(input_schema, str):
                try:
                    input_schema = json.loads(input_schema)
                except (json.JSONDecodeError, TypeError):
                    input_schema = {}
            output_schema = row.output_schema
            if isinstance(output_schema, str):
                try:
                    output_schema = json.loads(output_schema)
                except (json.JSONDecodeError, TypeError):
                    output_schema = {}
            required_tags = row.required_tags
            if isinstance(required_tags, str):
                try:
                    required_tags = json.loads(required_tags)
                except (json.JSONDecodeError, TypeError):
                    required_tags = []
            result.append({
                "id": row.id,
                "pack_id": row.pack_id,
                "name": row.name,
                "description": row.description,
                "input_schema": input_schema,
                "output_schema": output_schema,
                "required_tags": required_tags,
                "tool_dependency": row.tool_dependency,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            })
        return result
