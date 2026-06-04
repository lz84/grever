# Phase 4: 真正代码执行

> Agent Worker 从"模拟执行"升级为"真正写代码"

## 方案

### 执行流程

```
Worker 领任务 → 构造 Claude Code prompt → spawn claude subprocess → 等待完成 → 上报结果
```

### Claude Code 调用方式

```bash
cd D:\work\research\agents-nexus && claude --permission-mode bypassPermissions --print "<任务描述>"
```

### 修改点

**文件**: `scripts/agent_worker.py`

1. 重写 `execute_task()` 方法：
   - 将任务标题 + 描述转为 Claude Code prompt
   - 在 Nexus 目录 spawn `claude --print --permission-mode bypassPermissions`
   - 捕获 stdout/stderr
   - 返回 (success, result_message)

2. 增加超时控制：
   - 单任务最长 10 分钟
   - 超时后 kill subprocess，返回失败

3. 增加 git commit 自动提交：
   - 子代理完成后执行 `git add -A && git commit -m "[worker] {task_title}"`

### 验证标准

1. Worker 领到 task 后真正写代码
2. git commit 出现在 Nexus 仓库
3. Nexus 任务状态 done

## 任务清单

| # | 内容 | 说明 |
|---|------|------|
| 1 | 重写 execute_task() | Claude Code subprocess 调用 |
| 2 | 超时控制 | 10 分钟 kill |
| 3 | 自动 git commit | 子代理完成后提交 |
| 4 | 端到端测试 | 创建测试任务 → Worker 执行 → 代码入库 |
