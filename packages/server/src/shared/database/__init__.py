"""
Grever 数据库连接池模块
"""

from .pool import (
    ConnectionPool,
    PoolConfig,
    PoolMetrics,
    PooledConnection,
    create_pool,
    get_pool,
)
from .context import (
    PoolContext,
    acquire_connection,
)
from .models import (
    Base,
    Cognition,
    Task,
    SubTask,
    ExecutionLog,
    Workflow,
    WorkflowStep,
)
from .models_trace import (
    TraceEvent,
    TraceReport,
)

# Import from session (after models to avoid circular imports)
try:
    from .session import (
        get_database_manager,
        get_db_session,
        DatabaseSessionManager,
    )
except ImportError:
    get_database_manager = None
    get_db_session = None
    DatabaseSessionManager = None

__all__ = [
    'ConnectionPool',
    'PoolConfig',
    'PoolMetrics',
    'PooledConnection',
    'create_pool',
    'get_pool',
    'PoolContext',
    'acquire_connection',
    'Base',
    'Cognition',
    'Task',
    'SubTask',
    'ExecutionLog',
    'Workflow',
    'WorkflowStep',
    'TraceEvent',
    'TraceReport',
    'get_database_manager',
    'get_db_session',
    'DatabaseSessionManager',
]

# Aliases for backwards compatibility
get_db = get_db_session
get_db_manager = get_database_manager
