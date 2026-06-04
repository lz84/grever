import { useState } from 'react'
import { toast } from "sonner"
import { BarChart3, Loader2 } from 'lucide-react'
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

interface TaskProgressProps {
  taskId: string
  onRefresh: () => void
}

export function TaskProgress({ taskId, onRefresh }: TaskProgressProps) {
  const [open, setOpen] = useState(false)
  const [progress, setProgress] = useState('')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit() {
    if (!progress) return
    setSubmitting(true)
    try {
      await tasksApi.updateProgress(taskId, {
        progress: parseInt(progress),
        notes: notes.trim() || undefined,
      })
      setProgress('')
      setNotes('')
      setOpen(false)
      onRefresh?.()
      toast.success('进度已更新')
    } catch (e: any) {
      toast.error('进度更新失败: ' + e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <Button variant="outline" size="sm" className="w-full justify-start" onClick={() => setOpen(true)}>
        <BarChart3 className="w-3 h-3 mr-2" />更新进度
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>更新任务进度</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">进度百分比</label>
              <Select value={progress} onValueChange={setProgress}>
                <SelectTrigger>
                  <SelectValue placeholder="选择进度" />
                </SelectTrigger>
                <SelectContent>
                  {['0', '10', '20', '30', '40', '50', '60', '70', '80', '90', '100'].map(v => (
                    <SelectItem key={v} value={v}>{v}%</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">备注</label>
              <Textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="进度说明（可选）..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={submitting}>取消</Button>
            <Button onClick={handleSubmit} disabled={submitting || !progress}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : '更新'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
