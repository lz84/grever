# 贡献指南

欢迎为 Nexus 贡献代码！

## 开发环境

```bash
git clone <repo-url>
cd nexus
# 后端：cd packages/server && pip install -r requirements.txt
# 前端：cd packages/ui && npm install
```

## 代码规范

### Python
- 遵循 PEP 8
- 类型注解必须
- 测试覆盖率 ≥ 80%

### TypeScript
- ESLint + Prettier
- Props 必须定义类型
- 使用 shadcn/ui 组件库

## 提交规范

```
<type>(<scope>): <description>

feat(reins): 添加任务自动分配
fix(grasp): 修复认知注入空指针
docs(architecture): 更新架构图
```

## Pull Request

1. Fork 仓库
2. 创建特性分支 (`git checkout -b feat/xxx`)
3. 提交变更
4. 创建 PR，描述变更内容和动机

## 许可证

贡献即表示你同意将代码以 AGPL-3.0 许可证分发。
