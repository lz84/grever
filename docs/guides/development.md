# 开发指南

## 开发环境

```bash
git clone https://github.com/lz84/agents_nexus.git
cd agents_nexus

# 后端
cd packages/server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 前端
cd ../ui
npm install
```

## 代码规范

### Python

- 遵循 PEP 8
- 类型注解必须
- 测试覆盖率 ≥ 80%
- 使用 `pytest` 运行测试

```bash
# 运行测试
cd packages/server
pytest tests/ -v

# 运行特定测试
pytest tests/e2e/ -v -k "agent"

# 检查覆盖率
pytest tests/ --cov=src --cov-report=html
```

### TypeScript/React

- ESLint + Prettier
- 组件使用函数式写法
- Props 必须定义类型
- 使用 shadcn/ui 组件库

```bash
# 类型检查
cd packages/ui
npx tsc --noEmit

# 运行测试
npm test
```

## 项目结构

### 后端五域目录

```
packages/server/src/
├── cognitive/     # GrASP 认知域
│   ├── adapters/  # GraphRAG 后端适配器
│   ├── analysis/  # 认知提取与评估
│   ├── parser/    # 文档解析器
│   ├── registry/  # 后端注册表
│   └── injection/ # 知识注入
├── steering/      # Reins 驾驭域
│   ├── core/      # 状态机
│   ├── scheduler/ # 调度器
│   ├── tracking/  # 执行追踪
│   └── messaging/ # 消息系统
├── evolution/     # Evo 进化域
│   ├── distillation/ # 蒸馏引擎
│   ├── mutation/     # 突变引擎
│   └── weight/       # 权重管理
├── extension/     # Reach 拓展域
│   ├── scenarios/ # 场景库
│   ├── industry/  # 行业包
│   └── mcp/       # MCP 集成
├── security/      # Vigil 安全域
│   ├── trust/     # 信任管理
│   └── access/    # 访问控制
└── shared/        # 公共服务
    ├── database/  # DB 连接池
    ├── eventbus/  # 事件总线
    └── auth/      # 认证授权
```

### 前端目录

```
packages/ui/src/
├── pages/           # 功能页面
│   ├── reins/       # 驾驭域页面
│   ├── grasp/       # 认知域页面
│   ├── evo/         # 进化域页面
│   ├── reach/       # 拓展域页面
│   └── vigil/       # 安全域页面
├── shared/          # 共享组件
│   ├── components/  # UI 组件
│   │   └── ui/      # shadcn/ui 组件
│   ├── api/         # API 路径定义
│   ├── services/    # 服务层
│   └── utils/       # 工具函数
└── layout/          # 布局组件
```

## 提交规范

提交信息格式：

```
<type>(<scope>): <description>

[optional body]
```

**Type**:
- `feat` — 新功能
- `fix` — Bug 修复
- `docs` — 文档
- `style` — 代码格式
- `refactor` — 重构
- `test` — 测试
- `chore` — 构建/工具

**示例**:
```
feat(reins): 添加任务自动分配逻辑
fix(grasp): 修复认知注入空指针
docs(architecture): 更新架构图
```

## Pull Request 流程

1. Fork 仓库
2. 创建特性分支 (`git checkout -b feat/xxx`)
3. 提交变更
4. 创建 PR，描述变更内容和动机

**PR 要求**：
- 描述变更内容
- 包含测试用例
- 更新相关文档
- 通过 CI 检查

## 数据库迁移

```bash
# 创建新迁移
alembic revision -m "add_field_to_tasks"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## 许可证

贡献即表示你同意将代码以 AGPL-3.0 许可证分发。
