/**
 * 迭代操作组件
 * 支持迭代分析、共识、讨论
 * 调用 goalsApi.iterationAnalysis / iterationConsensus / iterationDiscuss
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { Loader2, Send, MessageSquare, Users, BarChart3, CheckCircle, ChevronDown, ChevronRight } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Input } from '@/shared/components/ui/input'
import { Textarea } from '@/shared/components/ui/textarea'
import { Card, CardContent } from '@/shared/components/ui/card'
import { goalsApi } from '@/shared/utils/api'

interface GoalIterationActionsProps {
  goalId: string
  iterationId: string
  iterationNumber?: string | number
}

interface DiscussMessage {
  id?: string
  role: 'ai' | 'human' | 'system'
  content: string
  author?: string
  created_at?: string
}

export default function GoalIterationActions({ goalId, iterationId, iterationNumber }: GoalIterationActionsProps) {
  const [activeTab, setActiveTab] = useState<'analysis' | 'consensus' | 'discuss'>('discuss')
  const [loading, setLoading] = useState(false)

  return (
    <div className="space-y-2">
      {/* Tab Switcher */}
      <div className="flex gap-1 bg-muted p-1 rounded-lg">
        {[
          { key: 'discuss' as const, label: '讨论', icon: MessageSquare },
          { key: 'analysis' as const, label: '分析', icon: BarChart3 },
          { key: 'consensus' as const, label: '共识', icon: Users },
        ].map(tab => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded text-xs font-medium transition-all ${
              activeTab === tab.key
                ? 'bg-background shadow-sm text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <tab.icon className="w-3 h-3" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'discuss' && (
        <IterationDiscuss goalId={goalId} iterationId={iterationId} />
      )}
      {activeTab === 'analysis' && (
        <IterationAnalysis goalId={goalId} iterationId={iterationId} iterationNumber={iterationNumber} />
      )}
      {activeTab === 'consensus' && (
        <IterationConsensus goalId={goalId} iterationId={iterationId} />
      )}
    </div>
  )
}

// ── 迭代讨论 ──────────────────────────────────────────────────────────────

