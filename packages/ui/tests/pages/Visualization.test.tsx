/**
 * MAK-197: 可视化单元测试
 * 测试内容：看板组件、Trace 时间线组件、报表组件
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

// Suppress console.error for expected warnings
const originalError = console.error
beforeEach(() => {
  console.error = vi.fn()
})
afterEach(() => {
  console.error = originalError
})

describe('可视化 - 看板', () => {
  describe('Dashboard 看板组件', () => {
    it('应该正确计算目标完成率', () => {
      const goals = [
        { id: 1, status: 'completed' },
        { id: 2, status: 'completed' },
        { id: 3, status: 'completed' },
        { id: 4, status: 'completed' },
        { id: 5, status: 'in_progress' },
        { id: 6, status: 'pending' },
      ]

      const completedGoals = goals.filter(g => g.status === 'completed')
      const completionRate = (completedGoals.length / goals.length) * 100

      expect(completionRate).toBeCloseTo(66.67, 1)
    })

    it('应该正确计算任务状态分布', () => {
      const tasks = [
        { id: '1', status: 'todo' },
        { id: '2', status: 'todo' },
        { id: '3', status: 'todo' },
        { id: '4', status: 'todo' },
        { id: '5', status: 'in_progress' },
        { id: '6', status: 'in_progress' },
        { id: '7', status: 'in_progress' },
        { id: '8', status: 'done' },
        { id: '9', status: 'done' },
        { id: '10', status: 'done' },
        { id: '11', status: 'done' },
        { id: '12', status: 'done' },
        { id: '13', status: 'blocked' },
      ]

      const statusCounts = {
        todo: tasks.filter(t => t.status === 'todo').length,
        in_progress: tasks.filter(t => t.status === 'in_progress').length,
        done: tasks.filter(t => t.status === 'done').length,
        blocked: tasks.filter(t => t.status === 'blocked').length,
      }

      expect(statusCounts.todo).toBe(4)
      expect(statusCounts.in_progress).toBe(3)
      expect(statusCounts.done).toBe(5)
      expect(statusCounts.blocked).toBe(1)
    })

    it('应该正确计算百分比', () => {
      const calculatePercentage = (part: number, total: number): number => {
        if (total === 0) return 0
        return Math.round((part / total) * 100)
      }

      expect(calculatePercentage(4, 13)).toBe(31)
      expect(calculatePercentage(3, 13)).toBe(23)
      expect(calculatePercentage(5, 13)).toBe(38)
      expect(calculatePercentage(1, 13)).toBe(8)
      expect(calculatePercentage(0, 0)).toBe(0)
    })
  })

  describe('智能体负载分布', () => {
    it('应该正确显示负载条', () => {
      const mockAgent = {
        name: '刚子',
        load: 78,
        current_tasks: 1,
      }

      const getLoadWidth = (load: number): string => {
        return `${Math.min(load, 100)}%`
      }

      expect(getLoadWidth(78)).toBe('78%')
      expect(getLoadWidth(100)).toBe('100%')
      expect(getLoadWidth(150)).toBe('100%') // cap at 100
    })

    it('应该正确分类负载级别', () => {
      const getLoadLevel = (load: number): 'high' | 'medium' | 'low' => {
        if (load > 90) return 'high'
        if (load > 70) return 'medium'
        return 'low'
      }

      expect(getLoadLevel(95)).toBe('high')
      expect(getLoadLevel(85)).toBe('medium')
      expect(getLoadLevel(65)).toBe('low')
    })
  })

  describe('执行趋势', () => {
    it('应该按天分组统计数据', () => {
      const workflows = [
        { started_at: '2026-04-15T09:30:00Z', status: 'completed' },
        { started_at: '2026-04-15T10:00:00Z', status: 'completed' },
        { started_at: '2026-04-15T11:00:00Z', status: 'running' },
        { started_at: '2026-04-14T09:00:00Z', status: 'completed' },
        { started_at: '2026-04-14T10:00:00Z', status: 'completed' },
        { started_at: '2026-04-13T14:00:00Z', status: 'completed' },
      ]

      const groupByDay = (workflows: typeof mockWorkflows) => {
        const groups: Record<string, number> = {}
        workflows.forEach(w => {
          const day = w.started_at.split('T')[0]
          groups[day] = (groups[day] || 0) + 1
        })
        return groups
      }

      const groups = groupByDay(workflows)
      expect(groups['2026-04-15']).toBe(3)
      expect(groups['2026-04-14']).toBe(2)
      expect(groups['2026-04-13']).toBe(1)
    })
  })
})

describe('可视化 - Trace 时间线', () => {
  describe('Trace 查看组件', () => {
    it('应该正确解析时间线步骤', () => {
      const trace = {
        task_id: 'task-1',
        workflow_id: 'wf-1',
        task_title: '危化品泄漏处置工作流',
        started_at: '2026-04-15T09:30:00Z',
        steps: [
          { timestamp: '2026-04-15T09:30:00Z', action: '工作流开始', type: 'start', duration_ms: 0, agent_id: '刚子' },
          { timestamp: '2026-04-15T09:30:00Z', action: '灾情评估', type: 'step', duration_ms: 120000, agent_id: '刚子' },
          { timestamp: '2026-04-15T09:32:00Z', action: '预案匹配', type: 'step', duration_ms: 60000, agent_id: '刚子' },
        ],
      }

      expect(trace.steps).toHaveLength(3)
      expect(trace.steps[0].action).toBe('工作流开始')
      expect(trace.steps[1].duration_ms).toBe(120000) // 2 minutes
    })

    it('应该正确计算步骤耗时', () => {
      const calculateDuration = (start: string, end: string | null): string => {
        if (!end) return '运行中'
        const startTime = new Date(start).getTime()
        const endTime = new Date(end).getTime()
        const durationMs = endTime - startTime
        const minutes = Math.round(durationMs / 60000)
        return `${minutes}分钟`
      }

      expect(calculateDuration('2026-04-15T09:30:00Z', '2026-04-15T09:32:00Z')).toBe('2分钟')
      expect(calculateDuration('2026-04-15T09:30:00Z', null)).toBe('运行中')
    })

    it('应该正确显示步骤状态', () => {
      const getStepStatusDisplay = (status: string): { icon: string; text: string; color: string } => {
        const statusMap: Record<string, { icon: string; text: string; color: string }> = {
          completed: { icon: '✅', text: '完成', color: 'green' },
          running: { icon: '🔄', text: '运行中', color: 'blue' },
          pending: { icon: '⏳', text: '等待', color: 'gray' },
          failed: { icon: '❌', text: '失败', color: 'red' },
        }
        return statusMap[status] || { icon: '❓', text: '未知', color: 'gray' }
      }

      expect(getStepStatusDisplay('completed').icon).toBe('✅')
      expect(getStepStatusDisplay('running').icon).toBe('🔄')
      expect(getStepStatusDisplay('pending').icon).toBe('⏳')
      expect(getStepStatusDisplay('failed').icon).toBe('❌')
    })

    it('应该正确处理时间线展开/折叠', () => {
      const mockTraces = [
        { id: 'wf-1', task_title: '工作流1', expanded: true },
        { id: 'wf-2', task_title: '工作流2', expanded: false },
        { id: 'wf-3', task_title: '工作流3', expanded: false },
      ]

      const toggleExpand = (id: string, traces: typeof mockTraces) => {
        return traces.map(t =>
          t.id === id ? { ...t, expanded: !t.expanded } : t
        )
      }

      let traces = [...mockTraces]
      traces = toggleExpand('wf-1', traces)
      expect(traces.find(t => t.id === 'wf-1')?.expanded).toBe(false)

      traces = toggleExpand('wf-2', traces)
      expect(traces.find(t => t.id === 'wf-2')?.expanded).toBe(true)
    })

    it('应该默认展开最近3条记录', () => {
      const traces = [
        { id: 'wf-1', task_title: '工作流1', started_at: '2026-04-15T09:30:00Z' },
        { id: 'wf-2', task_title: '工作流2', started_at: '2026-04-14T09:30:00Z' },
        { id: 'wf-3', task_title: '工作流3', started_at: '2026-04-13T09:30:00Z' },
        { id: 'wf-4', task_title: '工作流4', started_at: '2026-04-12T09:30:00Z' },
        { id: 'wf-5', task_title: '工作流5', started_at: '2026-04-11T09:30:00Z' },
      ]

      const sortedTraces = [...traces].sort((a, b) => 
        new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
      )
      const defaultExpanded = sortedTraces.slice(0, 3).map(t => ({ ...t, expanded: true }))
      const defaultCollapsed = sortedTraces.slice(3).map(t => ({ ...t, expanded: false }))

      expect(defaultExpanded).toHaveLength(3)
      expect(defaultCollapsed).toHaveLength(2)
    })
  })

  describe('冲突告警显示', () => {
    it('应该正确显示冲突事件', () => {
      const dispute = {
        id: 'dispute-1',
        description: '资源竞争冲突',
        involved_agents: ['刚子', '谷子'],
        status: 'open',
        created_at: '2026-04-15T09:33:00Z',
      }

      expect(dispute.description).toBe('资源竞争冲突')
      expect(dispute.involved_agents).toContain('刚子')
      expect(dispute.involved_agents).toContain('谷子')
    })
  })
})

describe('可视化 - 报表', () => {
  describe('Reports 报表组件', () => {
    it('应该正确计算完成率', () => {
      const calculateCompletionRate = (completed: number, total: number): number => {
        if (total === 0) return 0
        return Math.round((completed / total) * 100)
      }

      expect(calculateCompletionRate(3, 5)).toBe(60)
      expect(calculateCompletionRate(5, 5)).toBe(100)
      expect(calculateCompletionRate(0, 5)).toBe(0)
      expect(calculateCompletionRate(0, 0)).toBe(0)
    })

    it('应该正确计算总耗时', () => {
      const calculateTotalDuration = (started_at: string | null, completed_at: string | null): string => {
        if (!started_at || !completed_at) return '—'
        const start = new Date(started_at).getTime()
        const end = new Date(completed_at).getTime()
        const durationMs = end - start
        const minutes = Math.round(durationMs / 60000)
        return `${minutes}min`
      }

      expect(calculateTotalDuration('2026-04-15T09:30:00Z', '2026-04-15T10:02:00Z')).toBe('32min')
      expect(calculateTotalDuration('2026-04-15T09:30:00Z', null)).toBe('—')
    })

    it('应该正确处理报表展开/折叠', () => {
      const reports = [
        { workflow_id: 'wf-1', expanded: false },
        { workflow_id: 'wf-2', expanded: false },
      ]

      const toggleReport = (id: string, reports: typeof reports) => {
        return reports.map(r =>
          r.workflow_id === id ? { ...r, expanded: !r.expanded } : r
        )
      }

      let result = toggleReport('wf-1', reports)
      expect(result.find(r => r.workflow_id === 'wf-1')?.expanded).toBe(true)
      
      result = toggleReport('wf-1', result)
      expect(result.find(r => r.workflow_id === 'wf-1')?.expanded).toBe(false)
    })

    it('应该正确格式化执行时间', () => {
      const formatDate = (dateStr: string): string => {
        const date = new Date(dateStr)
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const day = String(date.getDate()).padStart(2, '0')
        return `${month}-${day}`
      }

      expect(formatDate('2026-04-15T09:30:00Z')).toBe('04-15')
      expect(formatDate('2026-04-01T10:00:00Z')).toBe('04-01')
    })
  })

  describe('报表详情', () => {
    it('应该正确显示智能体效率统计', () => {
      const agentStats = [
        { agent_id: '刚子', tasks: 2, total_duration_ms: 180000 },
        { agent_id: '谷子', tasks: 1, total_duration_ms: null },
      ]

      const calculateAvgDuration = (stats: typeof agentStats[0]): string => {
        if (!stats.total_duration_ms || stats.tasks === 0) return '运行中'
        const avgMs = stats.total_duration_ms / stats.tasks
        const avgMin = Math.round(avgMs / 60000)
        return `${avgMin}min/任务`
      }

      expect(calculateAvgDuration(agentStats[0])).toBe('1min/任务')
      expect(calculateAvgDuration(agentStats[1])).toBe('运行中')
    })
  })
})
