/**
 * 验证器设置组件
 * 调用 goalsApi.setVerifier
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { CheckCircle, Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { goalsApi } from '@/shared/utils/api'
import { getAgentName } from '@/shared/utils/agentMap'

interface GoalVerifierProps {
  goalId: string
  currentVerifierId?: string | null
  onVerifierChanged?: () => void
}

export default function GoalVerifier({ goalId, currentVerifierId, onVerifierChanged }: GoalVerifierProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<string>('none')
  const [saving, setSaving] = useState(false)

  const handleStartEdit = () => {
    setDraft(currentVerifierId || 'none')
    setEditing(true)
  }

  const handleCancel = () => {
    setEditing(false)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await goalsApi.setVerifier(goalId, draft === 'none' ? '' : draft)
      toast.success('验证器已更新')
      setEditing(false)
      onVerifierChanged?.()
    } catch (e: any) {
      toast.error('保存失败: ' + (e.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  const agents = [
    { value: 'none', label: '不设置' },
    { value: '3745f1f0-b67d-4287-a10b-e71b3ff17e97', label: '扣子（开发专员）' },
    { value: '9d899c03-4ada-45a7-805a-b2f0fb4ebb24', label: '麻子（技术专家）' },
    { value: '876b9322-0fbe-4cd0-97c2-9244a4e3b905', label: '谷子（业务专家）' },
    { value: '8817e140-2c46-40d8-9444-a6bca8a8e8fb', label: '蚊子（内容专员）' },
    { value: 'fefd19b0-7c1a-4927-b294-c795c76afb9f', label: '刚子（指挥调度）' },
  ]

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-slate-500" />
            <CardTitle className="text-sm">验证智能体</CardTitle>
          </div>
          {!editing && (
            <Button variant="ghost" size="sm" onClick={handleStartEdit}>
              {currentVerifierId ? '修改' : '设置'}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {editing ? (
          <div className="flex gap-2">
            <Select value={draft} onValueChange={setDraft}>
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="选择验证智能体" />
              </SelectTrigger>
              <SelectContent>
                {agents.map(a => (
                  <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button size="sm" onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : '保存'}
            </Button>
            <Button variant="outline" size="sm" onClick={handleCancel} disabled={saving}>取消</Button>
          </div>
        ) : (
          <span className="text-sm text-slate-800">
            {currentVerifierId ? getAgentName(currentVerifierId) : '未设置'}
          </span>
        )}
      </CardContent>
    </Card>
  )
}
