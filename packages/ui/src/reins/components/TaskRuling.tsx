import { useState } from 'react'
import { toast } from "sonner"
import { Gavel, Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Textarea } from '@/shared/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/shared/components/ui/dialog'
import { tasksApi } from '@/shared/utils/api'

interface TaskRulingProps {
  taskId: string
  onRefresh: () => void
}

export function TaskRuling({ taskId, onRefresh }: TaskRulingProps) {
  const [open, setOpen] = useState(false)
  const [ruling, setRuling] = useState('')
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit() {
    if (!ruling.trim()) return
    setSubmitting(true)
    try {
      await tasksApi.rulingTask(taskId, { ruling: ruling.trim(), reason: reason.trim() || undefined })
      setRuling('')
      setReason('')
      setOpen(false)
      onRefresh?.()
      toast.success('裁决已提交')
    } catch (e: any) {
      toast.error('裁决提交失败: ' + e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <Button variant="outline" size="sm" className="w-full justify-start" onClick={() => setOpen(true)}>
        <Gavel className="w-3 h-3 mr-2" />任务裁决
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>任务裁决</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">裁决结果</label>
              <Textarea
                value={ruling}
                onChange={e => setRuling(e.target.value)}
                placeholder="输入裁决结果..."
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">理由</label>
              <Textarea
                value={reason}
                onChange={e => setReason(e.target.value)}
                placeholder="裁决理由（可选）..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={submitting}>取消</Button>
            <Button onClick={handleSubmit} disabled={submitting || !ruling.trim()}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : '提交裁决'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
