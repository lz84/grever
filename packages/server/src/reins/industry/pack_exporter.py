"""
PackExporter - Industry Pack Export Module

Exports industry packs as .nexus-pack (zip) or .json format.
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

from sqlalchemy import text
from sqlalchemy.orm import Session


# Supported export formats
SUPPORTED_FORMATS = {"nexus-pack", "json"}

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
    Exports an industry pack to .nexus-pack (zip) or .json format.

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
        format: str = "nexus-pack",
        include_assets: bool = True,
    ) -> bytes:
        """
        Export an industry pack.

        Args:
            pack_id: The pack ID to export.
            format: Export format - "nexus-pack" (zip) or "json".
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
        row = self.db.execute(
            text("SELECT * FROM industry_packs WHERE id = :id"),
            {"id": pack_id},
        ).fetchone()

        if row is None:
            return None

        # Build dict from column names
        columns = row.keys() if hasattr(row, "keys") else [
            "id", "name", "industry", "version", "description",
            "tags_count", "scenarios_count", "skills_count", "status",
            "created_at", "updated_at", "pack_type", "base_pack_id",
            "format_version", "author", "license",
            "compatibility_min_version", "compatibility_max_version",
            "source_checksum", "source_signature", "import_source",
            "import_source_file", "dependencies",
        ]
        meta = {}
        for i, col in enumerate(columns):
            val = row[i] if i < len(row) else None
            # Parse JSON fields
            if col == "dependencies" and isinstance(val, str):
                try:
                    val = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    val = []
            meta[col] = val

        return meta

    def _get_pack_contents(self, pack_id: str) -> list[dict]:
        """Fetch all content entries for a pack."""
        rows = self.db.execute(
            text(
                "SELECT pack_id, content_type, content_id "
                "FROM industry_pack_contents WHERE pack_id = :pack_id"
            ),
            {"pack_id": pack_id},
        ).fetchall()

        contents = []
        for row in rows:
            contents.append({
                "pack_id": row[0],
                "content_type": row[1],
                "content_id": row[2],
            })
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
        export_data = {
            "pack": pack_meta,
            "contents": contents,
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
    # Internal: Zip export (.nexus-pack)
    # ------------------------------------------------------------------

    def _export_zip(
        self, pack_meta: dict, contents: list[dict], include_assets: bool
    ) -> bytes:
        """
        Export as a .nexus-pack (zip) file containing:
        - manifest.json (with integrity hashes for all files)
        - checksum.json (SHA256 hashes)
        - contents.json (content associations)
        - pack_meta.json (full pack metadata)
        """
        buffer = BytesIO()

        # 1. Build all file contents first
        meta_bytes = json.dumps(pack_meta, ensure_ascii=False, indent=2).encode("utf-8")
        contents_bytes = json.dumps(contents, ensure_ascii=False, indent=2).encode("utf-8")

        # 2. File list
        file_entries = ["pack_meta.json", "contents.json", "manifest.json", "checksum.json"]

        # 3. Build initial manifest
        manifest = self._build_manifest(pack_meta, contents, file_entries)

        # 4. Compute hashes for content files
        file_hashes = {
            "pack_meta.json": self._sha256(meta_bytes),
            "contents.json": self._sha256(contents_bytes),
        }

        # 5. Serialize manifest with placeholder, then compute its hash
        #    (manifest can't contain its own hash, so we leave it as placeholder)
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        file_hashes["manifest.json"] = self._sha256(manifest_bytes)

        # 6. Update manifest with real hashes for pack_meta and contents
        for filepath in ["pack_meta.json", "contents.json", "manifest.json"]:
            if filepath in manifest.get("files", {}):
                manifest["files"][filepath]["integrity"] = f"sha256:{file_hashes[filepath]}"

        # Re-serialize updated manifest
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        file_hashes["manifest.json"] = self._sha256(manifest_bytes)

        # 7. Build checksum.json (excludes manifest.json and checksum.json to avoid circular dependency)
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

        # 8. Update manifest with checksum.json hash
        if "checksum.json" in manifest.get("files", {}):
            manifest["files"]["checksum.json"]["integrity"] = f"sha256:{self._sha256(checksum_bytes)}"

        # Final manifest write (don't recompute manifest hash - it's the final version)
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

        # 9. Write all to zip
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("pack_meta.json", meta_bytes)
            zf.writestr("contents.json", contents_bytes)
            zf.writestr("manifest.json", manifest_bytes)
            zf.writestr("checksum.json", checksum_bytes)

        buffer.seek(0)
        return buffer.getvalue()
