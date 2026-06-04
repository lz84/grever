import { http, HttpResponse } from 'msw'

// Mock data
export const mockAgents = [
  {
    id: 'agent-1',
    name: '刚子',
    capabilities: ['编排', '规划', '协调'],
    status: 'online',
    address: 'http://localhost:18789/agents/gangzi',
    metadata: { role: 'CEO', model: 'qwen3.6-plus' },
    load: 78,
    current_tasks: 1,
    registered_at: '2026-04-14T16:17:00Z',
    last_heartbeat: '2026-04-15T10:30:00Z',
  },
  {
    id: 'agent-2',
    name: '谷子',
    capabilities: ['交易', '分析'],
    status: 'busy',
    address: 'http://localhost:18790/agents/guzi',
    metadata: { role: 'Trader', model: 'qwen3.6-plus' },
    load: 62,
    current_tasks: 2,
    registered_at: '2026-04-14T16:17:00Z',
    last_heartbeat: '2026-04-15T10:30:00Z',
  },
  {
    id: 'agent-3',
    name: '麻子',
    capabilities: ['编码', '调试'],
    status: 'offline',
    address: 'http://localhost:18791/agents/mazi',
    metadata: { role: 'Developer', model: 'qwen3.6-plus' },
    load: 91,
    current_tasks: 3,
    registered_at: '2026-04-14T16:17:00Z',
    last_heartbeat: '2026-04-15T09:00:00Z',
  },
]

export const mockGoals = [
  {
    id: 1,
    title: '城市应急管理平台',
    description: '构建一个综合性的城市应急管理平台',
    priority: 'P1',
    due_date: '2026-04-30',
    status: 'in_progress',
    created_at: '2026-04-01T11:08:00Z',
    updated_at: '2026-04-15T10:28:00Z',
    project_id: 1,
    parent_id: null,
  },
  {
    id: 2,
    title: '智能投资研究',
    description: '建立量化投资研究体系',
    priority: 'P2',
    due_date: '2026-05-15',
    status: 'pending',
    created_at: '2026-04-10T09:00:00Z',
    updated_at: '2026-04-15T08:30:00Z',
    project_id: 2,
    parent_id: null,
  },
  {
    id: 3,
    title: '抢险救灾',
    description: '抢险救灾预案与执行系统',
    priority: 'P0',
    due_date: '2026-04-20',
    status: 'completed',
    created_at: '2026-04-05T14:00:00Z',
    updated_at: '2026-04-14T18:00:00Z',
    project_id: 3,
    parent_id: null,
  },
]

export const mockProjects = [
  {
    id: 1,
    name: '预案模块开发',
    description: '城市应急管理平台的预案模块开发项目',
    goal_id: 1,
    status: 'active',
    created_at: '2026-04-10T10:00:00Z',
    updated_at: '2026-04-15T10:00:00Z',
  },
  {
    id: 2,
    name: '指挥调度模块',
    description: '指挥调度模块开发',
    goal_id: 1,
    status: 'active',
    created_at: '2026-04-11T10:00:00Z',
    updated_at: '2026-04-15T09:00:00Z',
  },
]

export const mockTasks = [
  {
    id: 'task-1',
    title: '设计数据库结构',
    description: '设计应急管理数据库结构',
    status: 'in_progress',
    priority: 1,
    category: 'development',
    due_date: '2026-04-20',
    created_at: '2026-04-10T10:00:00Z',
    updated_at: '2026-04-15T10:00:00Z',
    goal_id: 1,
    parent_id: null,
    dependency_ids: [],
    project_id: 1,
    assigned_agent: '麻子',
  },
  {
    id: 'task-2',
    title: '开发 API 接口',
    description: '开发应急管理 API',
    status: 'todo',
    priority: 0,
    category: 'development',
    due_date: '2026-04-25',
    created_at: '2026-04-10T10:00:00Z',
    updated_at: '2026-04-15T10:00:00Z',
    goal_id: 1,
    parent_id: null,
    dependency_ids: ['task-1'],
    project_id: 1,
    assigned_agent: '谷子',
  },
]

