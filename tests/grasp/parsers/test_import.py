"""
Test basic parser import
"""

from src.grasp.parsers import get_parser

# Test basic import
parser = get_parser('test.md')
print(f"Parser: {parser}")

# Test supported extensions
extensions = parser.supported_extensions()
print(f"Supported extensions: {extensions}")

# Test parsing (with a simple test file)
import tempfile
import os

test_content = """# Test Title

This is a test content.
"""

# Create temporary test file
fd, path = tempfile.mkstemp(suffix='.md')
try:
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    # Parse the file
    entries = parser.parse(path)
    
    # Verify parsing
    assert len(entries) > 0
    assert entries[0].title == "Test Title"
    assert "This is a test content" in entries[0].content
    
    print("All tests passed!")
finally:
    os.remove(path)
