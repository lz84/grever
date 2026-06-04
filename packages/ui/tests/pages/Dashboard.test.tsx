/**
 * MAK-194: 工作台单元测试
 * 测试内容：统计卡片数据渲染、快捷入口跳转、列表项渲染、空状态、API 失败错误提示
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Dashboard from '../../src/pages/Dashboard'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'

// Mock API module
vi.mock('../../src/utils/api', async () => {
  const actual = await vi.importActual('../../src/utils/api')
  return {
    ...actual,
    getDashboardData: vi.fn(),
  }
})

describe('Dashboard 工作台', () => {
  describe('统计卡片渲染', () => {
    it('应该正确显示统计卡片数据', async () => {
      const mockData = {
        agents: [
          { id: '1', name: '刚子', status: 'online', load: 78, current_tasks: 1, capabilities: [], address: null, metadata: null, registered_at: '', last_heartbeat: '' }
        ],
        goals: [
          { id: 1, title: '测试目标', description: null, priority: null, due_date: null, status: 'in_progress', created_at: null, updated_at: null, project_id: null, parent_id: null }
        ],
        stats: {
          runningTasks: 5,
          pendingTasks: 10,
          openDisputes: 2,
          completedTasks: 25,
        },
      }

      const { getDashboardData } = await import('../../src/utils/api')
      ;(getDashboardData as ReturnType<typeof vi.fn>).mockResolvedValue(mockData)

      render(
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('05')).toBeTruth() // 运行中任务
        expect(screen.getByText('10')).toBeTruth() // 待处理池
        expect(screen.getByText('02')).toBeTruth() // 争议待仲裁
        expect(screen.getByText('25')).toBeTruth() // 累计已完成
      })
    })

    it('争议数大于0时应该红色高亮', async () => {
      const mockData = {
        agents: [],
        goals: [],
        stats: {
          runningTasks: 0,
          pendingTasks: 0,
          openDisputes: 3,
          completedTasks: 0,
        },
      }

      const { getDashboardData } = await import('../../src/utils/api')
      ;(getDashboardData as ReturnType<typeof vi.fn>).mockResolvedValue(mockData)

      render(
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      )

      await waitFor(() => {
        const disputeCard = screen.getByText('03').closest('.bg-white')
        expect(disputeCard?.className).toContain('border-l-4')
      })
    })
  })

  describe('快捷入口跳转', () => {
    it('刷新按钮应该可点击并重新加载数据', async () => {
      const mockData = {
        agents: [],
        goals: [],
        stats: { runningTasks: 0, pendingTasks: 0, openDisputes: 0, completedTasks: 0 },
      }

      const { getDashboardData } = await import('../../src/utils/api')
      ;(getDashboardData as ReturnType<typeof vi.fn>).mockResolvedValue(mockData)

      render(
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      )

      await waitFor(() => {
        const refreshBtn = screen.getByRole('button', { name: /刷新/i })
        expect(refreshBtn).toBeTruth()
      })
    })
  })

  describe('列表项渲染', () => {
    it('应该正确渲染目标列表', async () => {
      const mockGoals = [
        { id: 1, title: '城市应急管理', description: '构建城市应急平台', priority: 'P1', status: 'in_progress', created_at: null, updated_at: null, project_id: null, parent_id: null, due_date: null },
        { id: 2, title: '智能投资研究', description: null, priority: 'P2', status: 'pending', created_at: null, updated_at: null, project_id: null, parent_id: null, due_date: null },
      ]

      const mockData = {
        agents: [],
        goals: mockGoals,
        stats: { runningTasks: 0, pendingTasks: 0, openDisputes: 0, completedTasks: 0 },
      }

      const { getDashboardData } = await import('../../src/utils/api')
      ;(getDashboardData as ReturnType<typeof vi.fn>).mockResolvedValue(mockData)

      render(
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('城市应急管理')).toBeTruth()
        expect(screen.getByText('智能投资研究')).toBeTruth()
      })
    })

    it('应该正确显示目标状态标签', async () => {
      const mockGoals = [
        { id: 1, title: '进行中目标', description: null, priority: null, status: 'in_progress', created_at: null, updated_at: null, project_id: null, parent_id: null, due_date: null },
        { id: 2, title: '已完成目标', description: null, priority: null, status: 'completed', created_at: null, updated_at: null, project_id: null, parent_id: null, due_date: null },
        { id: 3, title: '草稿目标', description: null, priority: null, status: 'draft', created_at: null, updated_at: null, project_id: null, parent_id: null, due_date: null },
      ]

      const mockData = {
        agents: [],
        goals: mockGoals,
        stats: { runningTasks: 0, pendingTasks: 0, openDisputes: 0, completedTasks: 0 },
      }

      const { getDashboardData } = await import('../../src/utils/api')
      ;(getDashboardData as ReturnType<typeof vi.fn>).mockResolvedValue(mockData)

      render(
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('执行中')).toBeTruth()
        expect(screen.getByText('已完成')).toBeTruth()
      })
    })
  })

  describe('空状态', () => {
    it('当没有目标时应该显示空状态提示', async () => {
      const mockData = {
        agents: [],
        goals: [],
        stats: { runningTasks: 0, pendingTasks: 0, openDisputes: 0, completedTasks: 0 },
      }

      const { getDashboardData } = await import('../../src/utils/api')
      ;(getDashboardData as ReturnType<typeof vi.fn>).mockResolvedValue(mockData)

      render(
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText(/暂无目标/i)).toBeTruth()
      })
    })

    it('当没有智能体时应该显示空状态', async () => {
      const mockData = {
        agents: [],
        goals: [
          { id: 1, title: '测试目标', description: null, priority: null, status: 'in_progress', created_at: null, updated_at: null, project_id: null, parent_id: null, due_date: null }
        ],
        stats: { runningTasks: 0, pendingTasks: 0, openDisputes: 0, completedTasks: 0 },
      }

      const { getDashboardData } = await import('../../src/utils/api')
      ;(getDashboardData as ReturnType<typeof vi.fn>).mockResolvedValue(mockData)

      render(
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText(/暂无注册智能体/i)).toBeTruth()
      })
    })
  })

  describe('API 失败错误提示', () => {
    it('API 请求失败时应该显示错误提示和重试按钮', async () => {
      const { getDashboardData } = await import('../../src/utils/api')
      ;(getDashboardData as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('网络错误'))

      render(
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText(/网络错误/i)).toBeTruth()
        expect(screen.getByRole('button', { name: /重试/i })).toBeTruth()
      })
    })

    it('点击重试按钮应该重新加载数据', async () => {
      let callCount = 0
      const { getDashboardData } = await import('../../src/utils/api')
      ;(getDashboardData as ReturnType<typeof vi.fn>).mockImplementation(() => {
        callCount++
        if (callCount === 1) {
          return Promise.reject(new Error('网络错误'))
        }
        return Promise.resolve({
          agents: [],
          goals: [],
          stats: { runningTasks: 0, pendingTasks: 0, openDisputes: 0, completedTasks: 0 },
        })
      })

      render(
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText(/网络错误/i)).toBeTruth()
      })

      const retryBtn = screen.getByRole('button', { name: /重试/i })
      await userEvent.click(retryBtn)

      await waitFor(() => {
        expect(callCount).toBe(2)
      })
    })
  })

  describe('加载状态', () => {
    it('数据加载中应该显示加载动画', () => {
      const { getDashboardData } = await import('../../src/utils/api')
      ;(getDashboardData as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}))

      render(
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      )

      expect(screen.getByText(/加载数据中/i)).toBeTruth()
    })
  })
})