export const mockDisputes = [
  {
    id: 'dispute-1',
    dispute_type: 'resource_competition',
    description: '资源竞争冲突',
    involved_agents: ['刚子', '谷子'],
    related_task_id: 'task-1',
    status: 'open',
    resolution: null,
    resolved_by: null,
    created_at: '2026-04-15T09:33:00Z',
    updated_at: '2026-04-15T09:33:00Z',
    resolved_at: null,
  },
]

export const mockTraces = [
  {
    task_id: 'task-1',
    workflow_id: 'wf-1',
    task_title: '危化品泄漏处置工作流',
    started_at: '2026-04-15T09:30:00Z',
    final_state: 'running',
    success: null,
    result: null,
    error_message: null,
    cognitions_used: 3,
    context_size_bytes: 1024,
    total_duration_ms: 900000,
    agent_id: '刚子',
    steps: [
      { timestamp: '2026-04-15T09:30:00Z', action: '工作流开始', type: 'start', duration_ms: 0, agent_id: '刚子' },
      { timestamp: '2026-04-15T09:30:00Z', action: '灾情评估', type: 'step', duration_ms: 120000, agent_id: '刚子' },
      { timestamp: '2026-04-15T09:32:00Z', action: '预案匹配', type: 'step', duration_ms: 60000, agent_id: '刚子' },
    ],
  },
]

export const mockWorkflows = [
  {
    id: 'wf-1',
    goal_id: '1',
    status: 'running',
    name: '危化品泄漏处置工作流',
    description: '危化品泄漏应急处置',
    dag: { nodes: ['step1', 'step2', 'step3'], edges: [] },
    workflow_metadata: {},
    created_by: '刚子',
    created_at: '2026-04-15T09:30:00Z',
    updated_at: '2026-04-15T09:33:00Z',
    started_at: '2026-04-15T09:30:00Z',
    completed_at: null,
    steps: [
      { id: 'step1', workflow_id: 'wf-1', name: '灾情评估', description: '评估灾情', status: 'completed', dependencies: [], order: 1, agent_id: '刚子', retry_count: 0, max_retries: 3 },
      { id: 'step2', workflow_id: 'wf-1', name: '预案匹配', description: '匹配预案', status: 'completed', dependencies: ['step1'], order: 2, agent_id: '刚子', retry_count: 0, max_retries: 3 },
      { id: 'step3', workflow_id: 'wf-1', name: '资源调度', description: '调度资源', status: 'running', dependencies: ['step2'], order: 3, agent_id: '谷子', retry_count: 0, max_retries: 3 },
    ],
  },
]

export const mockKnowledge = [
  {
    id: 'kb-1',
    title: '预案匹配经验',
    type: 'experience',
    tags: ['workflow', 'emergency'],
    source: '刚子',
    agent_id: 'agent-1',
    created_at: '2026-04-15T10:00:00Z',
    content: '# 预案匹配经验\n\n在应急管理中，预案匹配是关键环节...',
  },
  {
    id: 'kb-2',
    title: '地震救援教训',
    type: 'lesson',
    tags: ['rescue', 'earthquake'],
    source: '谷子',
    agent_id: 'agent-2',
    created_at: '2026-04-11T14:00:00Z',
    content: '# 地震救援教训\n\n地震救援中存在以下问题...',
  },
]

export const mockAssessments = [
  {
    agent_id: '刚子',
    overall_score: 85,
    retrieval_quality: 90,
    context_utilization: 82,
    injection_accuracy: 83,
    knowledge_freshness: 80,
  },
  {
    agent_id: '谷子',
    overall_score: 72,
    retrieval_quality: 75,
    context_utilization: 68,
    injection_accuracy: 74,
    knowledge_freshness: 70,
  },
  {
    agent_id: '麻子',
    overall_score: 91,
    retrieval_quality: 95,
    context_utilization: 88,
    injection_accuracy: 90,
    knowledge_freshness: 88,
  },
]

