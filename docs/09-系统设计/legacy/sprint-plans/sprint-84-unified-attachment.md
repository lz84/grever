# Sprint 84: 统一附件体系

**目标**：将 task_attachments 统一为 attachments + attachment_links，服务所有实体
**设计文档**：`docs/02-架构设计/21-unified-attachment-system.md`
**分支**：feat/sprint68（沿用当前分支）

## 任务拆分

| 任务 | 依赖 | 负责人 | 说明 |
|------|------|--------|------|
| 84-1 后端：DB迁移 | [] | 麻子 | 创建 attachments + attachment_links 表 |
| 84-2 后端：上传+下载API | [84-1] | 麻子 | upload/download/delete + link管理 |
| 84-3 后端：迁移脚本 | [84-1] | 麻子 | 迁移旧 task_attachments 数据 |
| 84-4 前端：通用组件 | [84-2] | 扣子 | AttachmentUploader 组件 |
| 84-5 前端：页面集成 | [84-4] | 扣子 | CreateGoal/GoalDetail/TaskDetail 集成 |

## 验证
- E2E：上传 → 关联 → 下载 → 删除 → 取消关联
- DB：关键字段非 null，关联正确
- 页面：上传组件正常渲染，附件列表正确显示
