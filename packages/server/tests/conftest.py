"""
Pytest configuration and fixtures
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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

# Insert mock before any imports
sys.modules['grever'] = MockGrever()
sys.modules['grever.common'] = MockGreverCommon()
sys.modules['grever.common.exceptions'] = MockGreverCommonExceptions()


# Increase recursion limit for deep import chains
import sys
if sys.getrecursionlimit() < 2000:
    sys.setrecursionlimit(2000)
