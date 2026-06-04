import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/shared/components/ui/dialog'
import { Button } from '@/shared/components/ui/button'
import { Card, CardContent } from '@/shared/components/ui/card'
import { Loader2 } from 'lucide-react'

interface SaveScenarioDialogProps {
  preview: any
  onClose: () => void
  onConfirm: () => void
  loading: boolean
  /** 'goal' shows "目标" text, 'project' shows "工程" text. Default: 'goal' */
  variant?: 'goal' | 'project'
}

export function SaveScenarioDialog({ preview, onClose, onConfirm, loading, variant = 'goal' }: SaveScenarioDialogProps) {
  if (!preview) return null
  const entityName = variant === 'project' ? '工程' : '目标'
  return (
    <Dialog open={!!preview} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>保存为场景</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <Card>
            <CardContent className="pt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">场景名称:</span>
                <span className="font-medium">{preview.basic?.name || '未命名场景'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">阶段数量:</span>
                <span className="font-medium">{preview.project_workflow?.phases?.length || 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">任务模板数量:</span>
                <span className="font-medium">{preview.task_templates?.length || 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">分类:</span>
                <span className="font-medium">{preview.basic?.category || '未分类'}</span>
              </div>
            </CardContent>
          </Card>
          <p className="text-sm text-muted-foreground">确定要将此{entityName}保存为场景吗？</p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>取消</Button>
          <Button onClick={onConfirm} disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            确认保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
