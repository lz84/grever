import { useState, useEffect } from 'react'
import { toast } from "sonner"
import { Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Textarea } from '@/shared/components/ui/textarea'
import { tasksApi } from '@/shared/utils/api'

interface TaskCommentsProps {
  taskId: string
  onRefresh: () => void
}

interface Comment {
  id: string
  author?: string
  author_role?: string
  content: string
  type?: string
  is_agent_reply?: boolean
  metadata?: any
  created_at?: string
}

export function TaskComments({ taskId, onRefresh }: TaskCommentsProps) {
  const [comments, setComments] = useState<Comment[]>([])
  const [newComment, setNewComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => { loadComments() }, [taskId])

  async function loadComments() {
    try {
      setLoading(true)
      const data = await tasksApi.getComments(taskId)
      setComments(Array.isArray(data) ? data : [])
    } catch {
      setComments([])
    } finally {
      setLoading(false)
    }
  }

  async function handleAddComment() {
    if (!newComment.trim()) return
    setSubmitting(true)
    try {
      await tasksApi.addComment(taskId, newComment, '人类')
      setNewComment('')
      await loadComments()
      onRefresh?.()
      toast.success('评论已提交')
    } catch (e: any) {
      toast.error('评论提交失败: ' + e.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(id: string) {
    try {
      await tasksApi.deleteComment(taskId, id)
      await loadComments()
      toast.success('评论已删除')
    } catch (e: any) {
      toast.error('删除失败: ' + e.message)
    }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })
  }

  if (loading) return <div className="text-center py-8"><Loader2 className="w-6 h-6 animate-spin mx-auto text-blue-500" /></div>

  return (
    <div>
      {/* Input */}
      <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm font-medium text-blue-800 mb-2">💬 发表评论（触发执行者重新修改）</p>
        <Textarea
          value={newComment}
          onChange={e => setNewComment(e.target.value)}
          placeholder="输入修改意见，提交后将触发执行者重新派发任务..."
          className="mb-2 text-sm"
          rows={3}
        />
        <Button
          size="sm"
          onClick={handleAddComment}
          disabled={submitting || !newComment.trim()}
        >
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : '提交并触发重新派发'}
        </Button>
      </div>

      {/* List */}
      {comments.length === 0 ? (
        <div className="text-center py-8 text-slate-400">
          <p className="text-sm">暂无讨论记录</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[500px] overflow-y-auto">
          {comments.map((c) => {
            const isHuman = c.author_role === 'human' || c.author === '人类'
            const isVerification = c.type === 'verification'
            const isRuling = c.type === 'human_ruling'
            const isDiscussion = c.type === 'discussion'
            const bgColor = isHuman
              ? (isRuling ? 'bg-amber-50 border-amber-200' : isDiscussion ? 'bg-blue-50 border-blue-200' : 'bg-slate-50 border-slate-200')
              : 'bg-green-50 border-green-200'
            return (
              <div key={c.id} className={`p-3 rounded-lg border ${bgColor}`}>
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant={isHuman ? (isRuling ? 'default' : 'secondary') : 'outline'} className="text-xs">
                    {isHuman ? (isRuling ? '👤 人类裁决' : isDiscussion ? '👤 人类评论' : '👤 人类') : `🤖 ${c.author}`}
                  </Badge>
                  {isVerification && <Badge variant="outline" className="text-xs">验证结果</Badge>}
                  <span className="text-xs text-slate-400 ml-auto">{formatDate(c.created_at)}</span>
                </div>
                <p className="text-sm text-slate-700 whitespace-pre-wrap">{c.content}</p>
                {c.metadata?.verification_cycle && (
                  <p className="text-xs text-slate-400 mt-1">验证轮次: {c.metadata.verification_cycle}/3</p>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
