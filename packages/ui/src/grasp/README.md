# Grasp 域（认知域）

认知相关业务组件、hooks 和服务。

## 范围

- 认知评估（CognitiveAssessment）
- 认知中心（CognitiveCenter）
- 知识注入（CognitiveInject）
- 知识管理（CognitiveKnowledge）

## 目录结构

```
grasp/
├── components/     域专用业务组件
├── hooks/          域专用 hooks
└── services/       域专用 API 服务
```

## 当前状态

认知域页面已就位：
- `pages/CognitiveAssessment.tsx`（15KB）
- `pages/CognitiveCenter.tsx`（9KB）
- `pages/CognitiveInject.tsx`（8KB）
- `pages/CognitiveKnowledge.tsx`（13KB）

这些页面目前自包含业务逻辑，直接引用 `shared/api/paths` 和 `shared/components/`。
后续如需抽取域专用组件/hooks，请归位到本目录。
