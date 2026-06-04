"""
Markdown parser tests
"""

import pytest
import os
from src.grasp.parser.md_parser import MDParser
from src.grasp.parser.base import CognitiveEntry


# Import test fixtures
from .conftest import create_test_md, teardown_test_md


class TestMDParserSupportedExtensions:
    """Test MDParser supported extensions"""
    
    def test_supported_extensions(self):
        """测试支持的扩展名"""
        parser = MDParser()
        extensions = parser.supported_extensions()
        
        assert '.md' in extensions
        assert '.markdown' in extensions


class TestParseHeadings:
    """Test heading parsing"""
    
    def test_parse_single_heading(self, tmp_path):
        """测试单个标题解析"""
        content = """# Introduction

This is the introduction section.
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) >= 1
            assert entries[0].title == "Introduction"
            assert "This is the introduction section" in entries[0].content
        finally:
            teardown_test_md(path)
    
    def test_parse_multi_level_headings(self, tmp_path):
        """测试多级标题解析"""
        content = """# Main Title

Main content here.

## Section One

Section one content.

### Subsection

Subsection content.

## Section Two

Section two content.
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            # Should have at least 4 entries (main + 3 sections)
            titles = [e.title for e in entries]
            assert "Main Title" in titles
            assert "Section One" in titles
            assert "Subsection" in titles
            assert "Section Two" in titles
        finally:
            teardown_test_md(path)
    
    def test_parse_headings_with_code(self, tmp_path):
        """测试标题中包含代码"""
        content = """# Getting Started

Install the package:

```bash
pip install mypackage
```

Now you can use it.
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) >= 1
            assert entries[0].title == "Getting Started"
            
            # Code is in metadata, not content (this is correct behavior)
            assert entries[0].entry_type == 'example'
            metadata = entries[0].metadata
            assert metadata['has_code'] == True
            assert len(metadata.get('code_blocks', [])) > 0
            assert metadata['code_blocks'][0]['code'] == 'pip install mypackage'
        finally:
            teardown_test_md(path)


class TestParseCodeBlocks:
    """Test code block parsing"""
    
    def test_parse_code_block(self, tmp_path):
        """测试代码块提取"""
        content = """# Python Example

Here's a Python function:

```python
def hello():
    print("Hello, World!")
```

That's it.
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) >= 1
            assert entries[0].title == "Python Example"
            
            # Check metadata has code blocks
            metadata = entries[0].metadata
            assert 'has_code' in metadata
            assert metadata['has_code'] == True
            assert len(metadata.get('code_blocks', [])) > 0
        finally:
            teardown_test_md(path)
    
    def test_parse_multiple_code_blocks(self, tmp_path):
        """测试多个代码块"""
        content = """# Multi-Language Examples

## Python

```python
print("Python")
```

## JavaScript

```javascript
console.log("JavaScript");
```

## Bash

```bash
echo "Bash"
```
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            # Find the multi-language entry
            for entry in entries:
                if entry.title == "Multi-Language Examples":
                    metadata = entry.metadata
                    code_blocks = metadata.get('code_blocks', [])
                    assert len(code_blocks) >= 2
                    break
        finally:
            teardown_test_md(path)
    
    def test_parse_code_block_without_language(self, tmp_path):
        """测试不带语言标注的代码块"""
        content = """# Example

```
def no_lang():
    pass
```
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) >= 1
            # Default language should be 'text'
            metadata = entries[0].metadata
            code_blocks = metadata.get('code_blocks', [])
            if code_blocks:
                assert code_blocks[0]['language'] == 'text'
        finally:
            teardown_test_md(path)


class TestParseTables:
    """Test table parsing"""
    
    def test_parse_simple_table(self, tmp_path):
        """测试简单表格解析"""
        content = """# Data Table

| Name | Age | City |
|------|-----|------|
| Alice | 25 | Beijing |
| Bob | 30 | Shanghai |
| Charlie | 35 | Guangzhou |
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) >= 1
            assert entries[0].title == "Data Table"
            
            # Check metadata has tables
            metadata = entries[0].metadata
            assert 'has_table' in metadata
            assert metadata['has_table'] == True
            
            tables = metadata.get('tables', [])
            assert len(tables) > 0
            assert tables[0]['header'] == ['Name', 'Age', 'City']
            assert len(tables[0]['rows']) == 3
        finally:
            teardown_test_md(path)
    
    def test_parse_empty_table(self, tmp_path):
        """测试空表格"""
        content = """# Empty Table

