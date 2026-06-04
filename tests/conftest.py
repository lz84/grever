"""
Pytest configuration and fixtures
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

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

# Insert mock before any imports
sys.modules['nexus'] = MockNexus()
sys.modules['nexus.common'] = MockNexusCommon()
sys.modules['nexus.common.exceptions'] = MockNexusCommonExceptions()
