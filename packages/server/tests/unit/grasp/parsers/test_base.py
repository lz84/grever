"""
Base parser tests
"""

import pytest
from src.grasp.parser.base import BaseParser, CognitiveEntry


class TestCognitiveEntry:
    """Test CognitiveEntry dataclass"""
    
    def test_cognitive_entry_creation(self):
        """测试 CognitiveEntry 基本创建"""
        entry = CognitiveEntry(
            title="Test Title",
            content="Test content",
            entry_type="concept",
            source_doc="test.md"
        )
        
        assert entry.title == "Test Title"
        assert entry.content == "Test content"
        assert entry.entry_type == "concept"
        assert entry.source_doc == "test.md"
        assert entry.source_section == ""
        assert entry.tags == []
        assert entry.confidence == 0.8
        assert entry.metadata == {}
    
    def test_cognitive_entry_full_creation(self):
        """测试 CognitiveEntry 完整创建"""
        entry = CognitiveEntry(
            title="Full Title",
            content="Full content",
            entry_type="procedure",
            source_doc="doc.md",
            source_section="# Section 1",
            tags=["test", "example"],
            confidence=0.95,
            metadata={"key": "value"}
        )
        
        assert entry.title == "Full Title"
        assert entry.content == "Full content"
        assert entry.entry_type == "procedure"
        assert entry.source_doc == "doc.md"
        assert entry.source_section == "# Section 1"
        assert entry.tags == ["test", "example"]
        assert entry.confidence == 0.95
        assert entry.metadata == {"key": "value"}
    
    def test_cognitive_entry_to_dict(self):
        """测试 to_dict 方法"""
        entry = CognitiveEntry(
            title="Dict Test",
            content="Content",
            entry_type="example",
            source_doc="test.md",
            tags=["tag1"],
            confidence=0.9,
            metadata={"custom": "data"}
        )
        
        result = entry.to_dict()
        
        assert result['title'] == "Dict Test"
        assert result['content'] == "Content"
        assert result['entry_type'] == "example"
        assert result['source_doc'] == "test.md"
        assert result['tags'] == ["tag1"]
        assert result['confidence'] == 0.9
        assert result['metadata'] == {"custom": "data"}


class TestBaseParser:
    """Test BaseParser abstract class"""
    
    def test_supported_extensions_abstractmethod(self):
        """测试 supported_extensions 是抽象方法"""
        with pytest.raises(TypeError):
            BaseParser()  # type: ignore
