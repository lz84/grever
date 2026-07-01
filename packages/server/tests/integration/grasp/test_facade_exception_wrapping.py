"""
GraspFacade 统一异常包装测试 — Sprint 101-1

测试目标：
1. 适配器异常被统一包装为 GreverException
2. facade 层不泄露适配器内部异常细节
3. UnknownBackendError 是 GreverException 子类
4. 各 CRUD 操作的异常处理正确
"""

import sys
import os
# Add src to path (before any local imports)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from grasp.facade.service import GraspFacade, UnknownBackendError, _wrap_adapter_error
from grasp.facade.models import CognitionInput
from grasp.adapters.registry import AdapterRegistry
from grasp.adapters.base import BaseGraspAdapter
from shared.common.exceptions import GreverException, ErrorCode


# ============================================================
# 辅助：创建模拟适配器
# ============================================================

def _make_mock_adapter(name: str = "mock", available: bool = True):
    adapter = MagicMock(spec=BaseGraspAdapter)
    adapter.name = name
    adapter.is_available.return_value = available
    adapter.inject = AsyncMock()
    adapter.retrieve = AsyncMock()
    adapter.update = AsyncMock()
    adapter.delete = AsyncMock()
    adapter.search_by_content_hash = AsyncMock(return_value=None)
    adapter.get_status.return_value = {"index_size": 0, "backend_version": "test"}
    return adapter


def _make_facade_with_mock_adapter(mock_adapter: MagicMock) -> GraspFacade:
    registry = AdapterRegistry()
    registry.register(mock_adapter)
    facade = GraspFacade(registry=registry)
    # Force active backend to our mock
    facade._active_backend = mock_adapter.name
    return facade


# ============================================================
# Test 1: UnknownBackendError 是 GreverException 子类
# ============================================================

class TestUnknownBackendError:
    def test_is_nexus_exception(self):
        """UnknownBackendError 必须继承 GreverException"""
        err = UnknownBackendError("cog-test-123")
        assert isinstance(err, GreverException)
        assert err.code == ErrorCode.GRASP_BACKEND_UNAVAILABLE
        assert "cog-test-123" in err.message
        assert err.details["cognition_id"] == "cog-test-123"

    def test_http_status_is_400(self):
        """GRASP_BACKEND_UNAVAILABLE (2010) 应该映射到 HTTP 400"""
        err = UnknownBackendError("cog-xyz")
        # 2000-2999 范围内的错误码映射到 400
        assert err.http_status == 400

    def test_to_dict_format(self):
        """to_dict 返回标准错误格式"""
        err = UnknownBackendError("cog-456")
        d = err.to_dict()
        assert "error" in d
        assert d["error"]["code"] == int(ErrorCode.GRASP_BACKEND_UNAVAILABLE)
        assert "message" in d["error"]
        assert "reference_id" in d["error"]


# ============================================================
# Test 2: _wrap_adapter_error 正确包装各种异常
# ============================================================

class TestWrapAdapterError:
    def test_keyerror_wrapped_as_not_found(self):
        """KeyError 应包装为 GRASP_NOT_FOUND"""
        err = _wrap_adapter_error("update", KeyError("'cog-missing'"))
        assert isinstance(err, GreverException)
        assert err.code == ErrorCode.GRASP_NOT_FOUND
        assert "cog-missing" in err.message

    def test_runtimeerror_wrapped_as_backend_unavailable(self):
        """RuntimeError 应包装为 GRASP_BACKEND_UNAVAILABLE"""
        err = _wrap_adapter_error("inject", RuntimeError("cost limit reached"))
        assert isinstance(err, GreverException)
        assert err.code == ErrorCode.GRASP_BACKEND_UNAVAILABLE
        assert err.details["operation"] == "inject"

    def test_oserror_wrapped_as_operation_specific(self):
        """OSError 应按操作类型分配错误码（而非通用 GRASP_BACKEND_UNAVAILABLE）"""
        err = _wrap_adapter_error("retrieve", OSError("disk full"))
        assert isinstance(err, GreverException)
        assert err.code == ErrorCode.GRASP_RETRIEVE_ERROR
        assert err.details["operation"] == "retrieve"

    def test_inject_error_code(self):
        """inject 操作的 ErrorCode 应为 GRASP_INJECT_ERROR"""
        err = _wrap_adapter_error("inject", FileNotFoundError("missing"))
        assert err.code == ErrorCode.GRASP_INJECT_ERROR

    def test_retrieve_error_code(self):
        """retrieve 操作的 ErrorCode 应为 GRASP_RETRIEVE_ERROR"""
        err = _wrap_adapter_error("retrieve", PermissionError("denied"))
        assert err.code == ErrorCode.GRASP_RETRIEVE_ERROR

    def test_update_error_code(self):
        """update 操作的 ErrorCode 应为 GRASP_UPDATE_ERROR"""
        err = _wrap_adapter_error("update", IOError("write failed"))
        assert err.code == ErrorCode.GRASP_UPDATE_ERROR

    def test_delete_error_code(self):
        """delete 操作的 ErrorCode 应为 GRASP_DELETE_ERROR"""
        err = _wrap_adapter_error("delete", OSError("delete failed"))
        assert err.code == ErrorCode.GRASP_DELETE_ERROR

    def test_does_not_leak_exception_type_name(self):
        """包装后的错误消息不应包含内部异常类名"""
        err = _wrap_adapter_error("inject", RuntimeError("some internal error"))
        # 消息中不应出现 "RuntimeError" 等内部类型名
        assert "RuntimeError" not in err.message
        assert "Traceback" not in err.message


# ============================================================
# Test 3: GraspFacade.inject 异常处理
# ============================================================

