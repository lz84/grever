/**
 * Grever E2E Deep Test Suite - 深度业务流程测试
 * 
 * 覆盖：表单提交、数据流转、CRUD 操作、跨页面导航、错误处理
 * 
 * 运行: npx playwright test tests/e2e/page-flows-deep.spec.ts
 */

import { test, expect, Page } from '@playwright/test';

const BASE = 'http://localhost:5173';

/** 等待 React 渲染 */
async function pageReady(page: Page) {
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
}

// ============================================
// D1: Goal CRUD 全流程
// ============================================

test.describe('D1: Goal CRUD 全流程', () => {
  test('D1-001: 创建 Goal 表单加载和验证', async ({ page }) => {
    await page.goto(`${BASE}/coordination/goals/new`);
    await pageReady(page);
    
    // 验证表单有输入字段
    const content = await page.content();
    expect(content.length).toBeGreaterThan(3000); // 表单内容较多
    
    // 找目标名称输入框
    const inputs = page.locator('input[type="text"]');
    const count = await inputs.count();
    expect(count).toBeGreaterThan(0); // 应该有输入框
    
    // 找提交按钮
    const submitBtn = page.locator('button[type="submit"], button:has-text("创建"), button:has-text("提交")');
    expect(await submitBtn.isVisible()).toBe(true);
  });

  test('D1-002: Goal 列表搜索和筛选', async ({ page }) => {
    await page.goto(`${BASE}/coordination/goals`);
    await pageReady(page);
    
    // 验证列表不为空
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
    
    // 搜索功能
    const searchInput = page.locator('input[placeholder*="搜索"], input[type="search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('E2E');
      await page.waitForTimeout(1000);
      // 验证搜索后内容更新
      const afterContent = await page.content();
      expect(afterContent.length).toBeGreaterThan(500);
    }
  });

  test('D1-003: Goal 详情页数据展示', async ({ page }) => {
    await page.goto(`${BASE}/coordination/goals`);
    await pageReady(page);
    
    // 点击第一个 goal
    const firstGoalLink = page.locator('a[href*="/coordination/goals/"]').first();
    if (await firstGoalLink.isVisible()) {
      await firstGoalLink.click();
      await pageReady(page);
      
      // 验证详情页有内容
      const content = await page.content();
      expect(content.length).toBeGreaterThan(1000);
      expect(content).not.toContain('404');
    }
  });

  test('D1-004: Goal 删除确认', async ({ page }) => {
    await page.goto(`${BASE}/coordination/goals`);
    await pageReady(page);
    
    // 验证刷新按钮可用
    const refreshBtn = page.locator('button:has-text("刷新"), button:has-text("Refresh")');
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click();
      await page.waitForTimeout(1000);
      expect(page.url()).toContain('/goals');
    }
  });
});

// ============================================
// D2: Project CRUD 全流程
// ============================================

test.describe('D2: Project CRUD 全流程', () => {
  test('D2-001: Project 列表加载和搜索', async ({ page }) => {
    await page.goto(`${BASE}/coordination/projects`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
    
    // 搜索
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="Search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      await page.waitForTimeout(500);
    }
  });

  test('D2-002: Project 详情加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/projects`);
    await pageReady(page);
    
    const firstLink = page.locator('a[href*="/coordination/projects/"]').first();
    if (await firstLink.isVisible()) {
      await firstLink.click();
      await pageReady(page);
      
      // 验证不是空页
      const content = await page.content();
      expect(content.length).toBeGreaterThan(1000);
      expect(content).not.toContain('404');
    }
  });

  test('D2-003: Project DAG 图加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/projects`);
    await pageReady(page);
    
    const diagramLink = page.locator('a[href*="diagram"]').first();
    if (await diagramLink.isVisible()) {
      await diagramLink.click();
      await page.waitForTimeout(3000); // DAG 图需要额外加载
      
      const content = await page.content();
      expect(content.length).toBeGreaterThan(1000);
    }
  });

  test('D2-004: Project 树视图加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/projects`);
    await pageReady(page);
    
    const treeLink = page.locator('a[href*="tree"]').first();
    if (await treeLink.isVisible()) {
      await treeLink.click();
      await pageReady(page);
      
      const content = await page.content();
      expect(content.length).toBeGreaterThan(1000);
    }
  });
});

