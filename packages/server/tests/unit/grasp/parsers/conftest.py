"""
Test fixture to create test markdown files
"""

import tempfile
import os


def create_test_md(content, suffix='.md'):
    """Create a temporary markdown file with given content"""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        return path
    except:
        os.close(fd)
        raise


def teardown_test_md(path):
    """Clean up test file"""
    if os.path.exists(path):
        os.remove(path)