function IterationDiscuss({ goalId, iterationId }: { goalId: string; iterationId: string }) {
  const [messages, setMessages] = useState<DiscussMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loaded, setLoaded] = useState(false)

  async function loadMessages() {
    try {
      const resp = await goalsApi.iterationDiscuss(goalId, iterationId, {} as any)
      const msgs = Array.isArray(resp) ? resp : resp?.messages || []
      setMessages(msgs)
      setLoaded(true)
    } catch {
      setLoaded(true)
    }
  }

  async function handleSend() {
    if (!input.trim() || sending) return
    setSending(true)
    try {
      const resp = await goalsApi.iterationDiscuss(goalId, iterationId, {
        message: input.trim(),
      })
      setInput('')
      const msgs = Array.isArray(resp) ? resp : resp?.messages || []
      setMessages(msgs)
      toast.success('消息已发送')
    } catch (e: any) {
      toast.error('发送失败: ' + (e.message || '未知错误'))
    } finally {
      setSending(false)
    }
  }

  if (!loaded) {
    return (
      <div className="text-center py-3">
        <Button size="sm" variant="ghost" onClick={loadMessages}>
          <ChevronDown className="w-3 h-3 mr-1" /> 加载讨论
        </Button>
      </div>
    )
  }

  return (
    <Card className="border-slate-200">
      <CardContent className="p-3">
        {messages.length > 0 ? (
          <div className="space-y-2 mb-3 max-h-[200px] overflow-y-auto">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'human' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] px-3 py-1.5 rounded-lg text-sm ${
                  msg.role === 'ai'
                    ? 'bg-blue-50 text-blue-900 border border-blue-200'
                    : msg.role === 'system'
                    ? 'bg-amber-50 text-amber-800 border border-amber-200 text-xs'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-3 text-muted-foreground text-sm">
            暂无讨论，开始第一轮讨论
          </div>
        )}
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入讨论内容..."
            className="flex-1 text-sm h-8"
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
          />
          <Button size="sm" onClick={handleSend} disabled={!input.trim() || sending} className="h-8 w-8 p-0">
            {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// ── 迭代分析 ──────────────────────────────────────────────────────────────

function IterationAnalysis({ goalId, iterationId, iterationNumber }: { goalId: string; iterationId: string; iterationNumber?: string | number }) {
  const [analysis, setAnalysis] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)

  async function runAnalysis() {
    setLoading(true)
    try {
      const resp = await goalsApi.iterationAnalysis(goalId, iterationId)
      setAnalysis(resp)
      toast.success('分析已生成')
    } catch (e: any) {
      toast.error('分析失败: ' + (e.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  if (!analysis) {
    return (
      <Card className="border-slate-200">
        <CardContent className="p-4 text-center">
          <BarChart3 className="w-8 h-8 mx-auto mb-2 text-muted-foreground opacity-40" />
          <p className="text-sm text-muted-foreground mb-3">对第 {iterationNumber} 轮迭代进行 AI 分析</p>
          <Button size="sm" onClick={runAnalysis} disabled={loading}>
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <BarChart3 className="w-3.5 h-3.5 mr-1" />}
            {loading ? '分析中...' : '运行分析'}
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-slate-200">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium flex items-center gap-1">
            <BarChart3 className="w-3.5 h-3.5 text-blue-500" />
            分析结果
          </h4>
          <Button size="sm" variant="outline" onClick={runAnalysis} disabled={loading}>
            重新分析
          </Button>
        </div>

        {analysis?.analysis || analysis?.summary ? (
          <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
            {analysis.analysis || analysis.summary}
          </div>
        ) : null}

        {analysis?.score != null && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">评分:</span>
            <Badge variant="default">{typeof analysis.score === 'number' ? analysis.score.toFixed(2) : analysis.score}</Badge>
          </div>
        )}

        {analysis?.suggestions && (
          <div>
            <h5 className="text-xs font-medium text-slate-600 mb-1">建议</h5>
            <div className="text-sm text-slate-700 whitespace-pre-wrap">
              {typeof analysis.suggestions === 'string' ? analysis.suggestions : JSON.stringify(analysis.suggestions)}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ── 迭代共识 ──────────────────────────────────────────────────────────────

function IterationConsensus({ goalId, iterationId }: { goalId: string; iterationId: string }) {
  const [consensus, setConsensus] = useState<string>('')
  const [existingConsensus, setExistingConsensus] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSaveConsensus() {
    if (!consensus.trim() || saving) return
    setSaving(true)
    try {
      await goalsApi.iterationConsensus(goalId, iterationId, { consensus: consensus.trim() })
      setExistingConsensus(consensus.trim())
      setConsensus('')
      toast.success('共识已达成')
    } catch (e: any) {
      toast.error('保存共识失败: ' + (e.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card className="border-slate-200">
      <CardContent className="p-4 space-y-3">
        {existingConsensus ? (
          <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-1 mb-1">
              <CheckCircle className="w-3.5 h-3.5 text-green-600" />
              <span className="text-xs font-medium text-green-800">已达成共识</span>
            </div>
            <p className="text-sm text-green-900 whitespace-pre-wrap">{existingConsensus}</p>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-1 text-sm font-medium">
              <Users className="w-3.5 h-3.5 text-purple-500" />
              达成共识
            </div>
            <Textarea
              value={consensus}
              onChange={(e) => setConsensus(e.target.value)}
              placeholder="输入本轮迭代的共识结论..."
              className="text-sm min-h-[80px]"
              rows={3}
            />
            <Button
              size="sm"
              onClick={handleSaveConsensus}
              disabled={!consensus.trim() || saving}
              className="w-full"
            >
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <CheckCircle className="w-3.5 h-3.5 mr-1" />}
              {saving ? '保存中...' : '达成共识'}
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}
