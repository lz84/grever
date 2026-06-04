"""
超时任务调度器

提供定时执行超时检测的功能
定期扫描处于 waiting_human 状态的任务并处理超时
"""

import threading
import time
from loguru import logger
from datetime import datetime
from typing import Optional
import atexit

from services.timeout_handler import handle_timeouts

class TimeoutScheduler:
    """超时任务调度器类"""
    
    def __init__(self, interval_minutes: int = 60):
        """
        初始化超时调度器
        
        Args:
            interval_minutes: 检查间隔（分钟），默认60分钟
        """
        self.interval_seconds = interval_minutes * 60
        self.timer: Optional[threading.Timer] = None
        self.is_running = False
        self.lock = threading.Lock()
    
    def _run(self):
        """执行超时检查的内部方法"""
        try:
            if self.is_running:
                logger.info("开始执行超时任务检查...")
                
                # 执行超时处理
                result = handle_timeouts()
                
                logger.info(f"超时任务检查完成: {result}")
                
                # 重新启动定时器
                self.start()
                
        except Exception as e:
            logger.error(f"执行超时任务检查时出现错误: {e}")
            # 即使出错也要重新启动定时器
            if self.is_running:
                self.start()
    
    def start(self):
        """启动定时器"""
        with self.lock:
            if not self.is_running:
                self.is_running = True
                self.timer = threading.Timer(self.interval_seconds, self._run)
                self.timer.daemon = True  # 设置为守护线程
                self.timer.start()
                logger.info(f"超时任务调度器已启动，检查间隔: {self.interval_seconds} 秒")
    
    def stop(self):
        """停止定时器"""
        with self.lock:
            self.is_running = False
            if self.timer:
                self.timer.cancel()
                self.timer = None
            logger.info("超时任务调度器已停止")

# 全局调度器实例
_timeout_scheduler = None

def get_timeout_scheduler() -> TimeoutScheduler:
    """
    获取超时调度器实例
    """
    global _timeout_scheduler
    
    if _timeout_scheduler is None:
        import os
        interval_minutes = int(os.getenv("TIMEOUT_CHECK_INTERVAL_MINUTES", "60"))
        _timeout_scheduler = TimeoutScheduler(interval_minutes=interval_minutes)
    
    return _timeout_scheduler

def start_timeout_scheduler():
    """
    启动超时调度器
    """
    scheduler = get_timeout_scheduler()
    scheduler.start()
    
    # 注册程序退出时的清理函数
    atexit.register(stop_timeout_scheduler)

def stop_timeout_scheduler():
    """
    停止超时调度器
    """
    global _timeout_scheduler
    
    if _timeout_scheduler:
        _timeout_scheduler.stop()
        _timeout_scheduler = None

def immediate_timeout_check():
    """
    立即执行一次超时检查
    """
    logger.info("立即执行超时任务检查...")
    result = handle_timeouts()
    logger.info(f"立即检查完成: {result}")
    return result

# 在模块加载时自动启动调度器（可选）
def _auto_start():
    """
    自动启动调度器（如果需要）
    """
    import os
    auto_start = os.getenv("AUTO_START_TIMEOUT_SCHEDULER", "true").lower() == "true"
    if auto_start:
        start_timeout_scheduler()

# 模块加载时执行自动启动
_auto_start()