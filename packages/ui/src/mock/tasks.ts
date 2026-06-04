// 工程数据
export const mockProjects = [
  {
    id: 'proj-001',
    name: '受灾群众安置',
    description: '为受灾群众提供临时安置点和基本生活保障',
    status: '进行中',
    startDate: '2024-03-15',
    endDate: '2024-03-18'
  },
  {
    id: 'proj-002',
    name: '应急物资运输',
    description: '确保食品、药品、饮用水等应急物资及时送达',
    status: '进行中',
    startDate: '2024-03-15',
    endDate: '2024-03-20'
  },
  {
    id: 'proj-003',
    name: '伤员救治转移',
    description: '将重伤员转移到安全区域的医疗机构',
    status: '已完成',
    startDate: '2024-03-15',
    endDate: '2024-03-16'
  },
  {
    id: 'proj-004',
    name: '灾后防疫工作',
    description: '开展灾后消毒、防疫和健康监测',
    status: '未开始',
    startDate: '2024-03-18',
    endDate: '2024-03-25'
  }
]

// 任务数据
export const mockTasks = [
  // 工程1：受灾群众安置
  {
    id: 'task-001',
    parentId: null,
    projectId: 'proj-001',
    name: '搭建临时帐篷',
    description: '为受灾群众搭建临时安置帐篷',
    status: '进行中',
    assignee: '搜救Agent',
    startDate: '2024-03-15',
    endDate: '2024-03-16',
    priority: '高',
    subtasks: [
      { id: 'sub-001', name: '领取帐篷材料', completed: true },
      { id: 'sub-002', name: '搭建帐篷A区', completed: true },
      { id: 'sub-003', name: '搭建帐篷B区', completed: false },
      { id: 'sub-004', name: '铺设地垫和睡袋', completed: false }
    ]
  },
  {
    id: 'task-002',
    parentId: null,
    projectId: 'proj-001',
    name: '发放应急物资',
    description: '向受灾群众发放食品、饮用水等',
    status: '待开始',
    assignee: '物资Agent',
    startDate: '2024-03-16',
    endDate: '2024-03-17',
    priority: '高',
    subtasks: [
      { id: 'sub-005', name: '清点物资数量', completed: false },
      { id: 'sub-006', name: '分配物资至各帐篷区', completed: false }
    ]
  },
  {
    id: 'task-003',
    parentId: null,
    projectId: 'proj-001',
    name: '健康检查',
    description: '对受灾群众进行基础健康检查',
    status: '待开始',
    assignee: '医疗Agent',
    startDate: '2024-03-16',
    endDate: '2024-03-18',
    priority: '中',
    subtasks: [
      { id: 'sub-007', name: '设置检查点', completed: false },
      { id: 'sub-008', name: '登记健康信息', completed: false }
    ]
  },
  // 工程2：应急物资运输
  {
    id: 'task-004',
    parentId: null,
    projectId: 'proj-002',
    name: '物资装载',
    description: '将应急物资装载至运输车辆',
    status: '进行中',
    assignee: '物资Agent',
    startDate: '2024-03-15',
    endDate: '2024-03-16',
    priority: '高',
    subtasks: [
      { id: 'sub-009', name: '核对物资清单', completed: true },
      { id: 'sub-010', name: '装载第一批物资', completed: true },
      { id: 'sub-011', name: '装载第二批物资', completed: false }
    ]
  },
  {
    id: 'task-005',
    parentId: null,
    projectId: 'proj-002',
    name: '物资运输',
    description: '将物资运输至受灾区域',
    status: '待开始',
    assignee: '物资Agent',
    startDate: '2024-03-16',
    endDate: '2024-03-17',
    priority: '高',
    dependencies: ['task-004'],
    subtasks: [
      { id: 'sub-012', name: '规划运输路线', completed: false },
      { id: 'sub-013', name: '执行运输任务', completed: false }
    ]
  },
  {
    id: 'task-006',
    parentId: null,
    projectId: 'proj-002',
    name: '物资分发',
    description: '在受灾区域分发应急物资',
    status: '待开始',
    assignee: '物资Agent',
    startDate: '2024-03-17',
    endDate: '2024-03-18',
    priority: '高',
    dependencies: ['task-005'],
    subtasks: [
      { id: 'sub-014', name: '确定分发点', completed: false },
      { id: 'sub-015', name: '组织群众有序领取', completed: false }
    ]
  },
  // 工程3：伤员救治转移
  {
    id: 'task-007',
    parentId: null,
    projectId: 'proj-003',
    name: '伤员搜救',
    description: '在灾区搜寻受伤群众',
    status: '已完成',
    assignee: '搜救Agent',
    startDate: '2024-03-15',
    endDate: '2024-03-15',
    priority: '高',
    subtasks: [
      { id: 'sub-016', name: '无人机侦察', completed: true },
      { id: 'sub-017', name: '地面搜救队行动', completed: true }
    ]
  },
  {
    id: 'task-008',
    parentId: null,
    projectId: 'proj-003',
    name: '现场急救',
    description: '对伤员进行紧急救治',
    status: '已完成',
    assignee: '医疗Agent',
    startDate: '2024-03-15',
    endDate: '2024-03-15',
    priority: '高',
    dependencies: ['task-007'],
    subtasks: [
      { id: 'sub-018', name: '初步诊断', completed: true },
      { id: 'sub-019', name: '紧急处理', completed: true }
    ]
  },
  {
    id: 'task-009',
    parentId: null,
    projectId: 'proj-003',
    name: '转运至医院',
    description: '将重伤员转运至定点医院',
    status: '已完成',
    assignee: '医疗Agent',
    startDate: '2024-03-15',
    endDate: '2024-03-16',
    priority: '高',
    dependencies: ['task-008'],
    subtasks: [
      { id: 'sub-020', name: '联系医院接收', completed: true },
      { id: 'sub-021', name: '安排救护车', completed: true }
    ]
  },
  {
    id: 'task-010',
    parentId: null,
    projectId: 'proj-003',
    name: '后续跟进',
    description: '跟踪伤员治疗情况',
    status: '待开始',
    assignee: '医疗Agent',
    startDate: '2024-03-16',
    endDate: '2024-03-18',
    priority: '中',
    dependencies: ['task-009'],
    subtasks: [
      { id: 'sub-022', name: '联系医院获取报告', completed: false }
    ]
  },
  // 工程4：灾后防疫
  {
    id: 'task-011',
    parentId: null,
    projectId: 'proj-004',
    name: '防疫物资准备',
    description: '准备消毒液、口罩等防疫物资',
    status: '待开始',
    assignee: '物资Agent',
    startDate: '2024-03-18',
    endDate: '2024-03-19',
    priority: '中',
    subtasks: [
      { id: 'sub-023', name: '采购防疫物资', completed: false },
      { id: 'sub-024', name: '物资入库', completed: false }
    ]
  },
  {
    id: 'task-012',
    parentId: null,
    projectId: 'proj-004',
    name: '区域消杀',
    description: '对灾区进行全面消毒',
    status: '待开始',
    assignee: '搜救Agent',
    startDate: '2024-03-19',
    endDate: '2024-03-21',
    priority: '高',
    dependencies: ['task-011'],
    subtasks: [
      { id: 'sub-025', name: '划分消杀区域', completed: false },
      { id: 'sub-026', name: '实施消杀作业', completed: false }
    ]
  }
]

// 导出任务数组
export const tasks = mockTasks

// 导出工程数组
export const projects = mockProjects


