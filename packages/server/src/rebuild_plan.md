"""优化 task_recoverer.py - 提取 build_dispatch_retry_context 函数到独立文件"""
# 重构 plan:
# 1. build_dispatch_retry_context 函数 (用于重派任务的 DP-1 上下文构建)
# 2. TaskRecoverer 类保持原样

# 新文件名：task_dispatch_retry_context.py
# 职责：专门构建 DP-1 重派任务的上下文