export const mockScenarios = [
  {
    id: 'scenario-1',
    name: '危化品泄漏处置',
    description: '危化品泄漏应急处置标准流程',
    category: 'emergency',
    steps: ['灾情评估', '预案匹配', '资源调度', '执行指挥', '灾后评估'],
    created_at: '2026-04-01T10:00:00Z',
    updated_at: '2026-04-15T10:00:00Z',
    favorite: true,
  },
  {
    id: 'scenario-2',
    name: '地震救援',
    description: '地震应急救援标准流程',
    category: 'rescue',
    steps: ['灾情评估', '人员搜救', '物资调配', '安置转移', '灾后恢复'],
    created_at: '2026-04-05T10:00:00Z',
    updated_at: '2026-04-14T10:00:00Z',
    favorite: false,
  },
]

export const mockInjectRules = [
  {
    id: 'rule-1',
    name: '任务完成自动注入',
    trigger_condition: 'task.status=done',
    target_kb: 'default',
    enabled: true,
    created_at: '2026-04-01T10:00:00Z',
    updated_at: '2026-04-15T10:00:00Z',
  },
  {
    id: 'rule-2',
    name: '工作流完成注入',
    trigger_condition: 'workflow=done',
    target_kb: 'default',
    enabled: true,
    created_at: '2026-04-01T10:00:00Z',
    updated_at: '2026-04-15T10:00:00Z',
  },
  {
    id: 'rule-3',
    name: '争议解决注入',
    trigger_condition: 'dispute=resolved',
    target_kb: 'experience',
    enabled: false,
    created_at: '2026-04-01T10:00:00Z',
    updated_at: '2026-04-10T10:00:00Z',
  },
]