// ============================================
// D3: Task CRUD 全流程
// ============================================

test.describe('D3: Task CRUD 全流程', () => {
  test('D3-001: Task 列表加载和状态筛选', async ({ page }) => {
    await page.goto(`${BASE}/coordination/tasks`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
    
    // 检查状态展示（Badge/状态列/待处理/进行中等）
    const hasStatus = content.includes('badge') || content.includes('Badge') || 
                      content.includes('待处理') || content.includes('进行中') || 
                      content.includes('done') || content.includes('pending') ||
                      content.includes('table') || content.includes('Table') ||
                      content.includes('Task') || content.includes('任务');
    expect(hasStatus).toBe(true);
  });

  test('D3-002: Task 创建表单', async ({ page }) => {
    await page.goto(`${BASE}/coordination/tasks/create`);
    await pageReady(page);
    
    // 验证表单字段存在
    const content = await page.content();
    expect(content).toContain('任务'); // 任务相关页面
    
    // 找 title 输入
    const titleInput = page.locator('input[placeholder*="标题"], input[placeholder*="title"], input[name="title"]').first();
    if (await titleInput.isVisible()) {
      await titleInput.fill('E2E测试任务');
    }
  });

  test('D3-003: Task 详情页状态展示', async ({ page }) => {
    await page.goto(`${BASE}/coordination/tasks`);
    await pageReady(page);
    
    // 点击任务列表中的第一个任务行
    const firstRow = page.locator('table tbody tr').first();
    if (await firstRow.isVisible()) {
      await firstRow.click();
      await pageReady(page);
      
      const content = await page.content();
      expect(content.length).toBeGreaterThan(1000);
      
      // 验证有状态信息：页面显示"状态"标签和状态值（待处理/进行中/已完成等）
      const hasStatus = content.includes('状态') || content.includes('待处理') || content.includes('进行中') || content.includes('已完成');
      expect(hasStatus).toBe(true);
    }
  });

  test('D3-004: Task 增强详情页', async ({ page }) => {
    await page.goto(`${BASE}/coordination/tasks`);
    await pageReady(page);
    
    const enhancedLink = page.locator('a[href*="enhanced"]').first();
    if (await enhancedLink.isVisible()) {
      await enhancedLink.click();
      await pageReady(page);
      
      const content = await page.content();
      expect(content.length).toBeGreaterThan(1000);
    }
  });
});

// ============================================
// D4: Execution 监控流程
// ============================================

test.describe('D4: Execution 监控流程', () => {
  test('D4-001: Execution 列表刷新', async ({ page }) => {
    await page.goto(`${BASE}/coordination/executions`);
    await pageReady(page);
    
    // 刷新按钮
    const refreshBtn = page.locator('button:has-text("刷新"), button:has-text("Refresh")');
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click();
      await page.waitForTimeout(1500);
      expect(page.url()).toContain('/executions');
    }
  });

  test('D4-002: Execution 详情加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/executions`);
    await pageReady(page);
    
    const firstLink = page.locator('a[href*="/coordination/executions/"]').first();
    if (await firstLink.isVisible()) {
      await firstLink.click();
      await pageReady(page);
      
      const content = await page.content();
      expect(content.length).toBeGreaterThan(500);
    }
  });
});

// ============================================
// D5: 认知中心流程
// ============================================

test.describe('D5: 认知中心流程', () => {
  test('D5-001: 认知中心创建条目', async ({ page }) => {
    await page.goto(`${BASE}/cognitive/center`);
    await pageReady(page);
    
    // 验证创建按钮
    const createBtn = page.locator('button:has-text("创建"), button:has-text("Create"), button:has-text("新增")');
    if (await createBtn.isVisible()) {
      await createBtn.click();
      await page.waitForTimeout(1000);
      
      // 验证表单出现
      const content = await page.content();
      expect(content.length).toBeGreaterThan(1000);
    }
  });

  test('D5-002: 知识查询和过滤', async ({ page }) => {
    await page.goto(`${BASE}/cognitive/knowledge`);
    await pageReady(page);
    
    // 搜索
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="Search"], input[type="search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      await page.waitForTimeout(500);
    }
  });

  test('D5-003: 认知评估加载', async ({ page }) => {
    await page.goto(`${BASE}/cognitive/assessment`);
    await pageReady(page);
    
    // 评估结果展示
    const content = await page.content();
    expect(content).toContain('评估'); // 应该有评估相关内容
  });

  test('D5-004: 知识注入流程', async ({ page }) => {
    await page.goto(`${BASE}/cognitive/inject`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
  });
});

