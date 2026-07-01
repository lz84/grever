# -*- coding: utf-8 -*-
"""
单元测试: reins/industry/pack_exporter.py

覆盖:
1. PackExporter.export_pack() - grever-pack (zip) 格式
2. PackExporter.export_pack() - json 格式
3. 导出文件包含 manifest.json + checksum.json + 内容
4. PackNotFoundError 处理
5. UnsupportedFormatError 处理

Sprint 109: B109-1 测试
"""

import hashlib
import json
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
src_dir = str(Path(__file__).parent.parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from reins.industry.pack_exporter import (
    PackExporter,
    PackNotFoundError,
    UnsupportedFormatError,
    SUPPORTED_FORMATS,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Create a mock SQLAlchemy session with realistic pack data."""
    db = MagicMock()

    # Pack metadata row
    pack_row = MagicMock()
    pack_row.__len__ = lambda self: 23
    pack_row.__getitem__ = lambda self, i: [
        "pack-chemical-emergency-v1",  # 0: id
        "化工应急行业包",                # 1: name
        "chemical-emergency",           # 2: industry
        "1.0.0",                       # 3: version
        "化工应急响应行业包",            # 4: description
        14,                            # 5: tags_count
        0,                             # 6: scenarios_count
        0,                             # 7: skills_count
        "draft",                       # 8: status
        1779700319,                    # 9: created_at
        1779852914,                    # 10: updated_at
        "standard",                    # 11: pack_type
        None,                          # 12: base_pack_id
        "1.0",                         # 13: format_version
        None,                          # 14: author
        "proprietary",                 # 15: license
        None,                          # 16: compatibility_min_version
        None,                          # 17: compatibility_max_version
        None,                          # 18: source_checksum
        None,                          # 19: source_signature
        "created",                     # 20: import_source
        None,                          # 21: import_source_file
        "[]",                          # 22: dependencies
    ][i]
    pack_row.keys = lambda: [
        "id", "name", "industry", "version", "description",
        "tags_count", "scenarios_count", "skills_count", "status",
        "created_at", "updated_at", "pack_type", "base_pack_id",
        "format_version", "author", "license",
        "compatibility_min_version", "compatibility_max_version",
        "source_checksum", "source_signature", "import_source",
        "import_source_file", "dependencies",
    ]

    # Content rows
    content_rows = [
        ("pack-chemical-emergency-v1", "tag", "biz:chemical-park-operations"),
        ("pack-chemical-emergency-v1", "tag", "biz:emergency-management"),
        ("pack-chemical-emergency-v1", "tag", "chem:hazmat-identification"),
    ]

    def mock_execute(sql, params=None):
        result = MagicMock()
        sql_str = str(sql)
        if "industry_packs" in sql_str and "WHERE" in sql_str:
            if params and params.get("id") == "pack-chemical-emergency-v1":
                result.fetchone = MagicMock(return_value=pack_row)
            else:
                result.fetchone = MagicMock(return_value=None)
        elif "industry_pack_contents" in sql_str:
            result.fetchall = MagicMock(return_value=content_rows)
        return result

    db.execute = mock_execute
    return db


# ============================================================================
# Test: PackNotFoundError
# ============================================================================

class TestPackNotFoundError:
    """测试包不存在错误处理"""

    def test_export_nonexistent_pack_raises(self, mock_db_session):
        """导出不存在的包应该抛出 PackNotFoundError"""
        exporter = PackExporter(mock_db_session)
        with pytest.raises(PackNotFoundError) as exc_info:
            exporter.export_pack("nonexistent-pack")
        assert "nonexistent-pack" in str(exc_info.value)


# ============================================================================
# Test: UnsupportedFormatError
# ============================================================================

class TestUnsupportedFormatError:
    """测试不支持的格式错误处理"""

    def test_unsupported_format_raises(self, mock_db_session):
        """使用不支持的格式应该抛出 UnsupportedFormatError"""
        exporter = PackExporter(mock_db_session)
        with pytest.raises(UnsupportedFormatError) as exc_info:
            exporter.export_pack("pack-chemical-emergency-v1", format="xml")
        assert "xml" in str(exc_info.value)
        assert "grever-pack" in str(exc_info.value)

    def test_supported_formats_constant(self):
        """验证 SUPPORTED_FORMATS 包含预期值"""
        assert "grever-pack" in SUPPORTED_FORMATS
        assert "json" in SUPPORTED_FORMATS


# ============================================================================
# Test: ZIP Export (.grever-pack)
# ============================================================================

class TestZipExport:
    """测试 .grever-pack (zip) 格式导出"""

    def test_export_returns_bytes(self, mock_db_session):
        """导出应该返回 bytes"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="grever-pack")
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_export_is_valid_zip(self, mock_db_session):
        """导出的数据应该是有效的 zip 文件"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="grever-pack")
        # Should not raise
        zf = zipfile.ZipFile(BytesIO(data))
        zf.close()

    def test_zip_contains_manifest(self, mock_db_session):
        """zip 应该包含 manifest.json"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="grever-pack")
        zf = zipfile.ZipFile(BytesIO(data))
        names = zf.namelist()
        assert "manifest.json" in names
        zf.close()

    def test_zip_contains_checksum(self, mock_db_session):
        """zip 应该包含 checksum.json"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="grever-pack")
        zf = zipfile.ZipFile(BytesIO(data))
        names = zf.namelist()
        assert "checksum.json" in names
        zf.close()

    def test_zip_contains_contents(self, mock_db_session):
        """zip 应该包含 contents.json"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="grever-pack")
        zf = zipfile.ZipFile(BytesIO(data))
        names = zf.namelist()
        assert "contents.json" in names
        zf.close()

    def test_zip_contains_pack_meta(self, mock_db_session):
        """zip 应该包含 pack_meta.json"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="grever-pack")
        zf = zipfile.ZipFile(BytesIO(data))
        names = zf.namelist()
        assert "pack_meta.json" in names
        zf.close()

    def test_manifest_structure(self, mock_db_session):
        """manifest.json 应该有正确的结构"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="grever-pack")
        zf = zipfile.ZipFile(BytesIO(data))

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["pack_id"] == "pack-chemical-emergency-v1"
        assert manifest["pack_name"] == "化工应急行业包"
        assert manifest["industry"] == "chemical-emergency"
        assert manifest["version"] == "1.0.0"
        assert "manifest_version" in manifest
        assert "exported_at" in manifest
        assert "contents" in manifest
        assert "files" in manifest

        # Verify files have integrity hashes
        for filepath, file_info in manifest["files"].items():
            assert "integrity" in file_info
            assert file_info["integrity"].startswith("sha256:")

        zf.close()

    def test_checksum_structure(self, mock_db_session):
        """checksum.json 应该有正确的结构"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="grever-pack")
        zf = zipfile.ZipFile(BytesIO(data))

        checksum = json.loads(zf.read("checksum.json").decode("utf-8"))
        assert checksum["algorithm"] == "SHA256"
        assert checksum["pack_id"] == "pack-chemical-emergency-v1"
        assert "generated_at" in checksum
        assert "files" in checksum

        # Each file should have a SHA256 hash
        for name, hash_val in checksum["files"].items():
            assert hash_val.startswith("sha256:")
            # Verify the hash is valid hex
            hex_part = hash_val.split(":", 1)[1]
            assert len(hex_part) == 64  # SHA256 = 64 hex chars

        zf.close()

    def test_contents_data(self, mock_db_session):
        """contents.json 应该有正确的内容"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="grever-pack")
        zf = zipfile.ZipFile(BytesIO(data))

        contents = json.loads(zf.read("contents.json").decode("utf-8"))
        assert len(contents) == 3
        assert contents[0]["content_type"] == "tag"
        assert contents[0]["content_id"] == "biz:chemical-park-operations"

        zf.close()

    def test_all_files_have_checksums(self, mock_db_session):
        """checksum.json 应该包含内容文件的 hash (不包含 manifest.json 和 checksum.json)"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="grever-pack")
        zf = zipfile.ZipFile(BytesIO(data))

        checksum = json.loads(zf.read("checksum.json").decode("utf-8"))
        # checksum.json can't contain its own hash (chicken-and-egg)
        # and doesn't include manifest.json hash (manifest is updated after checksum)
        expected_files = {"pack_meta.json", "contents.json"}
        assert set(checksum["files"].keys()) == expected_files

        zf.close()


# ============================================================================
# Test: JSON Export
# ============================================================================

class TestJsonExport:
    """测试 JSON 格式导出"""

    def test_export_returns_bytes(self, mock_db_session):
        """JSON 导出应该返回 bytes"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="json")
        assert isinstance(data, bytes)

    def test_export_is_valid_json(self, mock_db_session):
        """JSON 导出应该是有效的 JSON"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="json")
        parsed = json.loads(data.decode("utf-8"))
        assert isinstance(parsed, dict)

    def test_json_contains_pack(self, mock_db_session):
        """JSON 导出应该包含 pack 字段"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="json")
        parsed = json.loads(data.decode("utf-8"))
        assert "pack" in parsed
        assert parsed["pack"]["id"] == "pack-chemical-emergency-v1"

    def test_json_contains_contents(self, mock_db_session):
        """JSON 导出应该包含 contents 字段"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="json")
        parsed = json.loads(data.decode("utf-8"))
        assert "contents" in parsed
        assert len(parsed["contents"]) == 3

    def test_json_contains_checksum(self, mock_db_session):
        """JSON 导出应该包含 checksum 字段"""
        exporter = PackExporter(mock_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="json")
        parsed = json.loads(data.decode("utf-8"))
        assert "checksum" in parsed
        assert parsed["checksum"]["algorithm"] == "SHA256"
        assert len(parsed["checksum"]["value"]) == 64


# ============================================================================
# Test: SHA256 utility
# ============================================================================

class TestSha256:
    """测试 SHA256 工具函数"""

    def test_sha256_known_value(self):
        """测试已知值的 SHA256"""
        data = b"hello world"
        expected = hashlib.sha256(data).hexdigest()
        assert PackExporter._sha256(data) == expected

    def test_sha256_empty(self):
        """测试空数据的 SHA256"""
        result = PackExporter._sha256(b"")
        assert len(result) == 64


# ============================================================================
# Integration-like test: Real DB (if available)
# ============================================================================

class TestWithRealDB:
    """使用真实数据库的集成测试 (如果数据库可用)"""

    @pytest.fixture
    def real_db_session(self):
        """Try to create a real DB session."""
        try:
            from shared.database.config import DB_CONFIG, get_engine
            from reins.common.database import get_db_session

            session = get_db_session()
            yield session
            session.close()
        except Exception:
            pytest.skip("Real database not available")

    def test_real_db_export_zip(self, real_db_session):
        """使用真实数据库导出 zip 应该成功"""
        exporter = PackExporter(real_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="grever-pack")
        zf = zipfile.ZipFile(BytesIO(data))
        names = zf.namelist()
        assert "manifest.json" in names
        assert "checksum.json" in names
        assert len(names) >= 4
        zf.close()

    def test_real_db_export_json(self, real_db_session):
        """使用真实数据库导出 JSON 应该成功"""
        exporter = PackExporter(real_db_session)
        data = exporter.export_pack("pack-chemical-emergency-v1", format="json")
        parsed = json.loads(data.decode("utf-8"))
        assert parsed["pack"]["id"] == "pack-chemical-emergency-v1"
        assert "checksum" in parsed
