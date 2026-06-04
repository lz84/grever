"""
认知条目提取逻辑
将解析器输出的条目转换为Grasp系统可接受的格式
"""

from typing import List, Dict, Any
from grasp.parser.base import CognitiveEntry
from grasp.common.models import CognitionInput, CognitionType, SourceInfo
from grasp.common.service import GraspService


class CognitiveExtractor:
    """
    认知条目提取器
    
    将解析器输出的 CognitiveEntry 转换为 Grasp 系统可接受的 CognitionInput
    """
    
    def __init__(self, service: GraspService):
        """
        初始化提取器
        
        Args:
            service: GraspService 实例
        """
        self.service = service
        
    def extract(self, entries: List[CognitiveEntry]) -> List[CognitionInput]:
        """
        提取认知条目
        
        Args:
            entries: CognitiveEntry 列表
        
        Returns:
            CognitionInput 列表
        """
        cognition_inputs = []
        
        for entry in entries:
            # 确定认知类型
            cognition_type = self._determine_cognition_type(entry)
            
            # 创建来源信息
            source = SourceInfo(
                agent_id="grasp-parser",
                task_id="parse-document",
                channel="file",
            )
            
            # 创建认知输入
            cognition_input = CognitionInput(
                type=cognition_type,
                content=entry.content,
                source=source,
                tags=entry.tags,
                confidence=entry.confidence,
                metadata=entry.metadata,
            )
            
            cognition_inputs.append(cognition_input)
        
        return cognition_inputs
    
    def _determine_cognition_type(self, entry: CognitiveEntry) -> CognitionType:
        """
        根据条目类型确定认知类型
        
        Args:
            entry: CognitiveEntry
        
        Returns:
            CognitionType
        """
        # 映射条目类型到认知类型
        type_mapping = {
            'concept': CognitionType.FACT,
            'procedure': CognitionType.PATTERN,
            'policy': CognitionType.PATTERN,
            'example': CognitionType.LESSON,
        }
        
        # 如果没有匹配的类型，使用默认的 FACT
        return type_mapping.get(entry.entry_type, CognitionType.FACT)


def extract_cognitions(entries: List[CognitiveEntry], service: GraspService) -> List[CognitionInput]:
    """
    便捷函数：提取认知条目
    
    Args:
        entries: CognitiveEntry 列表
        service: GraspService 实例
    
    Returns:
        CognitionInput 列表
    """
    extractor = CognitiveExtractor(service)
    return extractor.extract(entries)
