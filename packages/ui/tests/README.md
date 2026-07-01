# Grever UI 测试指南

## 测试结构

```
tests/
├── setup.ts              # 测试全局配置
├── mocks/
│   ├── index.ts          # Mock 导出
│   ├── server.ts         # MSW 服务端
│   └── handlers.ts       # API Mock 处理函数
├── pages/                # 单元测试
│   ├── Dashboard.test.tsx
│   ├── Coordination.test.tsx
│   ├── SystemManagement.test.tsx
│   ├── Visualization.test.tsx
│   ├── CognitiveCenter.test.tsx
│   └── ScenarioLibrary.test.tsx
└── e2e/                  # E2E 测试
    ├── MAK-204-dashboard.spec.ts
    ├── MAK-205-coordination.spec.ts
    ├── MAK-206-system.spec.ts
    ├── MAK-207-visualization.spec.ts
    ├── MAK-208-cognitive.spec.ts
    └── MAK-209-scenarios.spec.ts
```

## 运行测试

### 安装依赖
```bash
cd packages/ui
npm install
```

### 运行单元测试
```bash
npm run test
```

### 运行单元测试（监听模式）
```bash
npm run test:watch
```

### 运行单元测试（带覆盖率）
```bash
npm run test:coverage
```

### 运行 E2E 测试
```bash
npm run test:e2e
```

## 测试 Issue 对应

### 单元测试
| Issue | 模块 | 测试文件 |
|-------|------|----------|
| MAK-194 | 工作台 | `Dashboard.test.tsx` |
| MAK-195 | 协同中心 | `Coordination.test.tsx` |
| MAK-196 | 系统管理 | `SystemManagement.test.tsx` |
| MAK-197 | 可视化 | `Visualization.test.tsx` |
| MAK-198 | 认知中心 | `CognitiveCenter.test.tsx` |
| MAK-199 | 场景库 | `ScenarioLibrary.test.tsx` |

### E2E 业务测试
| Issue | 模块 | 测试文件 |
|-------|------|----------|
| MAK-204 | 工作台 | `MAK-204-dashboard.spec.ts` |
| MAK-205 | 协同中心 | `MAK-205-coordination.spec.ts` |
| MAK-206 | 系统管理 | `MAK-206-system.spec.ts` |
| MAK-207 | 可视化 | `MAK-207-visualization.spec.ts` |
| MAK-208 | 认知中心 | `MAK-208-cognitive.spec.ts` |
| MAK-209 | 场景库 | `MAK-209-scenarios.spec.ts` |

## Mock 数据

所有 API 调用通过 MSW (Mock Service Worker) 进行模拟，详见 `tests/mocks/handlers.ts`。

### Mock 数据说明

- **Agents**: 刚子(gangzi)、谷子(guzi)、麻子(mazi)
- **Goals**: 城市应急管理、智能投资研究、抢险救灾
- **Projects**: 预案模块开发、指挥调度模块
- **Tasks**: 设计数据库结构、开发 API 接口
- **Scenarios**: 危化品泄漏处置、地震救援

## 注意事项

1. 场景库和注入管理模块的 API 未就绪，测试使用 mock 数据
2. E2E 测试需要开发服务器运行，配置在 `playwright.config.ts`
3. 部分组件依赖 React Router，请使用 `MemoryRouter` 包装
