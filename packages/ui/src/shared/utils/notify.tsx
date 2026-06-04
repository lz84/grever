// notify.tsx - Sonner toast + shadcn AlertDialog confirm
// 用法：
//   import { toast, ConfirmDialog, confirmAction } from "@/shared/utils/notify"
//   在根组件：<ConfirmDialog />
//   确认删除：if (!(await confirmAction({ title: '确认删除', description: '...', variant: 'destructive' }))) return
import { toast } from "sonner"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/shared/components/ui/alert-dialog"
import { useState, useEffect } from "react"

export { toast }

export interface ConfirmOptions {
  title?: string
  description?: string
  confirmText?: string
  cancelText?: string
  variant?: "default" | "destructive"
}

// ==================== 模块级单例 ====================
let _resolve: ((v: boolean) => void) | null = null
let _cfg: ConfirmOptions = {}
let _setOpenFn: ((v: boolean) => void) | null = null

function _confirmAction(opts: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    _cfg = opts
    _resolve = resolve
    _setOpenFn?.(true)
  })
}

export const confirmAction = _confirmAction

// ==================== Dialog 组件 ====================
export function ConfirmDialog() {
  const [open, setOpen] = useState(false)
  const [cfg, setCfg] = useState<ConfirmOptions>({})

  useEffect(() => {
    _setOpenFn = setOpen
  }, [setOpen])

  // 轮询同步外部 cfg
  useEffect(() => {
    const interval = setInterval(() => {
      setCfg((prev) => {
        if (prev.title !== _cfg.title || prev.description !== _cfg.description) {
          return { ..._cfg }
        }
        return prev
      })
    }, 50)
    return () => clearInterval(interval)
  }, [])

  const handleConfirm = () => {
    _resolve?.(true)
    _resolve = null
    setOpen(false)
  }

  const handleCancel = () => {
    _resolve?.(false)
    _resolve = null
    setOpen(false)
  }

  return (
    <AlertDialog open={open} onOpenChange={(v) => { if (!v) handleCancel() }}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{cfg.title || "确认操作"}</AlertDialogTitle>
          {cfg.description && <AlertDialogDescription>{cfg.description}</AlertDialogDescription>}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel}>{cfg.cancelText || "取消"}</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            className={cfg.variant === "destructive" ? "bg-destructive text-destructive-foreground hover:bg-destructive/90" : ""}
          >
            {cfg.confirmText || "确定"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

// 兼容旧 hook API（保留但改名）
export function useConfirmDialog() {
  return { confirm: confirmAction, ConfirmDialog }
}
