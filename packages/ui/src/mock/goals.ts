import { mockProjects, mockTasks } from './tasks'

// 目标数据
export const goals = [
  {
    id: 'goal-001',
    code: 'NG-2024-001',
    title: '抢险救灾专项任务',
    description: '针对突发洪水灾害的紧急救援行动',
    planId: 'plan-001',
    planName: '抢险救灾预案',
    status: '执行中',
    priority: '高',
    startDate: '2024-03-15',
    endDate: '2024-03-20',
    progress: 45,
    projects: mockProjects,
    tasks: mockTasks,
    conflicts: []
  }
]
