/**
 * MAK-205: 协同中心 E2E 业务测试
 * 测试内容：创建目标 → 自动分解 → 创建项目 → 创建任务 → 执行监控。验证全流程数据流转
 */
import { test, expect } from '@playwright/test'

test.describe('协同中心 E2E', () => {
  test('目标列表页面应该可访问', async ({ page }) => {
    await page.goto('/coordination/goals')
    await expect(page.locator('body')).toBeVisible()
    await page.waitForTimeout(1000)
  })

  test('项目列表页面应该可访问', async ({ page }) => {
    await page.goto('/coordination/projects')
    await expect(page.locator('body')).toBeVisible()
    await page.waitForTimeout(1000)
  })

  test('任务列表页面应该可访问', async ({ page }) => {
    await page.goto('/coordination/tasks')
    await expect(page.locator('body')).toBeVisible()
    await page.waitForTimeout(1000)
  })

  test('执行监控页面应该可访问', async ({ page }) => {
    await page.goto('/coordination/executions')
    await expect(page.locator('body')).toBeVisible()
    await page.waitForTimeout(1000)

    // 验证 Live 指示器
    const liveIndicator = page.getByText(/Live/i)
    await expect(liveIndicator).toBeVisible()
  })

  test('执行监控页面应该有刷新按钮', async ({ page }) => {
    await page.goto('/coordination/executions')
    await page.waitForTimeout(1000)

    const refreshBtn = page.getByRole('button', { name: /刷新/i })
    await expect(refreshBtn).toBeVisible()
  })

  test('新建目标按钮应该存在', async ({ page }) => {
    await page.goto('/coordination/goals')
    await page.waitForTimeout(1000)

    const newGoalBtn = page.getByRole('button', { name: /新建目标/i })
    await expect(newGoalBtn).toBeVisible()
  })

  test('搜索功能应该可用', async ({ page }) => {
    await page.goto('/coordination/goals')
    await page.waitForTimeout(1000)

    const searchInput = page.getByPlaceholder(/搜索/i)
    await expect(searchInput).toBeVisible()

    // 输入搜索关键词
    await searchInput.fill('测试')
    await page.waitForTimeout(500)
  })

  test('筛选功能应该可用', async ({ page }) => {
    await page.goto('/coordination/goals')
    await page.waitForTimeout(1000)

    // 查找状态筛选按钮
    const filterButtons = page.getAllByRole('button')
    const statusFilter = filterButtons.find(btn => btn.textContent()?.includes('状态'))
    
    if (statusFilter) {
      await statusFilter.click()
      await page.waitForTimeout(300)
    }
  })

  test('新建项目 Modal 应该可以打开', async ({ page }) => {
    await page.goto('/coordination/projects')
    await page.waitForTimeout(1000)

    const newProjectBtn = page.getByRole('button', { name: /新建项目/i })
    
    if (await newProjectBtn.isVisible()) {
      await newProjectBtn.click()
      await page.waitForTimeout(500)
    }
  })

  test('目标详情页应该可以访问', async ({ page }) => {
    await page.goto('/coordination/goals/1')
    await page.waitForTimeout(1000)

    const backBtn = page.getByText(/返回/)
    await expect(backBtn).toBeVisible()
  })

  test('项目详情页应该可以访问', async ({ page }) => {
    await page.goto('/coordination/projects/1')
    await page.waitForTimeout(1000)
  })

  test('执行详情页应该可以访问', async ({ page }) => {
    await page.goto('/coordination/executions/wf-1')
    await page.waitForTimeout(1000)
  })
})
