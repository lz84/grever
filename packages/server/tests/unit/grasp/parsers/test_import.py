"""
Test basic parser import
"""
import pytest
import tempfile
import os

from grasp.parser import get_parser


def test_basic_parser_import():
    """Test basic parser import"""
    parser = get_parser('test.md')
    print(f"Parser: {parser}")


def test_supported_extensions():
    """Test supported extensions"""
    parser = get_parser('test.md')
    extensions = parser.supported_extensions()
    print(f"Supported extensions: {extensions}")


def test_parsing_simple_file():
    """Test parsing with a simple test file"""
    test_content = """# Test Title

This is a test content.
"""

    # Create temporary test file
    fd, path = tempfile.mkstemp(suffix='.md')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # Parse the file
        parser = get_parser(path)
        entries = parser.parse(path)
        
        # Verify parsing
        assert len(entries) > 0
        assert entries[0].title == "Test Title"
        assert "This is a test content" in entries[0].content
        
        print("All tests passed!")
    finally:
        os.remove(path)