| Col1 | Col2 |
|------|------|
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            # Empty table should still create an entry
            assert len(entries) >= 1
        finally:
            teardown_test_md(path)


class TestParseLists:
    """Test list parsing"""
    
    def test_parse_unordered_list(self, tmp_path):
        """测试无序列表"""
        content = """# Features

- Feature one
- Feature two
- Feature three
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) >= 1
            assert entries[0].title == "Features"
        finally:
            teardown_test_md(path)
    
    def test_parse_ordered_list(self, tmp_path):
        """测试有序列表"""
        content = """# Steps

1. First step
2. Second step
3. Third step
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) >= 1
            assert entries[0].title == "Steps"
        finally:
            teardown_test_md(path)
    
    def test_parse_mixed_lists(self, tmp_path):
        """测试混合列表"""
        content = """# Items

- Unordered item 1
1. Ordered item 1
- Unordered item 2
2. Ordered item 2
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) >= 1
            assert entries[0].title == "Items"
        finally:
            teardown_test_md(path)


class TestParserRegistration:
    """Test parser registration"""
    
    def test_parser_registration_success(self, tmp_path):
        """测试注册机制"""
        from src.grasp.parser.registry import ParserRegistry, get_parser
        from src.grasp.parser.md_parser import MDParser
        
        # Clear any existing parsers
        ParserRegistry._parsers.clear()
        ParserRegistry._instances.clear()
        
        # Register MDParser manually (mock blocks auto-registration in __init__.py)
        ParserRegistry.register(MDParser)
        
        # Check MDParser is registered
        assert '.md' in ParserRegistry._parsers
        assert ParserRegistry._parsers['.md'] == MDParser
        
        # Test get_parser
        parser = get_parser('test.md')
        assert isinstance(parser, MDParser)
    
    def test_entry_type_detection(self, tmp_path):
        """测试条目类型检测"""
        # Test concept type
        concept_content = """# Machine Learning

Machine learning is a subset of AI.
"""
        path = create_test_md(concept_content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) > 0
            assert entries[0].entry_type == 'concept'
        finally:
            teardown_test_md(path)
        
        # Test example type (has code block)
        example_content = """# Python Example

```python
print("Hello")
```
"""
        path = create_test_md(example_content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) > 0
            assert entries[0].entry_type == 'example'
        finally:
            teardown_test_md(path)


class TestCognitiveEntryExtraction:
    """Test CognitiveEntry field extraction"""
    
    def test_source_doc_extraction(self, tmp_path):
        """测试来源文档提取"""
        content = """# Test

Content here.
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) > 0
            assert entries[0].source_doc == path
        finally:
            teardown_test_md(path)
    
    def test_confidence_calculation(self, tmp_path):
        """测试置信度计算"""
        # Short content
        short_content = """# Short

Hi.
"""
        path = create_test_md(short_content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) > 0
            # Should have lower confidence due to short content
            assert entries[0].confidence < 0.9
        finally:
            teardown_test_md(path)
        
        # Long content
        long_content = """# Long

This is a much longer content with more text to make it substantial.
We have multiple paragraphs and various sections.
This should give a higher confidence score.
"""
        path = create_test_md(long_content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) > 0
            # Should have higher confidence due to longer content
            assert entries[0].confidence >= 0.9
        finally:
            teardown_test_md(path)
    
    def test_tags_extraction(self, tmp_path):
        """测试标签提取"""
        content = """---
title: Test Document
tags: [python, tutorial, example]
---

# Python Tutorial

Learn Python basics.
"""
        path = create_test_md(content)
        try:
            parser = MDParser()
            entries = parser.parse(path)
            
            assert len(entries) > 0
            # Tags should be extracted from front-matter
            assert 'python' in entries[0].tags
            assert 'tutorial' in entries[0].tags
        finally:
            teardown_test_md(path)
