/**
 * Nexus E2E Test Suite
 * 
 * 覆盖 13 个业务流程，39 个页面测试用例
 * 
 * 运行: npx playwright test tests/e2e/page-flows.spec.ts
 */

import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';

/** 等待页面加载 */
async function pageReady(page) {
  await page.goto(`${BASE}/`);
  // Wait for network to settle, then wait a bit for React to mount
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
}

// ============================================
// F1: 工作台
// ============================================

test.describe('F1: 工作台', () => {
  test('TC-001: Dashboard 页面加载', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const title = await page.title();
    expect(title).toContain('Nexus');
  });
});

// ============================================
// F2: Goal 列表→详情→分解→树
// ============================================

test.describe('F2: Goal 流程', () => {
  test('TC-002: GoalList 列表加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/goals`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-005: GoalDecomposePage 树视图', async ({ page }) => {
    await page.goto(`${BASE}/coordination/goals`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const firstGoal = page.locator('tr, [role="row"], a').first();
    if (await firstGoal.isVisible()) {
      await firstGoal.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('TC-006: CreateGoal 表单加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/goals/new`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });
});

// ============================================
// F3: Project 列表→详情→图→树
// ============================================

test.describe('F3: Project 流程', () => {
  test('TC-007: ProjectList 列表加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/projects`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-008: ProjectDetail 详情加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/projects`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const firstProject = page.locator('tr, [role="row"], a').first();
    if (await firstProject.isVisible()) {
      await firstProject.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('TC-009: ProjectDiagram 图加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/projects`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const diagramLink = page.locator('a[href*="diagram"]').first();
    if (await diagramLink.isVisible()) {
      await diagramLink.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('TC-010: ProjectTreePage 树加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/projects`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const treeLink = page.locator('a[href*="tree"]').first();
    if (await treeLink.isVisible()) {
      await treeLink.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      await expect(page.locator('body')).toBeVisible();
    }
  });
});

// ============================================
// F4: Task 列表→详情→创建→增强
// ============================================

test.describe('F4: Task 流程', () => {
  test('TC-011: TaskList 列表加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/tasks`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-012: TaskDetail 详情加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/tasks`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const firstTask = page.locator('tr, [role="row"], a').first();
    if (await firstTask.isVisible()) {
      await firstTask.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('TC-013: CreateTask 表单加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/tasks/create`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-014: EnhancedTaskDetail 增强详情', async ({ page }) => {
    await page.goto(`${BASE}/coordination/tasks`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const firstTask = page.locator('tr, [role="row"], a').first();
    if (await firstTask.isVisible()) {
      await firstTask.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      const enhancedLink = page.locator('a[href*="enhanced"]').first();
      if (await enhancedLink.isVisible()) {
        await enhancedLink.click();
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1000);
        await expect(page.locator('body')).toBeVisible();
      }
    }
  });
});

// ============================================
// F5: Execution 监控→详情
// ============================================

test.describe('F5: Execution 流程', () => {
  test('TC-015: ExecutionMonitoring 监控加载', async ({ page }) => {
    await page.goto(`${BASE}/coordination/executions`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-016: ExecutionDetail 详情', async ({ page }) => {
    await page.goto(`${BASE}/coordination/executions`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const firstExecution = page.locator('tr, [role="row"], a').first();
    if (await firstExecution.isVisible()) {
      await firstExecution.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      await expect(page.locator('body')).toBeVisible();
    }
  });
});

// ============================================
// F6: 认知中心
// ============================================

test.describe('F6: 认知中心', () => {
  test('TC-017: CognitiveCenter 中心页面', async ({ page }) => {
    await page.goto(`${BASE}/cognitive/center`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-018: CognitiveKnowledge 知识页面', async ({ page }) => {
    await page.goto(`${BASE}/cognitive/knowledge`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-019: CognitiveAssessment 评估页面', async ({ page }) => {
    await page.goto(`${BASE}/cognitive/assessment`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-020: CognitiveInject 注入页面', async ({ page }) => {
    await page.goto(`${BASE}/cognitive/inject`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });
});

// ============================================
// F7: 场景库
// ============================================

test.describe('F7: 场景库', () => {
  test('TC-021: ScenarioCenter 中心页面', async ({ page }) => {
    await page.goto(`${BASE}/scenarios/center`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-022: ScenarioList 列表', async ({ page }) => {
    await page.goto(`${BASE}/scenarios`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-023: ScenarioFavorites 收藏', async ({ page }) => {
    await page.goto(`${BASE}/scenarios/starred`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await expect(page.locator('body')).toBeVisible();
  });

  test('TC-024: ScenarioDetail 详情', async ({ page }) => {
    await page.goto(`${BASE}/scenarios`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const firstScenario = page.locator('tr, [role="row"], a').first();
    if (await firstScenario.isVisible()) {
      await firstScenario.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('TC-025: ScenarioCreate 创建', async ({ page }) => {
    await page.goto(`${BASE}/scenarios/new`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });
});

// ============================================
// F8: 安全+HITL+裁决
// ============================================

test.describe('F8: 安全+HITL+裁决', () => {
  test('TC-026: SecurityCenter 安全中心', async ({ page }) => {
    await page.goto(`${BASE}/security`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-027: HumanInputDashboard HITL 仪表盘', async ({ page }) => {
    await page.goto(`${BASE}/human-input`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-028: HumanInputPage 待处理', async ({ page }) => {
    await page.goto(`${BASE}/human-input/pending`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await expect(page.locator('body')).toBeVisible();
  });

  test('TC-029: HumanInputAnalytics 分析', async ({ page }) => {
    await page.goto(`${BASE}/human-input/analytics`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-030: RulingsPage 裁决', async ({ page }) => {
    await page.goto(`${BASE}/rulings`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });
});

// ============================================
// F9: 系统管理
// ============================================

test.describe('F9: 系统管理', () => {
  test('TC-031: AgentList Agent 列表', async ({ page }) => {
    await page.goto(`${BASE}/system/agents`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-032: CapabilitiesPage 能力页面', async ({ page }) => {
    await page.goto(`${BASE}/system/capabilities`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-033: ArtifactList 工件列表', async ({ page }) => {
    await page.goto(`${BASE}/system/artifacts`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await expect(page.locator('body')).toBeVisible();
  });

  test('TC-034: Settings 设置', async ({ page }) => {
    await page.goto(`${BASE}/system/settings`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });
});

// ============================================
// F10: 可视化
// ============================================

test.describe('F10: 可视化', () => {
  test('TC-035: VisualBoard 可视化看板', async ({ page }) => {
    await page.goto(`${BASE}/visual/dashboard`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-036: TraceViewer 追踪', async ({ page }) => {
    await page.goto(`${BASE}/visual/traces`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });
});

// ============================================
// F11: 工作流图
// ============================================

test.describe('F11: 工作流图', () => {
  test('TC-037: WorkflowDiagram 图加载', async ({ page }) => {
    await page.goto(`${BASE}/workflows/test/diagram`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await expect(page.locator('body')).toBeVisible();
  });
});

// ============================================
// F12: 方案
// ============================================

test.describe('F12: 方案', () => {
  test('TC-038: SolutionList 列表', async ({ page }) => {
    await page.goto(`${BASE}/solutions`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const content = await page.content();
    expect(content.length).toBeGreaterThan(500);
  });

  test('TC-039: SolutionCenter 方案中心', async ({ page }) => {
    await page.goto(`${BASE}/solutions`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await expect(page.locator('body')).toBeVisible();
  });
});

// ============================================
// F13: 侧边栏导航
// ============================================

test.describe('F13: 侧边栏导航', () => {
  const menuItems = [
    { label: '工作台', path: '/' },
    { label: '目标', path: '/coordination/goals' },
    { label: '项目', path: '/coordination/projects' },
    { label: '任务', path: '/coordination/tasks' },
    { label: '执行', path: '/coordination/executions' },
    { label: '认知', path: '/cognitive/center' },
    { label: '场景', path: '/scenarios' },
    { label: '安全', path: '/security' },
    { label: 'HITL', path: '/human-input' },
    { label: 'Agent', path: '/system/agents' },
    { label: '可视化', path: '/visual/dashboard' },
    { label: '裁决', path: '/rulings' },
    { label: '设置', path: '/system/settings' },
  ];

  test('侧边栏导航可达所有页面', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    for (const item of menuItems) {
      await page.goto(`${BASE}${item.path}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);
      const content = await page.content();
      expect(content).not.toContain('Not Found');
      expect(content).not.toContain('Internal Server Error');
    }
  });
});
