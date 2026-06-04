"""
解析器注册表
管理所有可用解析器并提供工厂方法
"""

from typing import Dict, Type, List
from grasp.parser.base import BaseParser, CognitiveEntry


class ParserRegistry:
    """
    解析器注册表
    支持解析器的注册、查找和自动选择
    """
    
    _parsers: Dict[str, Type[BaseParser]] = {}
    _instances: Dict[str, BaseParser] = {}
    
    @classmethod
    def register(cls, parser_class: Type[BaseParser]) -> Type[BaseParser]:
        """
        注册解析器类
        
        Args:
            parser_class: 解析器类
        
        Returns:
            解析器类本身
        """
        instance = parser_class()
        for ext in instance.supported_extensions():
            cls._parsers[ext.lower()] = parser_class
            cls._instances[ext.lower()] = instance
        return parser_class
    
    @classmethod
    def get_parser(cls, file_path: str) -> BaseParser:
        """
        根据文件路径获取对应的解析器实例
        
        Args:
            file_path: 文件路径
        
        Returns:
            解析器实例
        
        Raises:
            ValueError: 如果找不到支持的解析器
        """
        ext = file_path[file_path.rfind('.'):].lower()
        
        if ext not in cls._instances:
            raise ValueError(
                f"No parser registered for file extension '{ext}'. "
                f"Supported extensions: {list(cls._parsers.keys())}"
            )
        
        return cls._instances[ext]
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """
        获取所有支持的扩展名
        
        Returns:
            扩展名列表
        """
        return list(cls._parsers.keys())
    
    @classmethod
    def list_parsers(cls) -> Dict[str, str]:
        """
        列出所有已注册的解析器
        
        Returns:
            扩展名到解析器类的映射
        """
        return {ext: cls._parsers[ext].__name__ for ext in cls._parsers}


# 全局注册表实例
_registry = ParserRegistry()


def register_parser(parser_class: Type[BaseParser]) -> Type[BaseParser]:
    """
    注册解析器类（便捷函数）
    
    Args:
        parser_class: 解析器类
    
    Returns:
        解析器类本身
    """
    return _registry.register(parser_class)


def get_parser(file_path: str) -> BaseParser:
    """
    获取解析器实例（便捷函数）
    
    Args:
        file_path: 文件路径
    
    Returns:
        解析器实例
    
    Raises:
        ValueError: 如果找不到支持的解析器
    """
    return _registry.get_parser(file_path)


def get_supported_parsers() -> List[str]:
    """
    获取支持的扩展名列表（便捷函数）
    
    Returns:
        扩展名列表
    """
    return _registry.get_supported_extensions()


def list_parsers() -> Dict[str, str]:
    """
    列出所有已注册的解析器（便捷函数）
    
    Returns:
        扩展名到解析器类的映射
    """
    return _registry.list_parsers()
