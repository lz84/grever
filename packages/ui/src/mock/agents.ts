// Agent 数据
export const agents = [
  {
    id: 'agent-001',
    name: '搜救Agent',
    type: '搜救',
    status: 'online', // online, busy, offline
    workload: 65,
    currentTask: '受灾群众搜救与转移',
    location: 'A区受灾区域',
    capacity: '高',
    lastActivity: '2024-03-15 14:30'
  },
  {
    id: 'agent-002',
    name: '医疗Agent',
    type: '医疗',
    status: 'busy', // online, busy, offline
    workload: 85,
    currentTask: '伤员现场急救与转运',
    location: '临时医疗点',
    capacity: '中',
    lastActivity: '2024-03-15 15:15'
  },
  {
    id: 'agent-003',
    name: '物资Agent',
    type: '后勤',
    status: 'online', // online, busy, offline
    workload: 45,
    currentTask: '应急物资运输与分发',
    location: '物资集散中心',
    capacity: '高',
    lastActivity: '2024-03-15 16:00'
  },
  {
    id: 'agent-004',
    name: '指挥Agent',
    type: '指挥',
    status: 'busy', // online, busy, offline
    workload: 90,
    currentTask: '全局协调与决策支持',
    location: '指挥中心',
    capacity: '严禁',
    lastActivity: '2024-03-15 16:30'
  }
]
