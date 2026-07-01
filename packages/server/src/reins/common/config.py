"""
Grever 系统配置

所有魔法数字必须定义在这里，支持环境变量覆盖。
"""

import os

# ============== 调度器配置 ==============
TICK_INTERVAL = int(os.getenv("GREVER_TICK_INTERVAL", "30"))  # 调度循环间隔（秒）
STALE_THRESHOLD = int(os.getenv("NEXUS_STALE_THRESHOLD", "300"))  # 任务 stale 阈值（秒，5分钟）
OFFLINE_THRESHOLD = int(os.getenv("NEXUS_OFFLINE_THRESHOLD", "900"))  # Agent 离线阈值（秒，15分钟）

# ============== 验证配置 ==============
MAX_VERIFICATION_CYCLES = int(os.getenv("NEXUS_MAX_VERIFICATION_CYCLES", "3"))  # 最大验证循环次数

# ============== 任务配置 ==============
DEFAULT_MAX_RETRIES = int(os.getenv("NEXUS_DEFAULT_MAX_RETRIES", "3"))  # 默认最大重试次数
TASK_TIMEOUT_MINUTES = int(os.getenv("NEXUS_TASK_TIMEOUT_MINUTES", "60"))  # 任务超时（分钟，2026-05-24 从 30→60）

# ============== 分页配置 ==============
DEFAULT_PAGE_SIZE = int(os.getenv("NEXUS_DEFAULT_PAGE_SIZE", "50"))  # 默认分页大小
MAX_PAGE_SIZE = int(os.getenv("NEXUS_MAX_PAGE_SIZE", "200"))  # 最大分页大小

# ============== 数据库配置 ==============
DB_BACKUP_DIR = os.getenv("NEXUS_DB_BACKUP_DIR", "data/backups")  # 备份目录
DB_BACKUP_KEEP_DAYS = int(os.getenv("NEXUS_DB_BACKUP_KEEP_DAYS", "30"))  # 备份保留天数

# ============== 日志配置 ==============
LOG_DIR = os.getenv("NEXUS_LOG_DIR", "logs")  # 日志目录
LOG_RETENTION_DAYS = int(os.getenv("NEXUS_LOG_RETENTION_DAYS", "30"))  # 日志保留天数

# ============== 健康检查配置 ==============
HEALTH_CHECK_INTERVAL = int(os.getenv("NEXUS_HEALTH_CHECK_INTERVAL", "60"))  # 健康检查间隔（秒）

# ============== 结果数据截断长度 ==============
MAX_CONTEXT_MD = int(os.getenv("NEXUS_MAX_CONTEXT_MD", "8000"))      # 执行上下文，供 Agent 参考
MAX_RESULT_SUMMARY = int(os.getenv("NEXUS_MAX_RESULT_SUMMARY", "2000"))   # 结果摘要，供验证器检查
MAX_RESULT_DETAIL = int(os.getenv("NEXUS_MAX_RESULT_DETAIL", "4000"))    # 结果详情，供人工查阅

# ============== 旧版 ReinsConfig（兼容 llm_service.py）=============
class ReinsConfig:
    """兼容旧版 LLM 配置的 ReinsConfig 类"""
    def __init__(self):
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.llm_model = os.getenv("LLM_MODEL", "qwen-plus")
