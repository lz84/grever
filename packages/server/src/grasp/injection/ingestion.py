"""
文档解析器注入入口
将解析器输出的条目注入到 Grasp 知识库
"""

from typing import List, Dict
from grasp.parser import get_parser, get_supported_parsers
from grasp.parser.base import CognitiveEntry
from grasp.analysis.cognitive_extractor import extract_cognitions
from grasp.common.service import GraspService


class DocumentIngestion:
    """
    文档注入器
    
    提供从文档解析到知识库注入的完整流程
    """
    
    def __init__(self, service: GraspService):
        """
        初始化注入器
        
        Args:
            service: GraspService 实例
        """
        self.service = service
        
    def ingest(self, file_path: str) -> List[str]:
        """
        注入文档到知识库
        
        Args:
            file_path: 文档路径
        
        Returns:
            注入成功的认知 ID 列表
        """
        # 获取解析器
        parser = get_parser(file_path)
        
        # 解析文档
        entries = parser.parse(file_path)
        
        # 提取认知条目
        cognition_inputs = extract_cognitions(entries, self.service)
        
        # 注入到知识库
        cognition_ids = []
        for cognition_input in cognition_inputs:
            result = self.service.inject(cognition_input)
            cognition_ids.append(result.cognition_id)
        
        return cognition_ids
    
    def ingest_many(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        批量注入文档
        
        Args:
            file_paths: 文档路径列表
        
        Returns:
            每个文件对应的认知 ID 列表
        """
        results = {}
        
        for file_path in file_paths:
            try:
                cognition_ids = self.ingest(file_path)
                results[file_path] = cognition_ids
            except Exception as e:
                results[file_path] = []
                print(f"Failed to ingest {file_path}: {str(e)}")
        
        return results

def ingest_document(file_path: str, service: GraspService) -> List[str]:
    """
    便捷函数：注入单个文档
    
    Args:
        file_path: 文档路径
        service: GraspService 实例
    
    Returns:
        注入成功的认知 ID 列表
    """
    ingestion = DocumentIngestion(service)
    return ingestion.ingest(file_path)

def ingest_documents(file_paths: List[str], service: GraspService) -> Dict[str, List[str]]:
    """
    便捷函数：批量注入文档
    
    Args:
        file_paths: 文档路径列表
        service: GraspService 实例
    
    Returns:
        每个文件对应的认知 ID 列表
    """
    ingestion = DocumentIngestion(service)
    return ingestion.ingest_many(file_paths)
