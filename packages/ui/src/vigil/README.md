# Vigil 域（安全域）

安全相关业务组件、hooks 和服务。

## 范围

- 安全中心（SecurityCenter）
- 裁决页面（RulingsPage）
- 争议处理（Disputes）
- 信任评分
- 告警通知

## 目录结构

```
vigil/
├── components/     域专用业务组件
├── hooks/          域专用 hooks
└── services/       域专用 API 服务
```

## 当前状态

域目录已创建，等待对应业务组件迁入。

相关页面位于 `pages/`:
- `RulingsPage.tsx`
- `SecurityCenter.tsx`
- `disputes/`
