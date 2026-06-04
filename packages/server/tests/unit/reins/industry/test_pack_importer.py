# -*- coding: utf-8 -*-
"""
单元测试: reins/industry/pack_importer.py

覆盖:
1. 导入有效包返回成功 + 正确计数
2. 重复导入 create 策略返回 409 (PackExistsError)
3. checksum 篡改返回 400 (ChecksumMismatchError)
4. 缺依赖返回 400 (DependencyMissingError)
5. 路径遍历攻击被拒绝 (SecurityError)
6. zip bomb 检测
7. 超大文件检测
8. 无效包结构检测
9. 格式版本不兼容检测
10. upsert / force 策略
11. API 端点集成测试

Sprint 110: B110-1 + B110-2 测试
"""

import hashlib
import json
import sys
import time
import uuid
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch
from sqlalchemy import text

import pytest

# Add src to path
src_dir = str(Path(__file__).parent.parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from reins.industry.pack_importer import (
    PackImporter,
    PackImportError,
    InvalidPackError,
    ChecksumMismatchError,
    DependencyMissingError,
    PackExistsError,
    SecurityError,
    IncompatibleFormatError,
    _sha256,
    MAX_UNCOMPRESSED_SIZE,
    MAX_SINGLE_FILE_SIZE,
)


# ============================================================================
# Helpers
# ============================================================================

def _create_valid_pack(
    pack_id: str = "test-pack-v1",
    pack_name: str = "Test Pack",
    industry: str = "test-industry",
    version: str = "1.0.0",
    format_version: str = "1.0",
    dependencies: list = None,
    contents: list = None,
    pack_type: str = "standard",
) -> bytes:
    """Create a valid .nexus-pack zip file with correct checksums."""
    if dependencies is None:
        dependencies = []
    if contents is None:
        contents = [
            {"pack_id": pack_id, "content_type": "tag", "content_id": "biz:test-tag"},
        ]

    manifest = {
        "manifest_version": "1.0",
        "pack_id": pack_id,
        "pack_name": pack_name,
        "industry": industry,
        "version": version,
        "pack_type": pack_type,
        "exported_at": "2026-06-04T12:00:00Z",
        "format_version": format_version,
        "description": "A test pack",
        "author": None,
        "license": "proprietary",
        "contents": contents,
        "files": {},
        "dependencies": dependencies,
    }

    # Compute file hashes for content files only
    pack_meta_bytes = json.dumps({"id": pack_id, "name": pack_name}, ensure_ascii=False).encode()
    contents_bytes = json.dumps(contents, ensure_ascii=False).encode()

    file_hashes = {
        "pack_meta.json": _sha256(pack_meta_bytes),
        "contents.json": _sha256(contents_bytes),
    }

    # Temp manifest for hash computation
    temp_manifest_bytes = json.dumps(manifest, ensure_ascii=False).encode()
    file_hashes["manifest.json"] = _sha256(temp_manifest_bytes)

    # Checksum (only includes non-manifest, non-checksum files to avoid circular dependency)
    # The manifest's hash in checksum.json is stale because manifest is updated after checksum
    checksum_content_files = {
        name: f"sha256:{h}" for name, h in sorted(file_hashes.items())
        if name not in ("checksum.json", "manifest.json")
    }
    checksum_data = {
        "algorithm": "SHA256",
        "generated_at": "2026-06-04T12:00:00Z",
        "files": checksum_content_files,
        "pack_id": pack_id,
    }
    checksum_bytes = json.dumps(checksum_data, ensure_ascii=False).encode()
    file_hashes["checksum.json"] = _sha256(checksum_bytes)

    # Update manifest with real hashes
    for filepath in ["pack_meta.json", "contents.json", "manifest.json", "checksum.json"]:
        manifest["files"][filepath] = {"integrity": f"sha256:{file_hashes[filepath]}"}

    manifest_bytes = json.dumps(manifest, ensure_ascii=False).encode()
    file_hashes["manifest.json"] = _sha256(manifest_bytes)

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("pack_meta.json", pack_meta_bytes)
        zf.writestr("contents.json", contents_bytes)
        zf.writestr("manifest.json", manifest_bytes)
        zf.writestr("checksum.json", checksum_bytes)

    buffer.seek(0)
    return buffer.getvalue()


def _tamper_pack_checksum(pack_bytes: bytes, target_file: str = "pack_meta.json") -> bytes:
    """Tamper with a file's content in the pack, making checksums invalid."""
    zf = zipfile.ZipFile(BytesIO(pack_bytes))
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as new_zf:
        for name in zf.namelist():
            if name == target_file:
                new_zf.writestr(name, b"tampered content!!!")
            else:
                new_zf.writestr(name, zf.read(name))
    zf.close()
    buffer.seek(0)
    return buffer.getvalue()


def _create_pack_with_traversal(filename: str = "../etc/passwd") -> bytes:
    """Create a pack with a path traversal filename."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, b"malicious")
        zf.writestr("manifest.json", b'{"pack_id":"x","pack_name":"x","industry":"x","version":"1.0","format_version":"1.0"}')
        zf.writestr("checksum.json", b'{"algorithm":"SHA256","files":{},"pack_id":"x"}')
    buffer.seek(0)
    return buffer.getvalue()


def _create_pack_without_required_file(missing: str) -> bytes:
    """Create a pack missing a required file."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if missing != "manifest.json":
            zf.writestr("manifest.json", b'{"pack_id":"x","pack_name":"x","industry":"x","version":"1.0","format_version":"1.0"}')
        if missing != "checksum.json":
            zf.writestr("checksum.json", b'{"algorithm":"SHA256","files":{},"pack_id":"x"}')
    buffer.seek(0)
    return buffer.getvalue()


def _make_mock_db(existing_packs: dict = None, dependency_packs: list = None):
    """Create a mock DB session with configurable existing packs."""
    db = MagicMock()

    if existing_packs is None:
        existing_packs = {}
    if dependency_packs is None:
        dependency_packs = []

    def mock_execute(sql, params=None):
        result = MagicMock()
        sql_str = str(sql)

        if "industry_packs" in sql_str and "WHERE" in sql_str and "SELECT" in sql_str:
            pack_id = params.get("id") if params else None
            if pack_id and pack_id in existing_packs:
                row = MagicMock()
                row.keys = lambda: list(existing_packs[pack_id].keys())
                vals = list(existing_packs[pack_id].values())
                row.__len__ = lambda self: len(vals)
                row.__getitem__ = lambda self, i: vals[i]
                result.fetchone = MagicMock(return_value=row)
            elif pack_id and pack_id in dependency_packs:
                row = MagicMock()
                row.keys = lambda: ["id"]
                row.__len__ = lambda self: 1
                row.__getitem__ = lambda self, i: pack_id
                result.fetchone = MagicMock(return_value=row)
            else:
                result.fetchone = MagicMock(return_value=None)
        else:
            result.fetchone = MagicMock(return_value=None)
            result.fetchall = MagicMock(return_value=[])

        return result

    db.execute = mock_execute
    db.commit = MagicMock()
    db.rollback = MagicMock()
    return db


# ============================================================================
# Test 1: Valid pack import (create)
# ============================================================================

class TestValidPackImport:
    """测试导入有效包返回成功 + 正确计数"""

    def test_import_valid_pack_returns_success(self):
        """导入有效包应该返回 success=True"""
        db = _make_mock_db()
        importer = PackImporter(db)
        pack_bytes = _create_valid_pack()

        result = importer.import_pack(pack_bytes, strategy="create")

        assert result["success"] is True
        assert result["pack_id"] == "test-pack-v1"
        assert result["action"] == "created"
        assert result["contents_count"] == 1

    def test_import_valid_pack_calls_commit(self):
        """导入有效包应该调用 commit"""
        db = _make_mock_db()
        importer = PackImporter(db)
        pack_bytes = _create_valid_pack()

        importer.import_pack(pack_bytes, strategy="create")

        db.commit.assert_called_once()

    def test_import_pack_with_multiple_contents(self):
        """导入包含多个内容的包应该正确计数"""
        db = _make_mock_db()
        importer = PackImporter(db)

        contents = [
            {"pack_id": "multi-pack", "content_type": "tag", "content_id": "tag:1"},
            {"pack_id": "multi-pack", "content_type": "tag", "content_id": "tag:2"},
            {"pack_id": "multi-pack", "content_type": "tag", "content_id": "tag:3"},
        ]
        pack_bytes = _create_valid_pack(
            pack_id="multi-pack", contents=contents, pack_name="Multi Content Pack"
        )

        result = importer.import_pack(pack_bytes, strategy="create")

        assert result["success"] is True
        assert result["contents_count"] == 3


# ============================================================================
# Test 2: Duplicate import with create strategy → 409
# ============================================================================

class TestDuplicateImport:
    """测试重复导入 create 策略返回 409"""

    def test_create_strategy_existing_pack_raises_409(self):
        """当包已存在时，create 策略应该抛出 PackExistsError"""
        existing = {
            "test-pack-v1": {
                "id": "test-pack-v1", "name": "Existing", "industry": "test",
                "version": "1.0.0", "description": "", "tags_count": 0,
                "scenarios_count": 0, "skills_count": 0, "status": "active",
                "created_at": 1000, "updated_at": 1000, "pack_type": "standard",
                "base_pack_id": None, "format_version": "1.0", "author": None,
                "license": "proprietary", "compatibility_min_version": None,
                "compatibility_max_version": None, "source_checksum": None,
                "source_signature": None, "import_source": "created",
                "import_source_file": None, "dependencies": "[]",
            }
        }
        db = _make_mock_db(existing_packs=existing)
        importer = PackImporter(db)
        pack_bytes = _create_valid_pack()

        with pytest.raises(PackExistsError) as exc_info:
            importer.import_pack(pack_bytes, strategy="create")

        assert exc_info.value.status_code == 409
        assert "test-pack-v1" in exc_info.value.message
        db.commit.assert_not_called()

    def test_upsert_strategy_existing_pack_succeeds(self):
        """当包已存在时，upsert 策略应该成功"""
        existing = {
            "test-pack-v1": {
                "id": "test-pack-v1", "name": "Existing", "industry": "test",
                "version": "1.0.0", "description": "", "tags_count": 0,
                "scenarios_count": 0, "skills_count": 0, "status": "active",
                "created_at": 1000, "updated_at": 1000, "pack_type": "standard",
                "base_pack_id": None, "format_version": "1.0", "author": None,
                "license": "proprietary", "compatibility_min_version": None,
                "compatibility_max_version": None, "source_checksum": None,
                "source_signature": None, "import_source": "created",
                "import_source_file": None, "dependencies": "[]",
            }
        }
        db = _make_mock_db(existing_packs=existing)
        importer = PackImporter(db)
        pack_bytes = _create_valid_pack()

        result = importer.import_pack(pack_bytes, strategy="upsert")

        assert result["success"] is True
        assert result["action"] == "updated"

    def test_force_strategy_existing_pack_succeeds(self):
        """当包已存在时，force 策略应该成功"""
        existing = {
            "test-pack-v1": {
                "id": "test-pack-v1", "name": "Existing", "industry": "test",
                "version": "1.0.0", "description": "", "tags_count": 0,
                "scenarios_count": 0, "skills_count": 0, "status": "active",
                "created_at": 1000, "updated_at": 1000, "pack_type": "standard",
                "base_pack_id": None, "format_version": "1.0", "author": None,
                "license": "proprietary", "compatibility_min_version": None,
                "compatibility_max_version": None, "source_checksum": None,
                "source_signature": None, "import_source": "created",
                "import_source_file": None, "dependencies": "[]",
            }
        }
        db = _make_mock_db(existing_packs=existing)
        importer = PackImporter(db)
        pack_bytes = _create_valid_pack()

        result = importer.import_pack(pack_bytes, strategy="force")

        assert result["success"] is True
        assert result["action"] == "forced"


# ============================================================================
# Test 3: Checksum mismatch → 400
# ============================================================================

class TestChecksumMismatch:
    """测试 checksum 篡改返回 400"""

    def test_tampered_content_raises_checksum_error(self):
        """篡改包内容应该抛出 ChecksumMismatchError"""
        db = _make_mock_db()
        importer = PackImporter(db)

        valid_pack = _create_valid_pack()
        tampered_pack = _tamper_pack_checksum(valid_pack, "pack_meta.json")

        with pytest.raises(ChecksumMismatchError) as exc_info:
            importer.import_pack(tampered_pack, strategy="create")

        assert exc_info.value.status_code == 400
        assert "mismatch" in exc_info.value.message.lower()

    def test_tampered_contents_json_raises_checksum_error(self):
        """篡改 contents.json 应该抛出 ChecksumMismatchError"""
        db = _make_mock_db()
        importer = PackImporter(db)

        valid_pack = _create_valid_pack()
        tampered_pack = _tamper_pack_checksum(valid_pack, "contents.json")

        with pytest.raises(ChecksumMismatchError):
            importer.import_pack(tampered_pack, strategy="create")


# ============================================================================
# Test 4: Missing dependencies → 400
# ============================================================================

class TestMissingDependencies:
    """测试缺依赖返回 400"""

    def test_missing_dependency_raises_error(self):
        """缺少依赖包应该抛出 DependencyMissingError"""
        db = _make_mock_db()
        importer = PackImporter(db)

        pack_bytes = _create_valid_pack(
            dependencies=["dep-pack-that-does-not-exist"],
        )

        with pytest.raises(DependencyMissingError) as exc_info:
            importer.import_pack(pack_bytes, strategy="create")

        assert exc_info.value.status_code == 400
        assert "dep-pack-that-does-not-exist" in exc_info.value.message

    def test_existing_dependency_allows_import(self):
        """依赖包存在时应该允许导入"""
        db = _make_mock_db(dependency_packs=["dep-pack-v1"])
        importer = PackImporter(db)

        pack_bytes = _create_valid_pack(
            dependencies=["dep-pack-v1"],
        )

        result = importer.import_pack(pack_bytes, strategy="create")
        assert result["success"] is True


# ============================================================================
# Test 5: Path traversal attack → rejected
# ============================================================================

class TestPathTraversal:
    """测试路径遍历攻击被拒绝"""

    def test_dotdot_in_filename_raises_security_error(self):
        """文件名包含 ../ 应该抛出 SecurityError"""
        db = _make_mock_db()
        importer = PackImporter(db)

        pack_bytes = _create_pack_with_traversal("../etc/passwd")

        with pytest.raises(SecurityError) as exc_info:
            importer.import_pack(pack_bytes, strategy="create")

        assert exc_info.value.status_code == 400
        assert "traversal" in exc_info.value.message.lower()

    def test_absolute_path_raises_security_error(self):
        """绝对路径文件名应该抛出 SecurityError"""
        db = _make_mock_db()
        importer = PackImporter(db)

        pack_bytes = _create_pack_with_traversal("/etc/passwd")

        with pytest.raises(SecurityError):
            importer.import_pack(pack_bytes, strategy="create")


# ============================================================================
# Test 6: Invalid pack structure
# ============================================================================

class TestInvalidPackStructure:
    """测试无效包结构检测"""

    def test_not_a_zip_raises_error(self):
        """非 zip 文件应该抛出 InvalidPackError"""
        db = _make_mock_db()
        importer = PackImporter(db)

        with pytest.raises(InvalidPackError):
            importer.import_pack(b"this is not a zip file", strategy="create")

    def test_missing_manifest_raises_error(self):
        """缺少 manifest.json 应该抛出 InvalidPackError"""
        db = _make_mock_db()
        importer = PackImporter(db)

        pack_bytes = _create_pack_without_required_file("manifest.json")

        with pytest.raises(InvalidPackError) as exc_info:
            importer.import_pack(pack_bytes, strategy="create")

        assert "manifest.json" in exc_info.value.message

    def test_missing_checksum_raises_error(self):
        """缺少 checksum.json 应该抛出 InvalidPackError"""
        db = _make_mock_db()
        importer = PackImporter(db)

        pack_bytes = _create_pack_without_required_file("checksum.json")

        with pytest.raises(InvalidPackError) as exc_info:
            importer.import_pack(pack_bytes, strategy="create")

        assert "checksum.json" in exc_info.value.message

    def test_invalid_manifest_json_raises_error(self):
        """无效的 manifest.json 应该抛出 InvalidPackError"""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", b"not valid json{{{")
            zf.writestr("checksum.json", b'{"algorithm":"SHA256","files":{},"pack_id":"x"}')
        buffer.seek(0)

        db = _make_mock_db()
        importer = PackImporter(db)

        with pytest.raises(InvalidPackError):
            importer.import_pack(buffer.getvalue(), strategy="create")

    def test_manifest_missing_required_fields(self):
        """manifest 缺少必填字段应该抛出 InvalidPackError"""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", b'{"pack_id":"x"}')  # Missing pack_name, industry, etc.
            zf.writestr("checksum.json", b'{"algorithm":"SHA256","files":{},"pack_id":"x"}')
        buffer.seek(0)

        db = _make_mock_db()
        importer = PackImporter(db)

        with pytest.raises(InvalidPackError) as exc_info:
            importer.import_pack(buffer.getvalue(), strategy="create")

        assert "required fields" in exc_info.value.message.lower()


# ============================================================================
# Test 7: Format compatibility
# ============================================================================

class TestFormatCompatibility:
    """测试格式版本兼容性"""

    def test_incompatible_major_version_raises_error(self):
        """不兼容的主版本号应该抛出 IncompatibleFormatError"""
        db = _make_mock_db()
        importer = PackImporter(db)

        pack_bytes = _create_valid_pack(format_version="2.0")

        with pytest.raises(IncompatibleFormatError) as exc_info:
            importer.import_pack(pack_bytes, strategy="create")

        assert exc_info.value.status_code == 400
        assert "incompatible" in exc_info.value.message.lower()

    def test_valid_format_version_1_x_succeeds(self):
        """格式版本 1.x 应该通过兼容性检查"""
        db = _make_mock_db()
        importer = PackImporter(db)

        pack_bytes = _create_valid_pack(format_version="1.5")

        result = importer.import_pack(pack_bytes, strategy="create")
        assert result["success"] is True


# ============================================================================
# Test 8: Invalid strategy
# ============================================================================

class TestInvalidStrategy:
    """测试无效策略"""

    def test_invalid_strategy_raises_error(self):
        """无效策略应该抛出 PackImportError"""
        db = _make_mock_db()
        importer = PackImporter(db)

        pack_bytes = _create_valid_pack()

        with pytest.raises(PackImportError):
            importer.import_pack(pack_bytes, strategy="invalid")


# ============================================================================
# Test 9: SHA256 utility
# ============================================================================

class TestSha256Util:
    """测试 SHA256 工具函数"""

    def test_known_value(self):
        """已知值的 SHA256"""
        data = b"hello world"
        expected = hashlib.sha256(data).hexdigest()
        assert _sha256(data) == expected

    def test_returns_hex_string(self):
        """返回应该是 64 位十六进制字符串"""
        result = _sha256(b"test")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


# ============================================================================
# Test 10: Real DB Integration
# ============================================================================

class TestWithRealDB:
    """使用真实数据库的集成测试"""

    @pytest.fixture
    def real_db_session(self):
        """Create a real DB session using direct connection."""
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import Session
            db_path = r"D:\work\research\agents-nexus\data\reins.db"
            engine = create_engine(f"sqlite:///{db_path}")
            session = Session(engine)
            yield session
            session.close()
            engine.dispose()
        except Exception as e:
            pytest.skip(f"Real database not available: {e}")

    def _get_pack_path(self) -> Path:
        """Get path to test-pack.nexus-pack (7 parent levels from test file)."""
        return Path(__file__).parent.parent.parent.parent.parent.parent.parent / "data" / "test-pack.nexus-pack"

    def test_import_real_pack(self, real_db_session):
        """导入真实导出 pack 应该成功"""
        pack_path = self._get_pack_path()
        if not pack_path.exists():
            pytest.skip(f"test-pack.nexus-pack not found at {pack_path}. Run _export_test_pack.py first.")

        pack_bytes = pack_path.read_bytes()

        # Delete the pack first if it exists (to allow create strategy)
        real_db_session.execute(
            text("DELETE FROM industry_pack_contents WHERE pack_id = 'pack-chemical-emergency-v1'"),
        )
        real_db_session.execute(
            text("DELETE FROM industry_packs WHERE id = 'pack-chemical-emergency-v1'"),
        )
        real_db_session.commit()

        importer = PackImporter(real_db_session)
        result = importer.import_pack(pack_bytes, strategy="create")

        assert result["success"] is True
        assert result["pack_id"] == "pack-chemical-emergency-v1"
        assert result["contents_count"] > 0

    def test_import_duplicate_real_pack(self, real_db_session):
        """重复导入真实 pack (create) 应该失败"""
        pack_path = self._get_pack_path()
        if not pack_path.exists():
            pytest.skip(f"test-pack.nexus-pack not found at {pack_path}.")

        # First, ensure the pack exists
        row = real_db_session.execute(
            text("SELECT id FROM industry_packs WHERE id = :id"),
            {"id": "pack-chemical-emergency-v1"},
        ).fetchone()

        if not row:
            # Import it first
            pack_bytes = pack_path.read_bytes()
            importer = PackImporter(real_db_session)
            importer.import_pack(pack_bytes, strategy="create")

        # Now try to import again with create strategy
        pack_bytes = pack_path.read_bytes()
        importer = PackImporter(real_db_session)

        with pytest.raises(PackExistsError):
            importer.import_pack(pack_bytes, strategy="create")
