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

# Temporarily mock the grever module before any imports
class MockGreverException(Exception):
    pass

class MockErrorCode:
    pass

class MockGreverCommonExceptions:
    GreverException = MockGreverException
    ErrorCode = MockErrorCode

class MockGreverCommon:
    exceptions = MockGreverCommonExceptions

class MockGrever:
    common = MockGreverCommon

sys.modules['grever'] = MockGrever()
sys.modules['grever.common'] = MockGreverCommon()
sys.modules['grever.common.exceptions'] = MockGreverCommonExceptions()
