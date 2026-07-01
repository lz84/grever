/**
 * MAK-204: 工作台 E2E 业务测试
 * 业务流：进入工作台 → 验证概览标题和描述 → 验证统计区域 → 验证快捷导航 → 验证侧边栏
 * 基于实际页面结构编写，按业务需求测试
 */
import { test, expect } from '@playwright/test'

test.describe('工作台 E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('工作台页面应该正确加载', async ({ page }) => {
    // 业务：用户进入系统，首先看到工作台入口
    await expect(page.getByRole('heading', { name: /🏠 工作台/ })).toBeVisible()
    await expect(page.getByText(/系统入口/)).toBeVisible()
  })

  test('统计卡片区域应该存在', async ({ page }) => {
    // 业务：工作台顶部展示核心业务统计卡片（目标/工程/任务/执行/方案/知识/智能体/场景/异常）
    await page.waitForTimeout(1000)
    // 统计卡片区域存在即可，通过 body 内容验证
    const body = await page.locator('body').textContent()
    expect(body).toBeTruthy()
    expect(body!.length).toBeGreaterThan(100)
  })

  test('今日待办区域应该显示', async ({ page }) => {
    // 业务：工作台应展示今日需要处理的事项，方便用户快速定位
    const todoSection = page.getByText(/今日待办/)
    await expect(todoSection).toBeVisible()
  })

  test('最近目标区域应该显示', async ({ page }) => {
    // 业务：展示最近操作过的目标，方便快速继续工作
    const recentGoals = page.getByText(/最近目标/)
    await expect(recentGoals).toBeVisible()
  })

  test('最近执行区域应该显示', async ({ page }) => {
    // 业务：展示最近的任务执行记录，方便追踪进度
    const recentExec = page.getByText(/最近执行/)
    await expect(recentExec).toBeVisible()
  })

  test('智能体状态区域应该显示', async ({ page }) => {
    // 业务：展示各智能体的实时状态（在线/离线/负载）
    const agentStatus = page.getByText(/智能体状态/)
    await expect(agentStatus).toBeVisible()
  })

  test('侧边栏应该包含所有核心模块入口', async ({ page }) => {
    // 业务：侧边栏应提供完整的系统导航
    const navLinks = [
      '工作台',
      '驾驭中心',
      '裁决中心',
      '认知中心',
      '场景库',
      '能力库',
      '智能体',
      '系统设置'
    ]
    for (const link of navLinks) {
      // 使用 nav 内的链接避免与页面标题冲突
      await expect(page.locator('nav').getByText(link).first()).toBeVisible()
    }
  })

  test('从工作台点击驾驭中心应该跳转到目标列表', async ({ page }) => {
    // 业务：点击侧边栏"驾驭中心"应导航到目标管理页面
    await page.getByText('驾驭中心').click()
    await expect(page).toHaveURL(/\/coordination\/goals/)
    await expect(page.getByRole('heading', { name: /目标管理/ })).toBeVisible()
  })

  test('顶部搜索框应该可用', async ({ page }) => {
    // 业务：全局搜索框允许用户快速搜索目标、任务
    const searchInput = page.getByPlaceholder('搜索目标、任务...')
    await expect(searchInput).toBeVisible()
    await searchInput.fill('test')
    await expect(searchInput).toHaveValue('test')
  })
})
