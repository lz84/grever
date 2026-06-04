// 冲突事件数据
export const conflicts = [
  {
    id: 'conflict-001',
    type: 'resource-competition', // resource-competition, dependency-block, dynamic-response
    title: '资源竞争',
    description: '多个任务同时需要同一批医疗物资',
    severity: '高',
    status: '处理中',
    affectedTasks: ['task-008', 'task-012'],
    affectedAgents: ['agent-002', 'agent-003'],
    resolution: '正在协调物资分配优先级',
    createdAt: '2024-03-15 10:30',
    resolvedAt: null
  },
  {
    id: 'conflict-002',
    type: 'dependency-block', // resource-competition, dependency-block, dynamic-response
    title: '依赖阻塞',
    description: '任务task-005依赖task-004完成，但task-004进度延迟',
    severity: '中',
    status: '处理中',
    affectedTasks: ['task-004', 'task-005', 'task-006'],
    affectedAgents: ['agent-003'],
    resolution: '正在优化加载流程',
    createdAt: '2024-03-15 11:45',
    resolvedAt: null
  },
  {
    id: 'conflict-003',
    type: 'dynamic-response', // resource-competition, dependency-block, dynamic-response
    title: '动态响应',
    description: '新的受灾区域发现，需要调整任务分配',
    severity: '高',
    status: '已解决',
    affectedTasks: ['task-001', 'task-007'],
    affectedAgents: ['agent-001'],
    resolution: '已增加新的搜救区域分配',
    createdAt: '2024-03-15 12:00',
    resolvedAt: '2024-03-15 13:30'
  }
]
