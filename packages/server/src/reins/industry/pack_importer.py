"""
PackImporter - Industry Pack Import Module

Imports industry packs from .grever-pack (zip) files.
Validates structure, checksums, compatibility, and dependencies before transactional DB write.

Sprint 110: B110-1
"""

import hashlib
import json
import time
import uuid
import zipfile
from io import BytesIO
from typing import Optional

from sqlalchemy import Table, MetaData
from sqlalchemy.orm import Session
from models.industry_tag import IndustryPack, IndustryPackVersion


# Constants
MAX_UNCOMPRESSED_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_SINGLE_FILE_SIZE = 10 * 1024 * 1024   # 10 MB per file
MANIFEST_VERSION = "1.0"
REQUIRED_FILES = {"manifest.json", "checksum.json"}


class PackImportError(Exception):
    """Base exception for pack import errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class InvalidPackError(PackImportError):
    """Raised when the pack structure is invalid."""
    pass


class ChecksumMismatchError(PackImportError):
    """Raised when checksum verification fails."""
    pass


class DependencyMissingError(PackImportError):
    """Raised when a required dependency pack is missing."""
    pass


class PackExistsError(PackImportError):
    """Raised when a pack already exists and strategy is 'create'."""
    def __init__(self, pack_id: str):
        super().__init__(
            f"Pack '{pack_id}' already exists. Use strategy='upsert' or 'force' to update.",
            status_code=409,
        )
        self.pack_id = pack_id


class SecurityError(PackImportError):
    """Raised when a security violation is detected."""
    pass


class IncompatibleFormatError(PackImportError):
    """Raised when the pack format version is incompatible."""
    pass


def _sha256(data: bytes) -> str:
    """Compute SHA256 hex digest."""
    return hashlib.sha256(data).hexdigest()


def _check_path_traversal(filename: str) -> None:
    """Raise SecurityError if filename contains path traversal patterns."""
    # Normalize and check
    normalized = filename.replace("\\", "/")
    if ".." in normalized or normalized.startswith("/") or ":" in normalized:
        raise SecurityError(f"Path traversal detected in filename: {filename}")


class PackImporter:
    """
    Imports industry packs from .grever-pack (zip) files.

    Usage:
        importer = PackImporter(db_session)
        result = importer.import_pack(file_bytes, strategy="create")
    """

    def __init__(self, db: Session):
        self.db = db

    def import_pack(self, file_bytes: bytes, strategy: str = "create") -> dict:
        """
        Import an industry pack from zip file bytes.

        Args:
            file_bytes: Raw bytes of the .grever-pack zip file.
            strategy: Import strategy - "create" (fail if exists),
                     "upsert" (update if exists), "force" (overwrite).

        Returns:
            dict with import result:
            {
                "success": True,
                "pack_id": "...",
                "pack_name": "...",
                "strategy": "...",
                "contents_count": N,
                "action": "created" | "updated" | "forced",
            }

        Raises:
            PackImportError subclasses on validation failures.
        """
        # Validate strategy
        if strategy not in ("create", "upsert", "force"):
            raise PackImportError(
                f"Invalid strategy '{strategy}'. Must be 'create', 'upsert', or 'force'.",
            )

        # Step 1: Extract and validate zip structure
        files = self._extract_and_validate(file_bytes)

        # Step 2: Validate manifest
        manifest = self._validate_manifest(files)

        # Step 3: Validate checksums
        self._validate_checksums(files)

        # Step 4: Validate format compatibility
        self._validate_compatibility(manifest)

        # Step 5: Check dependencies
        self._check_dependencies(manifest)

        # Step 6: Check import strategy
        pack_id = manifest["pack_id"]
        existing = self._get_existing_pack(pack_id)
        action = self._check_strategy(strategy, existing, pack_id)

        # Step 7: Transactional write
        result = self._write_to_db(manifest, files, action)

        return result

    # ------------------------------------------------------------------
    # Step 1: Extract and validate zip
    # ------------------------------------------------------------------

    def _extract_and_validate(self, file_bytes: bytes) -> dict[str, bytes]:
        """
        Extract zip contents with security checks.

        Returns dict of filename -> bytes for all files in the zip.
        """
        files: dict[str, bytes] = {}
        total_size = 0

        try:
            zf = zipfile.ZipFile(BytesIO(file_bytes))
        except zipfile.BadZipFile:
            raise InvalidPackError("Invalid zip file: not a valid .grever-pack archive")

        # Check for zip bomb: number of files
        if len(zf.namelist()) > 1000:
            raise SecurityError(
                f"Too many files in archive ({len(zf.namelist())}). Possible zip bomb."
            )

        for info in zf.infolist():
            filename = info.filename

            # Skip directories
            if filename.endswith("/"):
                continue

            # Path traversal check
            _check_path_traversal(filename)

            # Single file size check
            if info.file_size > MAX_SINGLE_FILE_SIZE:
                raise SecurityError(
                    f"File '{filename}' too large ({info.file_size} bytes). "
                    f"Max: {MAX_SINGLE_FILE_SIZE} bytes."
                )

            # Cumulative size check (zip bomb)
            total_size += info.file_size
            if total_size > MAX_UNCOMPRESSED_SIZE:
                raise SecurityError(
                    f"Total uncompressed size ({total_size} bytes) exceeds "
                    f"limit ({MAX_UNCOMPRESSED_SIZE} bytes). Possible zip bomb."
                )

            # Read file content
            files[filename] = zf.read(filename)

        zf.close()

        # Verify required files
        missing = REQUIRED_FILES - set(files.keys())
        if missing:
            raise InvalidPackError(
                f"Missing required files in pack: {', '.join(sorted(missing))}"
            )

        return files

    # ------------------------------------------------------------------
    # Step 2: Validate manifest
    # ------------------------------------------------------------------

    def _validate_manifest(self, files: dict[str, bytes]) -> dict:
        """Parse and validate manifest.json."""
        try:
            manifest = json.loads(files["manifest.json"])
        except json.JSONDecodeError as e:
            raise InvalidPackError(f"Invalid manifest.json: {e}")

        # Required fields
        required_fields = ["pack_id", "pack_name", "industry", "version", "format_version"]
        missing = [f for f in required_fields if f not in manifest or manifest[f] is None]
        if missing:
            raise InvalidPackError(f"Manifest missing required fields: {', '.join(missing)}")

        return manifest

    # ------------------------------------------------------------------
    # Step 3: Validate checksums
    # ------------------------------------------------------------------

    def _validate_checksums(self, files: dict[str, bytes]) -> None:
        """Validate SHA256 checksums of all files against checksum.json.

        Note: checksum.json may not include its own hash or manifest.json's hash
        (circular dependency). We only validate files that are both in checksum.json
        AND in the pack.
        """
        try:
            checksum_data = json.loads(files["checksum.json"])
        except json.JSONDecodeError as e:
            raise InvalidPackError(f"Invalid checksum.json: {e}")

        if checksum_data.get("algorithm") != "SHA256":
            raise InvalidPackError(
                f"Unsupported checksum algorithm: {checksum_data.get('algorithm')}"
            )

        file_hashes = checksum_data.get("files", {})

        # Must have at least one file hash
        if not file_hashes:
            raise InvalidPackError("checksum.json contains no file hashes")

        for filename, expected_hash_str in file_hashes.items():
            # Skip self-reference
            if filename == "checksum.json":
                continue

            # Parse "sha256:hexdigest" format
            if ":" in expected_hash_str:
                _, expected_hash = expected_hash_str.split(":", 1)
            else:
                expected_hash = expected_hash_str

            if filename not in files:
                raise ChecksumMismatchError(
                    f"File '{filename}' referenced in checksum.json but not found in pack"
                )

            actual_hash = _sha256(files[filename])
            if actual_hash != expected_hash:
                raise ChecksumMismatchError(
                    f"Checksum mismatch for '{filename}': "
                    f"expected {expected_hash[:16]}..., got {actual_hash[:16]}..."
                )

    # ------------------------------------------------------------------
    # Step 4: Validate compatibility
    # ------------------------------------------------------------------

    def _validate_compatibility(self, manifest: dict) -> None:
        """Check format_version compatibility."""
        fmt_version = manifest.get("format_version", "1.0")

        # Parse version tuple
        try:
            parts = fmt_version.split(".")
            major = int(parts[0])
        except (ValueError, IndexError):
            raise IncompatibleFormatError(
                f"Invalid format_version: {fmt_version}"
            )

        # Currently we support format_version 1.x
        if major != 1:
            raise IncompatibleFormatError(
                f"Incompatible format version: {fmt_version}. "
                f"Only version 1.x is supported."
            )

    # ------------------------------------------------------------------
    # Step 5: Check dependencies
    # ------------------------------------------------------------------

    def _check_dependencies(self, manifest: dict) -> None:
        """Verify that all dependency packs exist in the database."""
        dependencies = manifest.get("dependencies", [])
        if not dependencies:
            return

        for dep_id in dependencies:
            row = self.db.query(IndustryPack).filter(IndustryPack.id == dep_id).first()

            if not row:
                raise DependencyMissingError(
                    f"Missing dependency pack: '{dep_id}'. "
                    f"Please import it first."
                )

    # ------------------------------------------------------------------
    # Step 6: Check import strategy
    # ------------------------------------------------------------------

    def _get_existing_pack(self, pack_id: str) -> Optional[dict]:
        """Get existing pack info if it exists."""
        pack = self.db.query(IndustryPack).filter(IndustryPack.id == pack_id).first()

        if not pack:
            return None

        return pack.to_dict()

    def _check_strategy(self, strategy: str, existing: Optional[dict], pack_id: str) -> str:
        """
        Validate strategy against existing pack state.

        Returns the action to take: "created", "updated", or "forced".
        """
        if existing is None:
            return "created"

        if strategy == "create":
            raise PackExistsError(pack_id)
        elif strategy == "upsert":
            return "updated"
        elif strategy == "force":
            return "forced"

        return "created"

    # ------------------------------------------------------------------
    # Step 7: Transactional DB write
    # ------------------------------------------------------------------

    def _write_to_db(self, manifest: dict, files: dict[str, bytes], action: str) -> dict:
        """
        Write pack data to database in a transaction.

        Tables:
        - industry_packs
        - industry_pack_versions
        - industry_pack_contents
        """
        pack_id = manifest["pack_id"]
        now = int(time.time())

        try:
            if action == "created":
                # Insert new pack
                deps_json = json.dumps(manifest.get("dependencies", []), ensure_ascii=False)
                pack = IndustryPack(
                    id=pack_id,
                    name=manifest.get("pack_name", ""),
                    industry=manifest.get("industry", ""),
                    version=manifest.get("version", "1.0.0"),
                    description=manifest.get("description", ""),
                    tags_count=0,
                    scenarios_count=0,
                    skills_count=0,
                    status="active",
                    created_at=now,
                    updated_at=now,
                    pack_type=manifest.get("pack_type", "standard"),
                    base_pack_id=manifest.get("base_pack_id"),
                    format_version=manifest.get("format_version", "1.0"),
                    author=manifest.get("author"),
                    license=manifest.get("license", "proprietary"),
                    compatibility_min_version=None,
                    compatibility_max_version=None,
                    source_checksum=_sha256(files.get("checksum.json", b"")),
                    source_signature=None,
                    import_source="imported",
                    import_source_file=None,
                    dependencies=deps_json,
                )
                self.db.add(pack)
            else:
                # Update existing pack (upsert/force)
                deps_json = json.dumps(manifest.get("dependencies", []), ensure_ascii=False)
                self.db.query(IndustryPack).filter(IndustryPack.id == pack_id).update({
                    'name': manifest.get("pack_name", ""),
                    'industry': manifest.get("industry", ""),
                    'version': manifest.get("version", "1.0.0"),
                    'description': manifest.get("description", ""),
                    'status': "active",
                    'updated_at': now,
                    'pack_type': manifest.get("pack_type", "standard"),
                    'base_pack_id': manifest.get("base_pack_id"),
                    'format_version': manifest.get("format_version", "1.0"),
                    'author': manifest.get("author"),
                    'license': manifest.get("license", "proprietary"),
                    'source_checksum': _sha256(files.get("checksum.json", b"")),
                    'import_source': 'imported',
                    'dependencies': deps_json,
                }, synchronize_session=False)

            # Insert version record
            contents = manifest.get("contents", [])
            stats = {
                "tags": len([c for c in contents if c.get("content_type") == "tag"]),
                "scenarios": len([c for c in contents if c.get("content_type") == "scenario"]),
                "skills": len([c for c in contents if c.get("content_type") == "skill"]),
            }
            version_id = f"{pack_id}-v{manifest.get('version', '1.0.0')}-{now}-{uuid.uuid4().hex[:8]}"
            version = IndustryPackVersion(
                id=version_id,
                pack_id=pack_id,
                version=manifest.get("version", "1.0.0"),
                action=action,
                source_file=None,
                source_checksum=_sha256(files.get("checksum.json", b"")),
                stats=json.dumps(stats, ensure_ascii=False),
                imported_at=now,
                notes=f"Imported via API ({action})",
                created_at=now,
            )
            self.db.add(version)

            # Note: industry_pack_contents table is removed. Content tracking relies on pack_id FKs.

            self.db.commit()

            return {
                "success": True,
                "pack_id": pack_id,
                "pack_name": manifest.get("pack_name", ""),
                "strategy": action,
                "contents_count": len(contents),
                "action": action,
            }

        except Exception as e:
            self.db.rollback()
            if isinstance(e, PackImportError):
                raise
            raise PackImportError(f"Database write failed: {e}") from e
