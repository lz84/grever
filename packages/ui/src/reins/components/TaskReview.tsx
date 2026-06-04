import { useState } from 'react'
import { toast } from "sonner"
import { Eye, Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Textarea } from '@/shared/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/shared/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/components/ui/select'
import { tasksApi } from '@/shared/utils/api'

interface TaskReviewProps {
  taskId: string
  onRefresh: () => void
}

export function TaskReview({ taskId, onRefresh }: TaskReviewProps) {
  const [open, setOpen] = useState(false)
  const [review, setReview] = useState('')
  const [decision, setDecision] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit() {
    if (!review.trim()) return
    setSubmitting(true)
    try {
      await tasksApi.reviewTask(taskId, { review: review.trim(), decision: decision || undefined })
      setReview('')
      setDecision('')
      setOpen(false)
      onRefresh?.()
      toast.success('审查已提交')
    } catch (e: any) {
      toast.error('审查提交失败: ' + e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <Button variant="outline" size="sm" className="w-full justify-start" onClick={() => setOpen(true)}>
        <Eye className="w-3 h-3 mr-2" />任务审查
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>任务审查</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">审查意见</label>
              <Textarea
                value={review}
                onChange={e => setReview(e.target.value)}
                placeholder="输入审查意见..."
                rows={4}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">决定</label>
              <Select value={decision} onValueChange={setDecision}>
                <SelectTrigger>
                  <SelectValue placeholder="选择决定" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="approve">通过</SelectItem>
                  <SelectItem value="reject">驳回</SelectItem>
                  <SelectItem value="revise">修改后通过</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={submitting}>取消</Button>
            <Button onClick={handleSubmit} disabled={submitting || !review.trim()}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : '提交审查'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
