-- Sprint 80a: 迭代模式建议系统
-- 在 goal_iterations 表新增 3 个字段：
--   ai_suggestion          - AI 生成的结构化建议（JSON）
--   human_response         - 人的回复（同意/调整/跳过）
--   constraint_adjustments - 人调整后的约束值（JSON）

-- 使用 SQLite 的列检查确保幂等性（SQLite 不支持 ADD COLUMN IF NOT EXISTS）
-- 如果列已存在，ALTER TABLE 会失败，所以用脚本来安全添加

-- ai_suggestion: {"analysis": "本轮分析...", "comparison": {...}, "suggestion": "建议...", "action_buttons": ["同意", "调整", "跳过"]}
ALTER TABLE goal_iterations ADD COLUMN ai_suggestion TEXT;

-- human_response: 人的回复: "同意执行" / "安全系数提到40%" / "跳过本轮"
ALTER TABLE goal_iterations ADD COLUMN human_response TEXT;

-- constraint_adjustments: {"safety_weight": 0.4, "cost_weight": 0.3, ...} 人调整后的约束值
ALTER TABLE goal_iterations ADD COLUMN constraint_adjustments TEXT;
