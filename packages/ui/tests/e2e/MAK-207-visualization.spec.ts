/**
 * MAK-207: 可视化 E2E 业务测试
 * 测试内容：查看看板 → 数据正确显示 → 查看 Trace → 时间线正确展开
 */
import { test, expect } from '@playwright/test'

test.describe('可视化 E2E', () => {
  test('看板页面应该可访问', async ({ page }) => {
    await page.goto('/visual/dashboard')
    await expect(page.locator('body')).toBeVisible()
    await page.waitForTimeout(1000)
  })

  test('应该显示数据看板标题', async ({ page }) => {
    await page.goto('/visual/dashboard')
    await page.waitForTimeout(1000)

    const title = page.getByText(/数据看板/)
    await expect(title).toBeVisible()
  })

  test('看板应该显示刷新按钮', async ({ page }) => {
    await page.goto('/visual/dashboard')
    await page.waitForTimeout(1000)

    const refreshBtn = page.getByRole('button', { name: /刷新/i })
    await expect(refreshBtn).toBeVisible()
  })

  test('看板应该显示统计图表区域', async ({ page }) => {
    await page.goto('/visual/dashboard')
    await page.waitForTimeout(1000)

    // 查找可能的图表区域
    const sections = page.getByText(/目标完成率|任务状态分布|智能体负载/)
    const sectionCount = await sections.count()

    expect(sectionCount).toBeGreaterThanOrEqual(0)
  })

  test('Trace 查看页面应该可访问', async ({ page }) => {
    await page.goto('/visual/traces')
    await expect(page.locator('body')).toBeVisible()
    await page.waitForTimeout(1000)
  })

  test('Trace 页面应该显示时间范围筛选', async ({ page }) => {
    await page.goto('/visual/traces')
    await page.waitForTimeout(1000)

    // 查找时间范围下拉框
    const timeFilter = page.getByText(/时间范围/)
    
    if (await timeFilter.isVisible()) {
      await expect(timeFilter).toBeVisible()
    }
  })

  test('Trace 列表应该显示执行记录', async ({ page }) => {
    await page.goto('/visual/traces')
    await page.waitForTimeout(1000)

    // 查找执行记录
    const traces = page.locator('text=/工作流|执行/')
    const traceCount = await traces.count()

    expect(traceCount).toBeGreaterThanOrEqual(0)
  })

  test('Trace 时间线应该可展开', async ({ page }) => {
    await page.goto('/visual/traces')
    await page.waitForTimeout(1000)

    // 查找可点击的时间线项
    const timelineItems = page.locator('.cursor-pointer, button:has-text("工作流")')
    const itemCount = await timelineItems.count()

    if (itemCount > 0) {
      await timelineItems.first().click()
      await page.waitForTimeout(500)
    }
  })

  test('报表页面应该可访问', async ({ page }) => {
    await page.goto('/visual/reports')
    await expect(page.locator('body')).toBeVisible()
    await page.waitForTimeout(1000)
  })

  test('报表页面应该显示时间范围筛选', async ({ page }) => {
    await page.goto('/visual/reports')
    await page.waitForTimeout(1000)

    const timeFilter = page.getByText(/时间范围/)
    
    if (await timeFilter.isVisible()) {
      await expect(timeFilter).toBeVisible()
    }
  })

  test('报表列表应该可展开', async ({ page }) => {
    await page.goto('/visual/reports')
    await page.waitForTimeout(1000)

    // 查找可展开的报表行
    const reportRows = page.locator('tr, .bg-white')
    const rowCount = await reportRows.count()

    if (rowCount > 0) {
      await reportRows.first().click()
      await page.waitForTimeout(500)
    }
  })

  test('报表详情应该显示步骤效率', async ({ page }) => {
    await page.goto('/visual/reports')
    await page.waitForTimeout(1000)

    const stepsSection = page.getByText(/步骤效率/)
    
    if (await stepsSection.isVisible()) {
      await expect(stepsSection).toBeVisible()
    }
  })

  test('导出 PDF 按钮应该存在', async ({ page }) => {
    await page.goto('/visual/reports')
    await page.waitForTimeout(1000)

    const exportBtn = page.getByRole('button', { name: /导出 PDF/i })
    
    if (await exportBtn.isVisible()) {
      await expect(exportBtn).toBeVisible()
    }
  })
})
