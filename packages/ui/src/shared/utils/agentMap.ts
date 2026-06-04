// Agent UUID → 代号 映射
// 用于所有 UI 显示，禁止显示原始 UUID

export const AGENT_ID_MAP: Record<string, string> = {
  'fefd19b0-7c1a-4927-b294-c795c76afb9f': '刚子',
  '876b9322-0fbe-4cd0-97c2-9244a4e3b905': '谷子',
  '9d899c03-4ada-45a7-805a-b2f0fb4ebb24': '麻子',
  '8817e140-2c46-40d8-9444-a6bca8a8e8fb': '蚊子',
  '3745f1f0-b67d-4287-a10b-e71b3ff17e97': '扣子',
}

export function getAgentName(agentId: string | null | undefined): string {
  if (!agentId) return '未分配'
  return AGENT_ID_MAP[agentId] || agentId
}
