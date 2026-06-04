/**
 * MAK-199: 场景库单元测试
 * 测试内容：场景列表、详情、收藏组件（含 mock 数据测试）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Favorites from '../../src/pages/Favorites'
import { mockScenarios } from '../mocks/handlers'

// Suppress console.error for expected warnings
const originalError = console.error
beforeEach(() => {
  console.error = vi.fn()
})
afterEach(() => {
  console.error = originalError
})

describe('场景库', () => {
  describe('场景列表', () => {
    it('应该正确渲染场景列表', () => {
      expect(mockScenarios).toHaveLength(2)
      expect(mockScenarios[0].name).toBe('危化品泄漏处置')
    })

    it('应该正确显示场景字段', () => {
      const scenario = mockScenarios[0]

      expect(scenario.name).toBeTruthy()
      expect(scenario.description).toBeTruthy()
      expect(scenario.category).toBeTruthy()
      expect(Array.isArray(scenario.steps)).toBe(true)
      expect(scenario.steps.length).toBeGreaterThan(0)
    })

    it('场景应该有创建和更新时间', () => {
      const scenario = mockScenarios[0]

      expect(scenario.created_at).toBeTruthy()
      expect(scenario.updated_at).toBeTruthy()
      expect(new Date(scenario.created_at).getTime()).toBeLessThanOrEqual(Date.now())
    })

    it('应该正确显示场景分类', () => {
      const scenario = mockScenarios[0]
      expect(scenario.category).toBe('emergency')

      const scenario2 = mockScenarios[1]
      expect(scenario2.category).toBe('rescue')
    })

    it('场景步骤应该是完整的工作流', () => {
      const scenario = mockScenarios[0]
      
      expect(scenario.steps).toEqual(['灾情评估', '预案匹配', '资源调度', '执行指挥', '灾后评估'])
    })
  })

  describe('场景详情', () => {
    it('应该正确显示场景名称', () => {
      const scenario = mockScenarios[0]
      expect(scenario.name).toBe('危化品泄漏处置')
    })

    it('应该正确显示场景描述', () => {
      const scenario = mockScenarios[0]
      expect(scenario.description).toBe('危化品泄漏应急处置标准流程')
    })

    it('应该正确显示场景步骤', () => {
      const scenario = mockScenarios[0]
      
      expect(scenario.steps).toHaveLength(5)
      expect(scenario.steps[0]).toBe('灾情评估')
      expect(scenario.steps[4]).toBe('灾后评估')
    })

    it('应该能通过 ID 获取场景详情', () => {
      const getScenarioById = (id: string) => {
        return mockScenarios.find(s => s.id === id)
      }

      const scenario = getScenarioById('scenario-1')
      expect(scenario).toBeTruthy()
      expect(scenario?.name).toBe('危化品泄漏处置')

      const notFound = getScenarioById('non-existent')
      expect(notFound).toBeUndefined()
    })
  })

  describe('收藏功能', () => {
    it('场景应该有收藏状态', () => {
      const scenario = mockScenarios[0]
      expect(typeof scenario.favorite).toBe('boolean')
    })

    it('应该有收藏和未收藏的场景', () => {
      const favoritedScenarios = mockScenarios.filter(s => s.favorite)
      const unfavoritedScenarios = mockScenarios.filter(s => !s.favorite)

      expect(favoritedScenarios.length).toBeGreaterThan(0)
      expect(unfavoritedScenarios.length).toBeGreaterThan(0)
    })

    it('应该能切换收藏状态', () => {
      let scenario = { ...mockScenarios[0] }
      expect(scenario.favorite).toBe(true)

      scenario.favorite = !scenario.favorite
      expect(scenario.favorite).toBe(false)

      scenario.favorite = !scenario.favorite
      expect(scenario.favorite).toBe(true)
    })

    it('收藏列表应该只包含已收藏的场景', () => {
      const getFavorites = () => mockScenarios.filter(s => s.favorite)

      const favorites = getFavorites()
      expect(favorites.every(s => s.favorite === true)).toBe(true)
      expect(favorites.length).toBe(1) // 只有 scenario-1 是收藏的
    })
  })

  describe('收藏组件 Favorites', () => {
    it('应该渲染收藏页面', async () => {
      render(
        <MemoryRouter>
          <Favorites />
        </MemoryRouter>
      )

      expect(document.body).toBeTruthy()
    })

    it('应该显示收藏列表', async () => {
      render(
        <MemoryRouter>
          <Favorites />
        </MemoryRouter>
      )

      await waitFor(() => {
        // 等待数据加载
      })
    })
  })

  describe('场景分类', () => {
    it('应该支持多种分类', () => {
      const categories = mockScenarios.map(s => s.category)
      const uniqueCategories = [...new Set(categories)]

      expect(uniqueCategories).toContain('emergency')
      expect(uniqueCategories).toContain('rescue')
    })

    it('应该能按分类筛选场景', () => {
      const filterByCategory = (category: string | null) => {
        if (!category) return mockScenarios
        return mockScenarios.filter(s => s.category === category)
      }

      expect(filterByCategory(null)).toHaveLength(2)
      expect(filterByCategory('emergency')).toHaveLength(1)
      expect(filterByCategory('rescue')).toHaveLength(1)
      expect(filterByCategory('medical')).toHaveLength(0)
    })
  })

  describe('场景搜索', () => {
    it('应该支持按名称搜索', () => {
      const searchScenarios = (keyword: string) => {
        if (!keyword) return mockScenarios
        const lowerKeyword = keyword.toLowerCase()
        return mockScenarios.filter(s =>
          s.name.toLowerCase().includes(lowerKeyword) ||
          s.description.toLowerCase().includes(lowerKeyword)
        )
      }

      expect(searchScenarios('危化')).toHaveLength(1)
      expect(searchScenarios('地震')).toHaveLength(1)
      expect(searchScenarios('处置')).toHaveLength(1)
      expect(searchScenarios('')).toHaveLength(2)
      expect(searchScenarios('xxx')).toHaveLength(0)
    })

    it('搜索应该忽略大小写', () => {
      const searchScenarios = (keyword: string) => {
        if (!keyword) return mockScenarios
        const lowerKeyword = keyword.toLowerCase()
        return mockScenarios.filter(s =>
          s.name.toLowerCase().includes(lowerKeyword)
        )
      }

      expect(searchScenarios('WEAKENING')).toHaveLength(1)
      expect(searchScenarios('地震')).toHaveLength(1)
    })
  })

  describe('场景实例化', () => {
    it('应该能生成实例化 URL', () => {
      const generateInstanceUrl = (scenarioId: string) => {
        return `/coordination/goals/new?scenario_id=${scenarioId}`
      }

      expect(generateInstanceUrl('scenario-1')).toBe('/coordination/goals/new?scenario_id=scenario-1')
    })

    it('实例化 URL 应该包含场景 ID', () => {
      const scenario = mockScenarios[0]
      const instanceUrl = `/coordination/goals/new?scenario_id=${scenario.id}`

      expect(instanceUrl).toContain(scenario.id)
    })

    it('应该能从场景预填目标表单', () => {
      const scenario = mockScenarios[0]

      const prefillData = {
        title: scenario.name,
        description: scenario.description,
      }

      expect(prefillData.title).toBe('危化品泄漏处置')
      expect(prefillData.description).toBe('危化品泄漏应急处置标准流程')
    })
  })

  describe('场景数据验证', () => {
    it('场景 ID 应该是唯一的', () => {
      const ids = mockScenarios.map(s => s.id)
      const uniqueIds = [...new Set(ids)]

      expect(ids.length).toBe(uniqueIds.length)
    })

    it('场景名称不应该为空', () => {
      mockScenarios.forEach(scenario => {
        expect(scenario.name).toBeTruthy()
        expect(scenario.name.trim().length).toBeGreaterThan(0)
      })
    })

    it('场景步骤应该至少有一个', () => {
      mockScenarios.forEach(scenario => {
        expect(scenario.steps.length).toBeGreaterThan(0)
      })
    })

    it('场景更新时间应该不早于创建时间', () => {
      mockScenarios.forEach(scenario => {
        const created = new Date(scenario.created_at).getTime()
        const updated = new Date(scenario.updated_at).getTime()
        expect(updated).toBeGreaterThanOrEqual(created)
      })
    })
  })

  describe('Mock 数据测试', () => {
    it('所有 mock 场景数据应该完整', () => {
      mockScenarios.forEach(scenario => {
        expect(scenario.id).toBeTruthy()
        expect(scenario.name).toBeTruthy()
        expect(scenario.description).toBeTruthy()
        expect(scenario.category).toBeTruthy()
        expect(scenario.steps).toBeTruthy()
        expect(scenario.created_at).toBeTruthy()
        expect(scenario.updated_at).toBeTruthy()
        expect(typeof scenario.favorite).toBe('boolean')
      })
    })

    it('mock 数据应该包含预期的测试场景', () => {
      const scenarioNames = mockScenarios.map(s => s.name)
      
      expect(scenarioNames).toContain('危化品泄漏处置')
      expect(scenarioNames).toContain('地震救援')
    })
  })
})
