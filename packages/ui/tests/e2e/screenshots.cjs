/**
 * Nexus 页面截图工具
 * 使用 Playwright 直接截图，不需要 browser tool profile
 * 
 * 运行: node tests/e2e/screenshots.js
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE = 'http://localhost:5173';
const OUT_DIR = path.join(__dirname, 'screenshots');

if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

const pages = [
  { name: '00-Dashboard', path: '/' },
  { name: '01-GoalList', path: '/coordination/goals' },
  { name: '02-GoalDetail', path: '/coordination/goals' },
  { name: '03-CreateGoal', path: '/coordination/goals/new' },
  { name: '04-ProjectList', path: '/coordination/projects' },
  { name: '05-TaskList', path: '/coordination/tasks' },
  { name: '06-CreateTask', path: '/coordination/tasks/create' },
  { name: '07-Execution', path: '/coordination/executions' },
  { name: '08-CognitiveCenter', path: '/cognitive/center' },
  { name: '09-CognitiveKnowledge', path: '/cognitive/knowledge' },
  { name: '10-ScenarioCenter', path: '/scenarios/center' },
  { name: '11-ScenarioList', path: '/scenarios' },
  { name: '12-ScenarioCreate', path: '/scenarios/new' },
  { name: '13-SecurityCenter', path: '/security' },
  { name: '14-HumanInput', path: '/human-input' },
  { name: '15-AgentList', path: '/system/agents' },
  { name: '16-Capabilities', path: '/system/capabilities' },
  { name: '17-IndustryTags', path: '/industry/tags' },
  { name: '18-VisualBoard', path: '/visual/dashboard' },
  { name: '19-Settings', path: '/system/settings' },
  { name: '20-Rulings', path: '/rulings' },
  { name: '21-Solutions', path: '/solutions' },
];

async function screenshotPage(browser, pageInfo) {
  const { name, path: urlPath } = pageInfo;
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  try {
    await page.goto(`${BASE}${urlPath}`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(1500); // Wait for React to render
    
    const outPath = path.join(OUT_DIR, `${name}.png`);
    await page.screenshot({ path: outPath, fullPage: false });
    console.log(`  [OK] ${name}`);
    return true;
  } catch (err) {
    console.log(`  [FAIL] ${name}: ${err.message}`);
    return false;
  } finally {
    await page.close();
  }
}

async function main() {
  console.log('Starting Nexus screenshots...\n');
  console.log(`Output: ${OUT_DIR}\n`);
  
  const browser = await chromium.launch({ headless: true });
  
  let passed = 0;
  for (const pageInfo of pages) {
    const ok = await screenshotPage(browser, pageInfo);
    if (ok) passed++;
  }
  
  await browser.close();
  
  console.log(`\nDone: ${passed}/${pages.length} pages screenshot OK`);
  console.log(`Screenshots saved to: ${OUT_DIR}`);
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