class TestFacadeInjectException:
    @pytest.mark.asyncio
    async def test_inject_adapter_runtimeerror(self):
        """inject 时适配器抛 RuntimeError → GreverException"""
        mock = _make_mock_adapter()
        mock.inject.side_effect = RuntimeError("GraphRAG 每日成本上限已达")
        facade = _make_facade_with_mock_adapter(mock)

        input_data = CognitionInput(content="test content", type="what")

        with pytest.raises(GreverException) as exc_info:
            await facade.inject(input_data)

        assert exc_info.value.code == ErrorCode.GRASP_BACKEND_UNAVAILABLE
        # 不泄露 RuntimeError 类名
        assert "RuntimeError" not in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_inject_adapter_oserror(self):
        """inject 时适配器抛 OSError → GreverException"""
        mock = _make_mock_adapter()
        mock.inject.side_effect = OSError("disk write failed")
        facade = _make_facade_with_mock_adapter(mock)

        input_data = CognitionInput(content="test content", type="what")

        with pytest.raises(GreverException) as exc_info:
            await facade.inject(input_data)

        assert exc_info.value.code == ErrorCode.GRASP_INJECT_ERROR


# ============================================================
# Test 4: GraspFacade.retrieve 异常处理
# ============================================================

class TestFacadeRetrieveException:
    @pytest.mark.asyncio
    async def test_retrieve_adapter_exception(self):
        """retrieve 时适配器抛异常 → GreverException"""
        from grasp.facade.models import RetrieveResult
        mock = _make_mock_adapter()
        mock.retrieve.side_effect = IOError("query failed")
        facade = _make_facade_with_mock_adapter(mock)

        with pytest.raises(GreverException) as exc_info:
            await facade.retrieve(query="test")

        assert exc_info.value.code == ErrorCode.GRASP_RETRIEVE_ERROR
        assert exc_info.value.details["operation"] == "retrieve"


# ============================================================
# Test 5: GraspFacade.update 异常处理
# ============================================================

class TestFacadeUpdateException:
    @pytest.mark.asyncio
    async def test_update_adapter_keyerror(self):
        """update 时适配器抛 KeyError → GRASP_NOT_FOUND"""
        mock = _make_mock_adapter()
        mock.update.side_effect = KeyError("'cog-123'")
        facade = _make_facade_with_mock_adapter(mock)

        # 先注入一个映射
        facade._record_backend_mapping("cog-123", "mock")

        with pytest.raises(GreverException) as exc_info:
            await facade.update("cog-123", "new content", {})

        assert exc_info.value.code == ErrorCode.GRASP_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_unknown_backend(self):
        """update 时找不到后端映射 → UnknownBackendError"""
        mock = _make_mock_adapter()
        facade = _make_facade_with_mock_adapter(mock)

        with pytest.raises(UnknownBackendError) as exc_info:
            await facade.update("nonexistent-cog-id", "new content", {})

        assert exc_info.value.code == ErrorCode.GRASP_BACKEND_UNAVAILABLE


# ============================================================
# Test 6: GraspFacade.delete 异常处理
# ============================================================

class TestFacadeDeleteException:
    @pytest.mark.asyncio
    async def test_delete_adapter_exception(self):
        """delete 时适配器抛异常 → GreverException"""
        mock = _make_mock_adapter()
        mock.delete.side_effect = OSError("delete failed")
        facade = _make_facade_with_mock_adapter(mock)
        facade._record_backend_mapping("cog-del", "mock")

        with pytest.raises(GreverException) as exc_info:
            await facade.delete("cog-del")

        assert exc_info.value.code == ErrorCode.GRASP_DELETE_ERROR


# ============================================================
# Test 7: 正常流程不受影响
# ============================================================

class TestFacadeNormalFlow:
    @pytest.mark.asyncio
    async def test_inject_success(self):
        """正常 inject 应返回 InjectResult"""
        from grasp.facade.models import InjectResult
        mock = _make_mock_adapter()
        mock.inject.return_value = InjectResult(
            cognition_id="cog-123",
            backend="mock",
            quality_score=0.8,
        )
        facade = _make_facade_with_mock_adapter(mock)

        result = await facade.inject(CognitionInput(content="hello world", type="what"))
        assert result.cognition_id == "cog-123"
        # quality_score 会被 facade 的 _quality_score 覆盖，只要 ≥ 0 即可
        assert result.quality_score >= 0

    @pytest.mark.asyncio
    async def test_retrieve_success(self):
        """正常 retrieve 应返回 RetrieveResult"""
        from grasp.facade.models import RetrieveResult, CognitionItem
        mock = _make_mock_adapter()
        mock.retrieve.return_value = RetrieveResult(
            items=[CognitionItem(cognition_id="cog-1", type="what", content="test")],
            total=1,
            has_more=False,
        )
        facade = _make_facade_with_mock_adapter(mock)

        result = await facade.retrieve(query="test")
        assert result.total == 1
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_update_success(self):
        """正常 update 应返回 UpdateResult"""
        from grasp.facade.models import UpdateResult
        mock = _make_mock_adapter()
        mock.update.return_value = UpdateResult(cognition_id="cog-123", quality_score=0.9)
        facade = _make_facade_with_mock_adapter(mock)
        facade._record_backend_mapping("cog-123", "mock")

        result = await facade.update("cog-123", "updated content", {})
        assert result.cognition_id == "cog-123"

    @pytest.mark.asyncio
    async def test_delete_success(self):
        """正常 delete 应返回 True"""
        mock = _make_mock_adapter()
        mock.delete.return_value = True
        facade = _make_facade_with_mock_adapter(mock)
        facade._record_backend_mapping("cog-del", "mock")

        result = await facade.delete("cog-del")
        assert result is True
        # 映射已清除
        assert "cog-del" not in facade._backend_map


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
