// 预案数据
export const plans = [
  {
    id: 'plan-001',
    name: '抢险救灾预案',
    description: '针对洪涝、地震等自然灾害的紧急救援预案',
    category: '自然灾害',
    priority: '高',
    status: '启用中',
    lastUpdated: '2024-03-15',
    version: '2.1',
    scenarios: ['地震', '洪水', '台风']
  },
  {
    id: 'plan-002',
    name: '战场后勤保障预案',
    description: '应对紧急情况下的物资供应和后勤支持预案',
    category: '后勤保障',
    priority: '中',
    status: '启用中',
    lastUpdated: '2024-02-20',
    version: '1.5',
    scenarios: ['战区补给', '医疗后送', '装备维修']
  },
  {
    id: 'plan-003',
    name: '城市内涝应急处置预案',
    description: '针对城市内涝问题的专业处置方案',
    category: '城市安全',
    priority: '高',
    status: '待激活',
    lastUpdated: '2024-03-10',
    version: '3.0',
    scenarios: ['暴雨', '洪涝', '排水系统故障']
  }
]
