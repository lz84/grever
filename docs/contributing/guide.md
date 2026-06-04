# 贡献指南

欢迎为 Nexus 贡献代码！

## 开发环境

```bash
git clone https://github.com/lz84/agents_nexus.git
cd agents_nexus

# 后端
cd packages/server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 前端
cd ../ui
npm install
```

## 代码规范

### Python

- 遵循 PEP 8
- 类型注解必须
- 测试覆盖率 ≥ 80%

```bash
# 运行测试
cd packages/server
pytest tests/ -v
```

### TypeScript/React

- ESLint + Prettier
- Props 必须定义类型
- 使用 shadcn/ui 组件库

```bash
# 类型检查
cd packages/ui
npx tsc --noEmit
```

## 提交规范

提交信息格式：

```
<type>(<scope>): <description>
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
feat(reins): 添加任务自动分配
fix(grasp): 修复认知注入空指针
docs(architecture): 更新架构图
```

## Pull Request

1. Fork 仓库
2. 创建特性分支 (`git checkout -b feat/xxx`)
3. 提交变更
4. 创建 PR，描述变更内容和动机

**PR 要求**：
- 描述变更内容
- 包含测试用例
- 更新相关文档
- 通过 CI 检查

## 许可证

贡献即表示你同意将代码以 AGPL-3.0 许可证分发。
