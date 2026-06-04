"""
Markdown 文档解析器
解析 .md 文件，提取结构化认知条目
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from .base import BaseParser, CognitiveEntry


@dataclass
class FrontMatter:
    """Markdown front-matter 数据"""
    format: str  # yaml, toml, json
    data: Dict[str, Any]


class MDParser(BaseParser):
    """
    Markdown 文档解析器
    
    支持的解析功能：
    - 多级标题识别（# ## ### ...）
    - 代码块提取（带语言标注）
    - 表格解析并结构化
    - 列表解析（有序/无序）
    - Front-matter 提取
    - 非内容过滤（图片链接等）
    """
    
    SUPPORTED_EXTENSIONS = ['.md', '.markdown']
    
    # 正则表达式模式
    FRONT_MATTER_PATTERN = re.compile(
        r'^-{3}\s*\n(.*?)\n-{3}\s*\n',
        re.DOTALL
    )
    
    HEADING_PATTERN = re.compile(
        r'^(#{1,6})\s+(.+?)\s*$',
        re.MULTILINE
    )
    
    CODE_BLOCK_PATTERN = re.compile(
        r'```(\w*)\n(.*?)```',
        re.DOTALL
    )
    
    TABLE_PATTERN = re.compile(
        r'^(\|.*?\|)\n(\|.*?\|)\n((?:\|.+\|\n?)+)',
        re.MULTILINE
    )
    
    LIST_PATTERN = re.compile(
        r'^[\s]*([-*+]\s+|\d+\.[\s]+)(.+)$',
        re.MULTILINE
    )
    
    def supported_extensions(self) -> List[str]:
        """返回支持的扩展名"""
        return self.SUPPORTED_EXTENSIONS
    
    def parse(self, file_path: str) -> List[CognitiveEntry]:
        """
        解析 Markdown 文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            CognitiveEntry 列表
        """
        path = Path(file_path)
        content = path.read_text(encoding='utf-8')
        
        # 提取 front-matter
        front_matter = self._extract_front_matter(content)
        
        # 移除 front-matter 获取正文
        body_content = self._remove_front_matter(content, front_matter)
        
        # 解析文档结构
        sections = self._parse_sections(body_content)
        
        # 生成认知条目
        entries = []
        for section in sections:
            entry = self._create_entry(section, str(path), front_matter)
            if entry:
                entries.append(entry)
        
        return entries
    
    def _extract_front_matter(self, content: str) -> Optional[FrontMatter]:
        """
        提取 front-matter
        
        Args:
            content: 文件内容
        
        Returns:
            FrontMatter 对象或 None
        """
        match = self.FRONT_MATTER_PATTERN.match(content)
        if not match:
            return None
        
        fm_content = match.group(1).strip()
        
        # 简单的 YAML 格式检测
        if fm_content.startswith('title:') or 'title' in fm_content:
            return FrontMatter(format='yaml', data=self._parse_yaml(fm_content))
        elif fm_content.startswith('{"') or 'title' in fm_content and '":' in fm_content:
            import json
            try:
                return FrontMatter(format='json', data=json.loads(fm_content))
            except:
                return FrontMatter(format='yaml', data=self._parse_yaml(fm_content))
        
        return FrontMatter(format='yaml', data=self._parse_yaml(fm_content))
    
    def _remove_front_matter(self, content: str, front_matter: Optional[FrontMatter]) -> str:
        """移除 front-matter"""
        if front_matter:
            match = self.FRONT_MATTER_PATTERN.match(content)
            if match:
                return content[match.end():]
        return content
    
    def _parse_yaml(self, yaml_content: str) -> Dict[str, Any]:
        """简单的 YAML 解析器"""
        result = {}
        current_list_key = None
        
        for line in yaml_content.split('\n'):
            # 跳过空行和注释
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            # 处理列表项
            if line.strip().startswith('- '):
                if current_list_key:
                    if current_list_key not in result:
                        result[current_list_key] = []
                    item = line.strip()[2:].strip().strip('"').strip("'")
                    result[current_list_key].append(item)
                continue
            
            # 处理单行数组格式：tags: [python, tutorial, example]
            if ': [' in line:
                key, _, value = line.partition(':')
                key = key.strip()
                # 提取方括号内的内容
                match = re.search(r'\[(.*?)\]', value)
                if match:
                    array_content = match.group(1)
                    items = [item.strip().strip('"').strip("'") for item in array_content.split(',')]
                    result[key] = items
                continue
            
            # 处理键值对
            if ':' in line:
                current_list_key = None
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip()
                
                # 处理空值
                if value == '' or value == '~' or value == '""' or value == "''":
                    result[key] = None
                # 处理布尔值
                elif value.lower() == 'true':
                    result[key] = True
                elif value.lower() == 'false':
                    result[key] = False
                # 处理数字
                elif value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                    result[key] = int(value)
                else:
                    # 去除引号
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    result[key] = value
        
        return result
    
    def _parse_sections(self, content: str) -> List[Dict[str, Any]]:
        """
        解析文档为章节列表
        
        Returns:
            章节列表，每个章节包含标题、内容、类型等信息
        """
        sections = []
        current_section = None
        current_heading = None
        content_buffer = []
        in_code_block = False
        in_table = False
        
        lines = content.split('\n')
        
        for line in lines:
            # 检测代码块开始
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                content_buffer.append(line)
                continue
            
            # 检测表格开始和结束
            if re.match(r'^\|', line) and '|-' not in line and in_code_block is False:
                if not in_table:
                    in_table = True
                content_buffer.append(line)
                continue
            elif in_table and (not re.match(r'^\|', line) or line.strip() == ''):
                in_table = False
            
            if in_table:
                content_buffer.append(line)
                continue
            
            # 检测标题
            heading_match = self.HEADING_PATTERN.match(line)
            if heading_match and not in_code_block:
                # 保存之前的章节
                if current_section:
                    current_section['content'] = '\n'.join(content_buffer).strip()
                    sections.append(current_section)
                
                # 开始新章节
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                current_section = {
                    'level': level,
                    'title': title,
                    'content': '',
                    'code_blocks': [],
                    'tables': [],
                    'lists': [],
                }
                current_heading = heading_match
                content_buffer = []
                continue
            
            # 收集内容
            if current_section and not in_code_block:
                content_buffer.append(line)
            elif in_code_block:
                content_buffer.append(line)
        
        # 保存最后一章
        if current_section:
            current_section['content'] = '\n'.join(content_buffer).strip()
            sections.append(current_section)
        
        # 后处理：提取代码块、表格、列表
        for section in sections:
            self._extract_elements(section)
        
        return sections
    
    def _extract_elements(self, section: Dict[str, Any]):
        """提取代码块、表格、列表等元素"""
        content = section['content']
        
        # 提取代码块
        code_blocks = []
        for match in self.CODE_BLOCK_PATTERN.finditer(content):
            lang = match.group(1).strip() or 'text'
            code = match.group(2).strip()
            code_blocks.append({
                'language': lang,
                'code': code,
            })
        
        # 清理代码块占位符
        content = self.CODE_BLOCK_PATTERN.sub('', content)
        
        # 提取表格
        tables = []
        for match in self.TABLE_PATTERN.finditer(content):
            header_line = match.group(1).strip()
            separator_line = match.group(2).strip()
            rows_str = match.group(3).strip()
            
            # 解析表头
            header = [cell.strip() for cell in header_line.split('|')[1:-1]]
            
            rows = []
            for row in rows_str.strip().split('\n'):
                row = row.strip()
                if row and row.startswith('|') and row.endswith('|'):
                    cells = [cell.strip() for cell in row.split('|')[1:-1]]
                    if cells:
                        rows.append(cells)
            
            if rows:
                tables.append({
                    'header': header,
                    'rows': rows,
                })
        
        # 清理表格占位符
        content = self.TABLE_PATTERN.sub('', content)
        
        # 提取列表
        lists = []
        for match in self.LIST_PATTERN.finditer(content):
            bullet = match.group(1).strip()
            item = match.group(2).strip()
            lists.append({
                'type': 'ordered' if bullet[0].isdigit() else 'unordered',
                'marker': bullet,
                'content': item,
            })
        
        # 清理列表占位符
        content = self.LIST_PATTERN.sub('', content)
        
        # 更新章节信息
        section['code_blocks'] = code_blocks
        section['tables'] = tables
        section['lists'] = lists
        section['content'] = content.strip()
        
        # 保留原始内容中的代码块和表格信息用于验证
        # 如果没有内容但有代码块/表格，保留原始文本
        if not section['content'].strip() and (code_blocks or tables or lists):
            # 如果有代码块、表格或列表，说明这是有价值的内容
            section['has_elements'] = True
    
    def _create_entry(self, section: Dict[str, Any], source_doc: str, 
                      front_matter: Optional[FrontMatter]) -> Optional[CognitiveEntry]:
        """
        从章节创建认知条目
        
        Args:
            section: 章节数据
            source_doc: 源文档路径
            front_matter: front-matter 数据
        
        Returns:
            CognitiveEntry 或 None
        """
        title = section.get('title', 'Untitled')
        content = section.get('content', '')
        
        # 检查是否有有效元素（代码块、表格、列表）
        has_elements = section.get('has_elements', False) or \
                      section.get('code_blocks') or \
                      section.get('tables') or \
                      section.get('lists')
        
        # 跳过完全空的章节
        if not content and not has_elements:
            return None
        
        # 跳过纯列表或纯图片章节（低价值内容）
        if self._is_low_value_content(section):
            return None
        
        # 确定条目类型
        entry_type = self._determine_entry_type(section, front_matter)
        
        # 提取标签
        tags = self._extract_tags(section, front_matter)
        
        # 计算置信度
        confidence = self._calculate_confidence(section, content)
        
        return CognitiveEntry(
            title=title,
            content=content,
            entry_type=entry_type,
            source_doc=source_doc,
            source_section=self._get_section_path(section),
            tags=tags,
            confidence=confidence,
            metadata={
                'heading_level': section.get('level', 1),
                'has_code': len(section.get('code_blocks', [])) > 0,
                'has_table': len(section.get('tables', [])) > 0,
                'code_blocks': section.get('code_blocks', []),
                'tables': section.get('tables', []),
            },
        )
    
    def _is_low_value_content(self, section: Dict[str, Any]) -> bool:
        """判断是否为低价值内容"""
        content = section.get('content', '').strip()
        
        # 如果有代码块、表格或列表，说明是有效内容
        if section.get('code_blocks') or section.get('tables') or section.get('lists'):
            return False
        
        # 空内容
        if not content:
            return True
        
        # 过滤纯占位符内容
        if re.match(r'^[.\s]+$', content):
            return True
        
        return False
    
    def _determine_entry_type(self, section: Dict[str, Any], 
                              front_matter: Optional[FrontMatter]) -> str:
        """
        确定条目类型
        
        Returns:
            'concept', 'procedure', 'policy', 或 'example'
        """
        title_lower = section.get('title', '').lower()
        content = section.get('content', '').lower()
        
        # 通过标题关键词判断
        if any(kw in title_lower for kw in ['示例', 'example', '演示', 'demo']):
            return 'example'
        
        if any(kw in title_lower for kw in ['流程', '步骤', '如何', 'procedure', 'guide']):
            return 'procedure'
        
        if any(kw in title_lower for kw in ['规范', '规则', 'policy', '标准']):
            return 'policy'
        
        # 如果有代码块，很可能是示例
        if section.get('code_blocks'):
            return 'example'
        
        # 默认是概念
        return 'concept'
    
    def _extract_tags(self, section: Dict[str, Any], 
                      front_matter: Optional[FrontMatter]) -> List[str]:
        """提取标签"""
        tags = []
        
        # 从 front-matter 提取
        if front_matter and front_matter.data:
            fm_tags = front_matter.data.get('tags', [])
            if isinstance(fm_tags, list):
                tags.extend(fm_tags)
            elif isinstance(fm_tags, str):
                # 处理多种格式：[python, tutorial, example] 或 python, tutorial, example
                fm_tags = fm_tags.strip('[]')  # 移除方括号
                tags.extend([t.strip().strip('"').strip("'") for t in fm_tags.split(',')])
        
        # 从标题提取（可选）
        title = section.get('title', '')
        # 可以添加更多标签提取逻辑
        
        return list(set(tags))  # 去重
    
    def _calculate_confidence(self, section: Dict[str, Any], content: str) -> float:
        """
        计算置信度
        
        Returns:
            0-1 之间的置信度分数
        """
        confidence = 0.8  # 基础置信度
        
        # 内容长度奖励
        if len(content) > 100:
            confidence += 0.1
        elif len(content) < 20:
            confidence -= 0.1
        
        # 有代码块奖励
        if section.get('code_blocks'):
            confidence += 0.05
        
        # 有表格奖励
        if section.get('tables'):
            confidence += 0.05
        
        # 限制在 0-1 范围内
        return max(0.0, min(1.0, confidence))
    
    def _get_section_path(self, section: Dict[str, Any]) -> str:
        """获取章节路径（层级路径）"""
        level = section.get('level', 1)
        title = section.get('title', '')
        return f'{"#" * level} {title}'