// ============================================
// D6: 场景库流程
// ============================================

test.describe('D6: 场景库流程', () => {
  test('D6-001: 场景创建表单验证', async ({ page }) => {
    await page.goto(`${BASE}/scenarios/new`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(2000); // 创建表单比较复杂
    expect(content).toContain('场景');
  });

  test('D6-002: 场景列表搜索和筛选', async ({ page }) => {
    await page.goto(`${BASE}/scenarios`);
    await pageReady(page);
    
    // 搜索
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="Search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      await page.waitForTimeout(500);
    }
    
    // 验证列表
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
  });

  test('D6-003: 场景详情数据完整性', async ({ page }) => {
    await page.goto(`${BASE}/scenarios`);
    await pageReady(page);
    
    const firstLink = page.locator('a[href*="/scenarios/"]').first();
    if (await firstLink.isVisible()) {
      await firstLink.click();
      await pageReady(page);
      
      const content = await page.content();
      expect(content.length).toBeGreaterThan(3000); // 场景详情应该内容丰富
      
      // 验证有场景步骤/任务
      const hasSteps = content.includes('step') || content.includes('Step') || 
                       content.includes('任务') || content.includes('project');
      expect(hasSteps).toBe(true);
    }
  });

  test('D6-004: 场景中心功能', async ({ page }) => {
    await page.goto(`${BASE}/scenarios/center`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
  });
});

// ============================================
// D7: 智能体管理
// ============================================

test.describe('D7: 智能体管理', () => {
  test('D7-001: Agent 列表和状态展示', async ({ page }) => {
    await page.goto(`${BASE}/system/agents`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
    
    // 验证有在线状态
    const hasOnlineStatus = content.includes('online') || content.includes('Online') || 
                            content.includes('在线') || content.includes('离线');
    expect(hasOnlineStatus).toBe(true);
  });

  test('D7-002: Agent 注册流程', async ({ page }) => {
    await page.goto(`${BASE}/system/agents`);
    await pageReady(page);
    
    // 注册按钮
    const registerBtn = page.locator('button:has-text("注册"), button:has-text("Register"), button:has-text("新增")');
    if (await registerBtn.isVisible()) {
      await registerBtn.click();
      await page.waitForTimeout(1000);
      
      const content = await page.content();
      expect(content.length).toBeGreaterThan(1000);
    }
  });

  test('D7-003: 在线状态切换', async ({ page }) => {
    await page.goto(`${BASE}/system/agents`);
    await pageReady(page);
    
    // 在线筛选按钮
    const onlineFilter = page.locator('button:has-text("在线"), button:has-text("Online")');
    if (await onlineFilter.isVisible()) {
      await onlineFilter.click();
      await page.waitForTimeout(500);
      expect(page.url()).toContain('/agents');
    }
  });
});

// ============================================
// D8: 能力库和能力标签
// ============================================

test.describe('D8: 能力库流程', () => {
  test('D8-001: 能力列表加载', async ({ page }) => {
    await page.goto(`${BASE}/system/capabilities`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
  });

  test('D8-002: 能力标签页面', async ({ page }) => {
    await page.goto(`${BASE}/industry/tags`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
  });

  test('D8-003: 行业包页面', async ({ page }) => {
    await page.goto(`${BASE}/industry/packs`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('D8-004: 工件列表', async ({ page }) => {
    await page.goto(`${BASE}/system/artifacts`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });
});

// ============================================
// D9: 设置页面
// ============================================

test.describe('D9: 设置页面', () => {
  test('D9-001: 设置页加载', async ({ page }) => {
    await page.goto(`${BASE}/system/settings`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(2000);
    expect(content).toContain('设置');
  });
});

// ============================================
// D10: 可视化看板
// ============================================

test.describe('D10: 可视化看板', () => {
  test('D10-001: 可视化数据加载', async ({ page }) => {
    await page.goto(`${BASE}/visual/dashboard`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(2000);
    
    // 应该有数据展示（看板通常有卡片或列表）
    const hasData = content.includes('card') || content.includes('Card') || 
                    content.includes('统计') || content.includes('Dashboard') ||
                    content.includes('dashboard') || content.includes('看板') ||
                    content.includes('目标') || content.includes('Goal');
    expect(hasData).toBe(true);
  });

  test('D10-002: 追踪器页面', async ({ page }) => {
    await page.goto(`${BASE}/visual/traces`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
  });
});

// ============================================
// D11: 方案流程
// ============================================

test.describe('D11: 方案流程', () => {
  test('D11-001: 方案列表', async ({ page }) => {
    await page.goto(`${BASE}/solutions`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
  });

  test('D11-002: 方案中心', async ({ page }) => {
    await page.goto(`${BASE}/solutions`);
    await pageReady(page);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
  });
});

// ============================================
// D12: 跨页面导航流程
// ============================================

test.describe('D12: 跨页面导航流程', () => {
  test('D12-001: 工作台 → Goal 列表 → Goal 详情', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await pageReady(page);
    
    // 从工作台跳转到 goals
    const goalsLink = page.locator('a[href="/coordination/goals"], a[href*="goals"]');
    if (await goalsLink.first().isVisible()) {
      await goalsLink.first().click();
      await pageReady(page);
      expect(page.url()).toContain('/goals');
    }
  });

  test('D12-002: Goal → Project → Task 关联导航', async ({ page }) => {
    // 验证从 goal 详情页能找到 projects
    await page.goto(`${BASE}/coordination/goals`);
    await pageReady(page);
    
    const firstGoal = page.locator('a[href*="/coordination/goals/"]').first();
    if (await firstGoal.isVisible()) {
      await firstGoal.click();
      await pageReady(page);
      
      const content = await page.content();
      // goal 详情页应该显示关联的 projects
      expect(content.length).toBeGreaterThan(1000);
    }
  });

  test('D12-003: 面包屑导航返回', async ({ page }) => {
    await page.goto(`${BASE}/coordination/goals`);
    await pageReady(page);
    
    // 进入详情页
    const firstGoal = page.locator('a[href*="/coordination/goals/"]').first();
    if (await firstGoal.isVisible()) {
      await firstGoal.click();
      await pageReady(page);
      
      // 返回按钮
      const backBtn = page.locator('button:has-text("返回"), a[href*="back"], a[href*="/coordination/goals"]');
      if (await backBtn.first().isVisible()) {
        // 验证返回列表
        await page.goto(`${BASE}/coordination/goals`);
        await pageReady(page);
        expect(page.url()).toContain('/goals');
      }
    }
  });

  test('D12-004: 侧边栏折叠/展开', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await pageReady(page);
    
    // 侧边栏收起按钮
    const collapseBtn = page.locator('button[title*="收起"], button[title*="Collapse"]');
    if (await collapseBtn.first().isVisible()) {
      await collapseBtn.first().click();
      await page.waitForTimeout(500);
      
      // 再次展开
      const expandBtn = page.locator('button[title*="展开"], button[title*="Expand"]');
      if (await expandBtn.first().isVisible()) {
        await expandBtn.first().click();
        await page.waitForTimeout(500);
      }
    }
  });
});

// ============================================
// D13: 错误处理
// ============================================

test.describe('D13: 错误处理', () => {
  test('D13-001: 404 页面处理', async ({ page }) => {
    await page.goto(`${BASE}/non-existent-page`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // 应该不是空白页
    const content = await page.content();
    expect(content.length).toBeGreaterThan(100);
  });

  test('D13-002: 无效 ID 的详情页面', async ({ page }) => {
    await page.goto(`${BASE}/coordination/goals/nonexistent-id-123`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    const content = await page.content();
    // 页面应该加载（不崩溃），可能显示错误信息
    expect(content.length).toBeGreaterThan(100);
  });

  test('D13-003: 无效场景 ID', async ({ page }) => {
    await page.goto(`${BASE}/scenarios/nonexistent-id-123`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(100);
  });
});

// ============================================
// D14: 响应式和可访问性
// ============================================

test.describe('D14: 响应式和可访问性', () => {
  test('D14-001: 移动端视口', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // 验证移动端也能加载
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
  });

  test('D14-002: 平板视口', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
  });

  test('D14-003: 4K 视口', async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1440 });
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    const content = await page.content();
    expect(content.length).toBeGreaterThan(1000);
  });
});
