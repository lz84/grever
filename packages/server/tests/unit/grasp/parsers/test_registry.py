"""
Registry tests
"""

import pytest
from grasp.parser import BaseParser, CognitiveEntry
from src.grasp.parser.registry import ParserRegistry, register_parser, get_parser, list_parsers


class MockParser(BaseParser):
    """Mock parser for testing"""
    
    def supported_extensions(self):
        return ['.mock']
    
    def parse(self, file_path: str):
        return []


class TestParserRegistry:
    """Test ParserRegistry class"""
    
    def setup_method(self):
        """清除注册表状态"""
        ParserRegistry._parsers.clear()
        ParserRegistry._instances.clear()
    
    def test_register_parser(self):
        """测试注册解析器"""
        result = ParserRegistry.register(MockParser)
        
        assert result == MockParser
        assert '.mock' in ParserRegistry._parsers
        assert ParserRegistry._parsers['.mock'] == MockParser
    
    def test_get_parser(self):
        """测试获取解析器"""
        ParserRegistry.register(MockParser)
        
        parser = ParserRegistry.get_parser('test.mock')
        
        assert isinstance(parser, MockParser)
    
    def test_get_parser_not_found(self):
        """测试获取不存在的解析器"""
        with pytest.raises(ValueError) as exc_info:
            ParserRegistry.get_parser('test.txt')
        
        assert "No parser registered" in str(exc_info.value)
    
    def test_get_supported_extensions(self):
        """测试获取支持的扩展名"""
        ParserRegistry.register(MockParser)
        
        extensions = ParserRegistry.get_supported_extensions()
        
        assert '.mock' in extensions
    
    def test_list_parsers(self):
        """测试列出解析器"""
        ParserRegistry.register(MockParser)
        
        parsers = ParserRegistry.list_parsers()
        
        assert '.mock' in parsers
        assert parsers['.mock'] == 'MockParser'


class TestRegistryFunctions:
    """Test registry convenience functions"""
    
    def setup_method(self):
        """清除注册表状态"""
        ParserRegistry._parsers.clear()
        ParserRegistry._instances.clear()
    
    def test_register_parser_decorator(self):
        """测试装饰器方式注册"""
        @register_parser
        class TestParser(BaseParser):
            def supported_extensions(self):
                return ['.test']
            
            def parse(self, file_path: str):
                return []
        
        assert '.test' in ParserRegistry._parsers
    
    def test_get_parser_function(self):
        """测试 get_parser 函数"""
        ParserRegistry.register(MockParser)
        
        parser = get_parser('test.mock')
        
        assert isinstance(parser, MockParser)
    
    def test_list_parsers_function(self):
        """测试 list_parsers 函数"""
        ParserRegistry.register(MockParser)
        
        parsers = list_parsers()
        
        assert '.mock' in parsers
