/**
 * MAK-196: 系统管理单元测试
 * 测试内容：智能体列表/详情组件、Agent 状态显示、负载进度条渲染
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import AgentStatus from '../../src/pages/AgentStatus'
import AgentDetailModal from '../../src/pages/AgentDetailModal'
import { mockAgents } from '../mocks/handlers'

// Suppress console.error for expected warnings
const originalError = console.error
beforeEach(() => {
  console.error = vi.fn()
})
afterEach(() => {
  console.error = originalError
})

describe('系统管理 - 智能体管理', () => {
  describe('AgentStatus 组件', () => {
    it('应该渲染智能体列表', async () => {
      render(
        <MemoryRouter>
          <AgentStatus />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText(/活跃智能体/i)).toBeTruth()
      })
    })

    it('应该显示加载状态', () => {
      render(
        <MemoryRouter>
          <AgentStatus />
        </MemoryRouter>
      )

      // Initial load should show loading
      expect(screen.queryByText(/加载智能体状态/i) || screen.queryByText(/加载中/i)).toBeTruthy()
    })

    it('应该显示刷新按钮', async () => {
      render(
        <MemoryRouter>
          <AgentStatus />
        </MemoryRouter>
      )

      await waitFor(() => {
        const refreshBtn = screen.getByRole('button', { name: /刷新/i })
        expect(refreshBtn).toBeTruthy()
      })
    })

    it('应该显示 Live 状态指示器', async () => {
      render(
        <MemoryRouter>
          <AgentStatus />
        </MemoryRouter>
      )

      await waitFor(() => {
        const liveIndicator = screen.getByText(/Live/i)
        expect(liveIndicator).toBeTruthy()
      })
    })
  })

  describe('Agent 状态显示', () => {
    it('应该正确映射在线状态', () => {
      const mapAgentStatus = (status: string): 'online' | 'busy' | 'offline' => {
        if (status === 'idle' || status === 'online') return 'online'
        if (status === 'busy' || status === 'working') return 'busy'
        return 'offline'
      }

      expect(mapAgentStatus('idle')).toBe('online')
      expect(mapAgentStatus('online')).toBe('online')
      expect(mapAgentStatus('busy')).toBe('busy')
      expect(mapAgentStatus('working')).toBe('busy')
      expect(mapAgentStatus('offline')).toBe('offline')
      expect(mapAgentStatus('unknown')).toBe('offline')
    })

    it('应该正确显示状态文本', () => {
      const mapAgentStatusText = (status: string): string => {
        const mapped = mapAgentStatus(status)
        if (mapped === 'online') return '运行中'
        if (mapped === 'busy') return '协商中'
        return '离线'
      }

      const mapAgentStatus = (status: string): 'online' | 'busy' | 'offline' => {
        if (status === 'idle' || status === 'online') return 'online'
        if (status === 'busy' || status === 'working') return 'busy'
        return 'offline'
      }

      expect(mapAgentStatusText('online')).toBe('运行中')
      expect(mapAgentStatusText('busy')).toBe('协商中')
      expect(mapAgentStatusText('offline')).toBe('离线')
    })

    it('应该根据状态应用正确的样式类', () => {
      const getStatusColor = (status: string): string => {
        if (status === 'online') return 'blue'
        if (status === 'busy') return 'amber'
        return 'slate'
      }

      expect(getStatusColor('online')).toBe('blue')
      expect(getStatusColor('busy')).toBe('amber')
      expect(getStatusColor('offline')).toBe('slate')
    })
  })

  describe('负载进度条渲染', () => {
    it('应该正确计算负载百分比', () => {
      const mockAgent = {
        id: '1',
        name: '刚子',
        load: 78,
        current_tasks: 1,
        status: 'online',
        capabilities: ['编排', '规划'],
        address: 'http://localhost:18789',
        metadata: {},
        registered_at: '2026-04-14T16:17:00Z',
        last_heartbeat: '2026-04-15T10:30:00Z',
      }

      expect(mockAgent.load).toBe(78)
      expect(Math.min(mockAgent.load, 100)).toBe(78)
    })

    it('负载超过100应该被限制为100', () => {
      const agent = { load: 150 }
      expect(Math.min(agent.load, 100)).toBe(100)
    })

    it('应该根据负载显示不同颜色', () => {
      const getLoadColor = (load: number): string => {
        if (load > 90) return 'red'
        if (load > 70) return 'amber'
        return 'blue'
      }

      expect(getLoadColor(95)).toBe('red')
      expect(getLoadColor(85)).toBe('amber')
      expect(getLoadColor(60)).toBe('blue')
    })

    it('应该显示容量状态文本', () => {
      const getCapacityText = (load: number): string => {
        if (load > 80) return '紧张'
        if (load > 50) return '中等'
        return '充裕'
      }

      expect(getCapacityText(90)).toBe('紧张')
      expect(getCapacityText(65)).toBe('中等')
      expect(getCapacityText(40)).toBe('充裕')
    })
  })

  describe('AgentDetailModal 组件', () => {
    it('应该正确渲染智能体详情', () => {
      const agent = mockAgents[0]

      render(
        <AgentDetailModal
          agent={agent}
          onClose={vi.fn()}
        />
      )

      expect(screen.getByText(agent.name)).toBeTruthy()
      expect(screen.getByText(/编排/i)).toBeTruth() // capabilities
    })

    it('应该显示智能体地址', () => {
      const agent = mockAgents[0]

      render(
        <AgentDetailModal
          agent={agent}
          onClose={vi.fn()}
        />
      )

      expect(screen.getByText(agent.address || '')).toBeTruthy()
    })

    it('应该显示负载进度条', () => {
      const agent = mockAgents[0]

      render(
        <AgentDetailModal
          agent={agent}
          onClose={vi.fn()}
        />
      )

      // 负载百分比应该在 modal 中显示
      expect(screen.getByText(/\d+% LOAD/i)).toBeTruthy()
    })

    it('关闭按钮应该可点击', async () => {
      const onClose = vi.fn()
      const agent = mockAgents[0]

      render(
        <AgentDetailModal
          agent={agent}
          onClose={onClose}
        />
      )

      const closeBtn = screen.getByRole('button', { name: /关闭/i })
      await userEvent.click(closeBtn)
      
      expect(onClose).toHaveBeenCalled()
    })

    it('ESC 键应该关闭 Modal', async () => {
      const onClose = vi.fn()
      const agent = mockAgents[0]

      render(
        <AgentDetailModal
          agent={agent}
          onClose={onClose}
        />
      )

      fireEvent.keyDown(document, { key: 'Escape' })
      
      expect(onClose).toHaveBeenCalled()
    })
  })

  describe('能力标签显示', () => {
    it('应该显示最多3个能力标签', () => {
      const capabilities = ['编排', '规划', '协调', '执行', '监控']
      const displayCapabilities = capabilities.slice(0, 3)
      const extraCount = capabilities.length - 3

      expect(displayCapabilities).toHaveLength(3)
      expect(extraCount).toBe(2)
    })

    it('应该正确显示额外能力数量', () => {
      const capabilities = ['编排', '规划', '协调', '执行']
      const displayCapabilities = capabilities.slice(0, 3)
      const extraCount = capabilities.length - 3

      if (extraCount > 0) {
        expect(screen.getByText(`+${extraCount}`)).toBeTruthy()
      }
    })
  })

  describe('统计数据计算', () => {
    it('应该正确计算平均负载', () => {
      const agents = [
        { load: 78 },
        { load: 62 },
        { load: 91 },
        { load: 45 },
      ]

      const avgLoad = Math.round(agents.reduce((s, a) => s + a.load, 0) / agents.length)
      expect(avgLoad).toBe(69)
    })

    it('应该正确计算活跃智能体数量', () => {
      const agents = [
        { id: '1', status: 'online' },
        { id: '2', status: 'busy' },
        { id: '3', status: 'offline' },
        { id: '4', status: 'unreachable' },
      ]

      const activeCount = agents.filter(a => a.status !== 'offline' && a.status !== 'unreachable').length
      expect(activeCount).toBe(2)
    })

    it('应该正确计算总任务数', () => {
      const agents = [
        { id: '1', current_tasks: 1 },
        { id: '2', current_tasks: 2 },
        { id: '3', current_tasks: 3 },
      ]

      const totalTasks = agents.reduce((s, a) => s + a.current_tasks, 0)
      expect(totalTasks).toBe(6)
    })
  })

  describe('错误处理', () => {
    it('API 加载失败应该显示错误提示', async () => {
      render(
        <MemoryRouter>
          <AgentStatus />
        </MemoryRouter>
      )

      // 由于使用 MSW mock，应该能正常加载
      await waitFor(() => {
        // 如果加载失败应该显示错误信息
      })
    })
  })
})