export const handlers = [
  // Goals API
  http.get('*/api/v1/goals', () => {
    return HttpResponse.json(mockGoals)
  }),
  http.get('*/api/v1/goals/:id', ({ params }) => {
    const goal = mockGoals.find(g => g.id === Number(params.id))
    if (!goal) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(goal)
  }),
  http.post('*/api/v1/goals', async ({ request }) => {
    const data = await request.json()
    return HttpResponse.json({ id: 4, ...data, created_at: new Date().toISOString() })
  }),

  // Projects API
  http.get('*/api/v1/projects', () => {
    return HttpResponse.json(mockProjects)
  }),
  http.get('*/api/v1/projects/:id', ({ params }) => {
    const project = mockProjects.find(p => p.id === Number(params.id))
    if (!project) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(project)
  }),
  http.post('*/api/v1/projects', async ({ request }) => {
    const data = await request.json()
    return HttpResponse.json({ id: 3, ...data, created_at: new Date().toISOString() })
  }),

  // Tasks API
  http.get('*/api/v1/tasks', () => {
    return HttpResponse.json(mockTasks)
  }),
  http.get('*/api/v1/tasks/:id', ({ params }) => {
    const task = mockTasks.find(t => t.id === params.id)
    if (!task) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(task)
  }),
  http.post('*/api/v1/tasks', async ({ request }) => {
    const data = await request.json()
    return HttpResponse.json({ id: 'task-new', ...data, created_at: new Date().toISOString() })
  }),
  http.patch('*/api/v1/tasks/:id/status', async ({ params, request }) => {
    const data = await request.json()
    const task = mockTasks.find(t => t.id === params.id)
    if (task) {
      return HttpResponse.json({ ...task, status: data.status })
    }
    return new HttpResponse(null, { status: 404 })
  }),

  // Agents API
  http.get('*/api/v1/agents', () => {
    return HttpResponse.json(mockAgents)
  }),
  http.get('*/api/v1/agents/:id', ({ params }) => {
    const agent = mockAgents.find(a => a.id === params.id)
    if (!agent) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(agent)
  }),

  // Disputes API
  http.get('*/api/v1/disputes', () => {
    return HttpResponse.json(mockDisputes)
  }),
  http.get('*/api/v1/disputes/:id', ({ params }) => {
    const dispute = mockDisputes.find(d => d.id === params.id)
    if (!dispute) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(dispute)
  }),

  // Workflows API
  http.get('*/api/v1/workflows', () => {
    return HttpResponse.json(mockWorkflows)
  }),
  http.get('*/api/v1/workflows/:id', ({ params }) => {
    const workflow = mockWorkflows.find(w => w.id === params.id)
    if (!workflow) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(workflow)
  }),
  http.post('*/api/v1/workflows/from-goal', async ({ request }) => {
    return HttpResponse.json({ id: 'wf-new', status: 'running', created_at: new Date().toISOString() })
  }),

  // Traces API
  http.get('*/api/v1/traces', () => {
    return HttpResponse.json({ running: mockTraces.filter(t => t.final_state === 'running'), completed: mockTraces.filter(t => t.final_state === 'completed') })
  }),
  http.get('*/api/v1/traces/:taskId', ({ params }) => {
    const trace = mockTraces.find(t => t.task_id === params.taskId)
    if (!trace) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(trace)
  }),

  // Reports API
  http.get('*/api/v1/reports', () => {
    return HttpResponse.json([
      {
        workflow_id: 'wf-1',
        workflow_name: '危化品泄漏处置工作流',
        started_at: '2026-04-15T09:30:00Z',
        completed_at: null,
        status: 'running',
        steps_completed: 2,
        steps_total: 5,
        disputes_resolved: 1,
      },
    ])
  }),
  http.get('*/api/v1/reports/:workflowId', ({ params }) => {
    return HttpResponse.json({
      workflow_id: params.workflowId,
      workflow_name: '危化品泄漏处置工作流',
      started_at: '2026-04-15T09:30:00Z',
      completed_at: null,
      status: 'running',
      steps: mockWorkflows[0].steps,
      agent_stats: [
        { agent_id: '刚子', tasks: 2, avg_duration_ms: 90000 },
        { agent_id: '谷子', tasks: 1, avg_duration_ms: null },
      ],
    })
  }),

  // Knowledge (Grasp) API
  http.get('*/api/v1/grasp/knowledge', () => {
    return HttpResponse.json(mockKnowledge)
  }),
  http.get('*/api/v1/grasp/knowledge/:id', ({ params }) => {
    const kb = mockKnowledge.find(k => k.id === params.id)
    if (!kb) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(kb)
  }),

  // Assessment API
  http.get('*/api/v1/grasp/cognition-assessment', () => {
    return HttpResponse.json(mockAssessments)
  }),

  // Inject Status API
  http.get('*/api/v1/grasp/inject/status', () => {
    return HttpResponse.json({
      service_status: 'running',
      recent_injections: [
        { id: 'inj-1', source: 'task', type: 'task_result', cognition_count: 3, status: 'success', created_at: '2026-04-15T09:30:00Z' },
        { id: 'inj-2', source: 'workflow', type: 'workflow_result', cognition_count: 5, status: 'success', created_at: '2026-04-15T09:25:00Z' },
      ],
    })
  }),

  // Inject Rules API
  http.get('*/api/v1/grasp/inject/rules', () => {
    return HttpResponse.json(mockInjectRules)
  }),
  http.patch('*/api/v1/grasp/inject/rules/:id', async ({ params, request }) => {
    const data = await request.json()
    const rule = mockInjectRules.find(r => r.id === params.id)
    if (rule) {
      return HttpResponse.json({ success: true, rule: { ...rule, enabled: data.enabled } })
    }
    return new HttpResponse(null, { status: 404 })
  }),

  // Scenarios API
  http.get('*/api/v1/scenarios', () => {
    return HttpResponse.json(mockScenarios)
  }),
  http.get('*/api/v1/scenarios/:id', ({ params }) => {
    const scenario = mockScenarios.find(s => s.id === params.id)
    if (!scenario) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(scenario)
  }),
  http.post('*/api/v1/scenarios/:id/favorite', ({ params }) => {
    const scenario = mockScenarios.find(s => s.id === params.id)
    if (scenario) {
      scenario.favorite = !scenario.favorite
      return HttpResponse.json({ success: true, favorite: scenario.favorite })
    }
    return new HttpResponse(null, { status: 404 })
  }),

  // Favorites API
  http.get('*/api/v1/favorites', () => {
    return HttpResponse.json(mockScenarios.filter(s => s.favorite))
  }),
]
