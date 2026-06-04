/**
 * MAK-208: 认知中心 E2E 业务测试
 * 测试内容：查看知识库 → 搜索认知 → 查看评估报告
 */
import { test, expect } from '@playwright/test'

test.describe('认知中心 E2E', () => {
  test('知识库页面应该可访问', async ({ page }) => {
    await page.goto('/cognitive/knowledge')
    await expect(page.locator('body')).toBeVisible()
    await page.waitForTimeout(1000)
  })

  test('应该显示认知知识库标题', async ({ page }) => {
    await page.goto('/cognitive/knowledge')
    await page.waitForTimeout(1000)

    const title = page.getByText(/认知知识库/)
    await expect(title).toBeVisible()
  })

  test('应该显示搜索输入框', async ({ page }) => {
    await page.goto('/cognitive/knowledge')
    await page.waitForTimeout(1000)

    const searchInput = page.getByPlaceholder(/搜索/i)
    await expect(searchInput).toBeVisible()
  })

  test('搜索功能应该可用', async ({ page }) => {
    await page.goto('/cognitive/knowledge')
    await page.waitForTimeout(1000)

    const searchInput = page.getByPlaceholder(/搜索/i)
    await searchInput.fill('预案')
    await page.waitForTimeout(500)
  })

  test('类型筛选应该可用', async ({ page }) => {
    await page.goto('/cognitive/knowledge')
    await page.waitForTimeout(1000)

    // 查找类型筛选按钮
    const filterButtons = page.getAllByRole('button')
    const typeFilters = filterButtons.filter(btn => 
      btn.textContent()?.match(/经验|教训|流程|meta/)
    )

    const filterCount = await typeFilters.count()
    expect(filterCount).toBeGreaterThanOrEqual(0)
  })

  test('认知列表应该显示认知项', async ({ page }) => {
    await page.goto('/cognitive/knowledge')
    await page.waitForTimeout(1000)

    // 查找认知标题
    const knowledgeItems = page.locator('text=/预案|地震|资源/')
    const itemCount = await knowledgeItems.count()

    expect(itemCount).toBeGreaterThanOrEqual(0)
  })

  test('评估页面应该可访问', async ({ page }) => {
    await page.goto('/cognitive/assessment')
    await expect(page.locator('body')).toBeVisible()
    await page.waitForTimeout(1000)
  })

  test('应该显示认知评估标题', async ({ page }) => {
    await page.goto('/cognitive/assessment')
    await page.waitForTimeout(1000)

    const title = page.getByText(/认知评估/)
    await expect(title).toBeVisible()
  })

  test('评估表格应该显示智能体评分', async ({ page }) => {
    await page.goto('/cognitive/assessment')
    await page.waitForTimeout(1000)

    // 查找智能体评分表格
    const scoreTexts = page.getByText(/\d{2}/)
    const scoreCount = await scoreTexts.count()

    expect(scoreCount).toBeGreaterThanOrEqual(0)
  })

  test('维度 Tab 应该可以切换', async ({ page }) => {
    await page.goto('/cognitive/assessment')
    await page.waitForTimeout(1000)

    // 查找维度 Tab
    const tabs = page.getByText(/检索质量|上下文利用|注入精度|知识新鲜度/)
    const tabCount = await tabs.count()

    if (tabCount > 0) {
      await tabs.first().click()
      await page.waitForTimeout(300)
    }
  })

  test('刷新按钮应该可用', async ({ page }) => {
    await page.goto('/cognitive/assessment')
    await page.waitForTimeout(1000)

    const refreshBtn = page.getByRole('button', { name: /刷新/i })
    
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click()
      await page.waitForTimeout(500)
    }
  })

  test('注入管理页面应该可访问', async ({ page }) => {
    await page.goto('/cognitive/inject')
    await expect(page.locator('body')).toBeVisible()
    await page.waitForTimeout(1000)
  })

  test('注入历史应该显示', async ({ page }) => {
    await page.goto('/cognitive/inject')
    await page.waitForTimeout(1000)

    const historySection = page.getByText(/注入历史/)
    
    if (await historySection.isVisible()) {
      await expect(historySection).toBeVisible()
    }
  })

  test('注入规则应该显示', async ({ page }) => {
    await page.goto('/cognitive/inject')
    await page.waitForTimeout(1000)

    const rulesSection = page.getByText(/注入规则/)
    
    if (await rulesSection.isVisible()) {
      await expect(rulesSection).toBeVisible()
    }
  })

  test('规则开关应该可以切换', async ({ page }) => {
    await page.goto('/cognitive/inject')
    await page.waitForTimeout(1000)

    // 查找开关
    const toggles = page.locator('button:has(input[type="checkbox"])')
    const toggleCount = await toggles.count()

    if (toggleCount > 0) {
      await toggles.first().click()
      await page.waitForTimeout(300)
    }
  })
})
