"""
Nexus 统一异常处理模块
"""

from .exceptions import (
    NexusException,
    BusinessException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    RateLimitException,
    DatabaseException,
    ErrorCode,
)

__all__ = [
    'NexusException',
    'BusinessException',
    'ValidationException',
    'AuthenticationException',
    'AuthorizationException',
    'NotFoundException',
    'RateLimitException',
    'DatabaseException',
    'ErrorCode',
]
