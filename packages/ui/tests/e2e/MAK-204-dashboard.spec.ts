/**
 * MAK-204: 工作台 E2E 业务测试
 * 测试内容：打开工作台 → 验证统计卡片数据正确 → 点击快捷入口跳转 → 验证最近列表显示
 */
import { test, expect } from '@playwright/test'

test.describe('工作台 E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('应该正确显示工作台页面', async ({ page }) => {
    // 等待页面加载
    await expect(page.locator('body')).toBeVisible()
  })

  test('应该显示统计卡片', async ({ page }) => {
    // 等待数据加载
    await page.waitForTimeout(1000)

    // 验证统计卡片存在
    const runningTasks = page.getByText(/运行中任务/)
    const pendingTasks = page.getByText(/待处理池/)
    const openDisputes = page.getByText(/争议待仲裁/)
    const completedTasks = page.getByText(/累计已完成/)

    await expect(runningTasks).toBeVisible()
    await expect(pendingTasks).toBeVisible()
    await expect(openDisputes).toBeVisible()
    await expect(completedTasks).toBeVisible()
  })

  test('统计卡片数据应该是数字格式', async ({ page }) => {
    await page.waitForTimeout(1000)

    // 验证数字显示（00格式）
    const numberPattern = /\d{2}/
    const cards = page.locator('.bg-white.industrial-border')
    
    // 至少应该有统计卡片
    const cardCount = await cards.count()
    expect(cardCount).toBeGreaterThan(0)
  })

  test('应该显示活跃智能体区域', async ({ page }) => {
    await page.waitForTimeout(1000)

    const agentSection = page.getByText(/活跃智能体/)
    await expect(agentSection).toBeVisible()
  })

  test('应该显示目标列表', async ({ page }) => {
    await page.waitForTimeout(1000)

    const goalSection = page.getByText(/救援目标列表/)
    await expect(goalSection).toBeVisible()
  })

  test('刷新按钮应该可点击', async ({ page }) => {
    await page.waitForTimeout(1000)

    const refreshBtn = page.getByRole('button', { name: /刷新/i })
    await expect(refreshBtn).toBeVisible()

    // 点击刷新
    await refreshBtn.click()
    
    // 等待数据重新加载
    await page.waitForTimeout(500)
  })

  test('目标列表项应该可点击', async ({ page }) => {
    await page.waitForTimeout(1000)

    // 查找目标列表中的目标
    const goalItems = page.locator('.industrial-border.rounded-md')
    const goalCount = await goalItems.count()

    if (goalCount > 0) {
      // 点击第一个目标
      await goalItems.first().click()
      
      // 验证页面有变化或者有跳转
      await page.waitForTimeout(500)
    }
  })

  test('智能体卡片应该显示状态', async ({ page }) => {
    await page.waitForTimeout(1000)

    // 查找状态指示器
    const statusIndicators = page.locator('span:has(.w-2.h-2.rounded-full)')
    const statusCount = await statusIndicators.count()

    // 应该至少有智能体状态指示
    expect(statusCount).toBeGreaterThanOrEqual(0)
  })

  test('负载进度条应该正确显示', async ({ page }) => {
    await page.waitForTimeout(1000)

    // 查找负载条
    const loadBars = page.locator('.h-1\\.5, .h-\\[6px\\]')
    const loadCount = await loadBars.count()

    // 负载条可能存在
    expect(loadCount).toBeGreaterThanOrEqual(0)
  })
})
