"""
Pytest configuration - set recursion limit and path early
"""
import sys
import os

# Set recursion limit early for deep import chains
if sys.getrecursionlimit() < 3000:
    sys.setrecursionlimit(3000)

# Add src to path
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Temporarily mock the nexus module before any imports
class MockNexusException(Exception):
    pass

class MockErrorCode:
    pass

class MockNexusCommonExceptions:
    NexusException = MockNexusException
    ErrorCode = MockErrorCode

class MockNexusCommon:
    exceptions = MockNexusCommonExceptions

class MockNexus:
    common = MockNexusCommon

sys.modules['nexus'] = MockNexus()
sys.modules['nexus.common'] = MockNexusCommon()
sys.modules['nexus.common.exceptions'] = MockNexusCommonExceptions()
