"""
解析器基类和认知条目定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class CognitiveEntry:
    """
    认知条目 - 从文档解析提取的基本单元
    
    Attributes:
        title: 标题
        content: 正文内容
        entry_type: 类型 - concept(概念)/procedure(流程)/policy(规范)/example(示例)
        source_doc: 来源文档
        source_section: 来源章节
        tags: 标签列表
        confidence: 置信度 0-1
        metadata: 其他元数据
    """
    title: str
    content: str
    entry_type: str  # concept, procedure, policy, example
    source_doc: str
    source_section: str = ""
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'title': self.title,
            'content': self.content,
            'entry_type': self.entry_type,
            'source_doc': self.source_doc,
            'source_section': self.source_section,
            'tags': self.tags,
            'confidence': self.confidence,
            'metadata': self.metadata,
        }


class BaseParser(ABC):
    """
    解析器基类 - 定义文档解析器的统一接口
    
    所有文档解析器都应继承此类并实现核心方法
    """
    
    @abstractmethod
    def parse(self, file_path: str) -> List[CognitiveEntry]:
        """
        解析文档，返回认知条目列表
        
        Args:
            file_path: 文件路径
        
        Returns:
            CognitiveEntry 列表
        """
        pass
    
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """
        返回支持的扩展名列表
        
        Returns:
            扩展名列表，如 ['.md', '.markdown']
        """
        pass
    
    def can_parse(self, file_path: str) -> bool:
        """
        检查解析器是否能处理指定文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            是否支持解析
        """
        ext = self._get_extension(file_path).lower()
        return ext in [e.lower() for e in self.supported_extensions()]
    
    @staticmethod
    def _get_extension(file_path: str) -> str:
        """获取文件扩展名"""
        return file_path[file_path.rfind('.'):].lower()
