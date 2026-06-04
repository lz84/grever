/**
 * 约束设置组件
 * 调用 goalsApi.setConstraints
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { Loader2, Save, X, Plus } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { goalsApi } from '@/shared/utils/api'

interface GoalConstraintsProps {
  goalId: string
  currentConstraints?: Record<string, any>
  onConstraintsChanged?: () => void
}

export default function GoalConstraints({ goalId, currentConstraints, onConstraintsChanged }: GoalConstraintsProps) {
  const [editing, setEditing] = useState(false)
  const [constraints, setConstraints] = useState<Array<{ key: string; value: string }>>([])
  const [saving, setSaving] = useState(false)

  const handleStartEdit = () => {
    if (currentConstraints) {
      const entries = Object.entries(currentConstraints).map(([key, value]) => ({
        key,
        value: typeof value === 'string' ? value : JSON.stringify(value),
      }))
      setConstraints(entries.length > 0 ? entries : [{ key: '', value: '' }])
    } else {
      setConstraints([{ key: '', value: '' }])
    }
    setEditing(true)
  }

  const handleCancel = () => {
    setEditing(false)
  }

  const addRow = () => {
    setConstraints([...constraints, { key: '', value: '' }])
  }

  const removeRow = (index: number) => {
    setConstraints(constraints.filter((_, i) => i !== index))
  }

  const updateRow = (index: number, field: 'key' | 'value', val: string) => {
    const updated = [...constraints]
    updated[index][field] = val
    setConstraints(updated)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const obj: Record<string, any> = {}
      for (const c of constraints) {
        if (c.key.trim()) {
          try {
            obj[c.key.trim()] = JSON.parse(c.value)
          } catch {
            obj[c.key.trim()] = c.value
          }
        }
      }
      await goalsApi.setConstraints(goalId, obj)
      toast.success('约束已更新')
      setEditing(false)
      onConstraintsChanged?.()
    } catch (e: any) {
      toast.error('保存失败: ' + (e.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-sm">约束条件</CardTitle>
          </div>
          {!editing && (
            <Button variant="ghost" size="sm" onClick={handleStartEdit}>
              修改
            </Button>
          )}
        </div>
        <CardDescription>设置目标迭代时 AI 需要遵守的约束，会被注入到提示词中</CardDescription>
      </CardHeader>
      <CardContent>
        {editing ? (
          <div className="space-y-3">
            <div className="bg-blue-50 border border-blue-200 rounded-md p-3 text-xs text-blue-800 space-y-1">
              <p className="font-medium">约束条件说明：</p>
              <p>每轮迭代时，这些约束会被注入到 AI 提示词中，限制 AI 的生成范围。</p>
              <p className="mt-1 font-medium">示例：</p>
              <p>• <code className="bg-blue-100 px-1 rounded">budget</code> → <code className="bg-blue-100 px-1 rounded">预算不超过 5000 元</code></p>
              <p>• <code className="bg-blue-100 px-1 rounded">time_limit</code> → <code className="bg-blue-100 px-1 rounded">一周内完成</code></p>
              <p>• <code className="bg-blue-100 px-1 rounded">tech_stack</code> → <code className="bg-blue-100 px-1 rounded">只能使用 Python + FastAPI</code></p>
              <p>• <code className="bg-blue-100 px-1 rounded">compliance</code> → <code className="bg-blue-100 px-1 rounded">必须通过等保三级认证</code></p>
            </div>
            {constraints.map((c, i) => (
              <div key={i} className="flex gap-2 items-center">
                <Input
                  placeholder="约束名称，如 budget"
                  value={c.key}
                  onChange={(e) => updateRow(i, 'key', e.target.value)}
                  className="flex-1 text-sm"
                />
                <Input
                  placeholder="约束内容，如 预算不超过5000元"
                  value={c.value}
                  onChange={(e) => updateRow(i, 'value', e.target.value)}
                  className="flex-1 text-sm"
                />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeRow(i)}
                  className="h-8 w-8 shrink-0"
                >
                  <X className="w-3.5 h-3.5" />
                </Button>
              </div>
            ))}
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={addRow}>
                <Plus className="w-3 h-3 mr-1" /> 添加约束
              </Button>
              <div className="flex-1" />
              <Button variant="outline" size="sm" onClick={handleCancel} disabled={saving}>取消</Button>
              <Button size="sm" onClick={handleSave} disabled={saving}>
                {saving ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Save className="w-3 h-3 mr-1" />}
                保存
              </Button>
            </div>
          </div>
        ) : currentConstraints && Object.keys(currentConstraints).length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {Object.entries(currentConstraints).map(([key, value]) => (
              <Badge key={key} variant="secondary" className="text-xs">
                {key}: {typeof value === 'string' ? value : JSON.stringify(value)}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">暂无约束条件</p>
        )}
      </CardContent>
    </Card>
  )
}
