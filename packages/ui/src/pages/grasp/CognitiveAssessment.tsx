import { useState, useEffect } from 'react'
import { GRASP } from '../../shared/api/paths'
import { agentsApi } from '../../shared/utils/api'
import { Brain, Activity, Target, BookOpen, Zap, TrendingUp, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Progress } from '@/shared/components/ui/progress'

function getScoreColor(score: number) {
  if (score >= 90) return 'text-green-600'
  if (score >= 80) return 'text-blue-600'
  if (score >= 70) return 'text-amber-600'
  return 'text-red-600'
}

function getScoreVariant(score: number) {
  if (score >= 90) return 'success'
  if (score >= 80) return 'info'
  if (score >= 70) return 'warning'
  return 'destructive'
}

function getStatusBadgeVariant(status: string) {
  const s = status.toLowerCase()
  if (s === 'online' || s === 'active' || s === 'running') return 'success'
  if (s === 'busy' || s === 'processing') return 'warning'
  return 'secondary'
}

function getStatusLabel(status: string) {
  const s = status.toLowerCase()
  if (s === 'online' || s === 'active' || s === 'running') return '在线'
  if (s === 'busy' || s === 'processing') return '忙碌'
  if (s === 'offline' || s === 'disconnected') return '离线'
  return '空闲'
}

export default function CognitiveAssessment() {
  const [cognitiveAgents, setCognitiveAgents] = useState<CognitiveAgent[]>([])
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState('')

  async function fetchData() {
    try {
      setLoading(true)
      const agents = await agentsApi.list()

      // 并行获取每个 agent 的认知评估
      const agentPromises = agents.map(async (agent) => {
        let assessment = null
        let fetchFailed = false
        try {
          const res = await fetch(GRASP.COGNITION_ASSESSMENT(agent.id))
          if (!res.ok) {
            fetchFailed = true
          } else {
            assessment = await res.json()
          }
        } catch {
          fetchFailed = true
        }

        const scores = assessment?.dimensions
          ? {
              understanding: Math.round((assessment.dimensions.retrieval_quality?.score || 0.8) * 100),
              reasoning: Math.round((assessment.dimensions.context_utilization?.score || 0.75) * 100),
              memory: Math.round((assessment.dimensions.injection_accuracy?.score || 0.7) * 100),
              decision: Math.round((assessment.dimensions.knowledge_freshness?.score || 0.72) * 100),
            }
          : { understanding: 0, reasoning: 0, memory: 0, decision: 0 }

        return {
          id: agent.id,
          name: agent.name,
          scores,
          status: agent.status || 'idle',
          currentTask: agent.current_tasks ? `${agent.current_tasks} 个任务运行中` : '空闲',
          knowledgeUsed: assessment?.knowledge_used ?? 0,
          plansApplied: assessment?.plans_applied ?? 0,
          assessment,
          fetchFailed,
        }
      })

      const results = await Promise.all(agentPromises)
      const hasFailure = results.some(r => r.fetchFailed)
      if (hasFailure) {
        setApiError('部分 Agent 认知评估接口调用失败，请检查后端服务是否正常运行')
      } else {
        setApiError('')
      }
      setCognitiveAgents(results)
    } catch (e) {
      setApiError('认知评估加载失败，请检查后端服务是否正常运行')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000) // 60s refresh
    return () => clearInterval(interval)
  }, [])

  // 计算总体指标
  const avgUnderstanding = cognitiveAgents.length > 0
    ? Math.round(cognitiveAgents.reduce((s, a) => s + a.scores.understanding, 0) / cognitiveAgents.length)
    : 0
  const avgReasoning = cognitiveAgents.length > 0
    ? Math.round(cognitiveAgents.reduce((s, a) => s + a.scores.reasoning, 0) / cognitiveAgents.length)
    : 0
  const totalKnowledgeUsed = cognitiveAgents.reduce((s, a) => s + a.knowledgeUsed, 0)
  const avgDecision = cognitiveAgents.length > 0
    ? Math.round(cognitiveAgents.reduce((s, a) => s + a.scores.decision, 0) / cognitiveAgents.length)
    : 0

  // 知识调用热力数据（基于 agent 实际数据）
  const heatData = cognitiveAgents.length > 0
    ? cognitiveAgents.map(a => ({
        name: a.name,
        calls: a.knowledgeUsed,
        max: Math.max(1, ...cognitiveAgents.map(x => x.knowledgeUsed)),
      }))
    : []

  if (loading && cognitiveAgents.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Brain className="w-10 h-10 text-muted-foreground animate-spin mx-auto mb-3" />
          <p className="text-muted-foreground">加载中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页眉 */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-500" />
            认知评估
          </h2>
          <p className="text-muted-foreground text-sm mt-1">Grasp 认知底座：智能体理解深度与推理能力评估</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <span className="text-sm text-muted-foreground">实时评估</span>
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
        </div>
      </div>

      {/* 错误提示 */}
      {apiError && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg px-4 py-3 text-sm text-destructive flex items-start gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <span>{apiError}</span>
        </div>
      )}

      {/* 总体认知指标 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Target className="w-4 h-4 text-purple-500" />
            总体认知指标
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {/* 平均理解度 */}
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-50 rounded-lg">
                  <Brain className="w-5 h-5 text-blue-500" />
                </div>
                <span className="text-sm text-muted-foreground">平均理解度</span>
              </div>
              <div className={`text-3xl font-bold ${getScoreColor(avgUnderstanding)}`}>
                {avgUnderstanding}%
              </div>
              <Progress value={avgUnderstanding} className="h-1.5" />
              <div className="text-xs text-muted-foreground">平均值</div>
            </div>

            {/* 平均推理力 */}
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-50 rounded-lg">
                  <TrendingUp className="w-5 h-5 text-green-500" />
                </div>
                <span className="text-sm text-muted-foreground">平均推理力</span>
              </div>
              <div className={`text-3xl font-bold ${getScoreColor(avgReasoning)}`}>
                {avgReasoning}%
              </div>
              <Progress value={avgReasoning} className="h-1.5" />
              <div className="text-xs text-muted-foreground">平均值</div>
            </div>

            {/* 知识调用 */}
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-50 rounded-lg">
                  <BookOpen className="w-5 h-5 text-purple-500" />
                </div>
                <span className="text-sm text-muted-foreground">知识调用</span>
              </div>
              <div className="text-3xl font-bold text-purple-600">
                {totalKnowledgeUsed}
              </div>
              <div className="text-xs text-muted-foreground">总调用次数</div>
            </div>

            {/* 决策质量 */}
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-50 rounded-lg">
                  <Target className="w-5 h-5 text-amber-500" />
                </div>
                <span className="text-sm text-muted-foreground">决策质量</span>
              </div>
              <div className={`text-3xl font-bold ${getScoreColor(avgDecision)}`}>
                {avgDecision}%
              </div>
              <Progress value={avgDecision} className="h-1.5" />
              <div className="text-xs text-muted-foreground">平均值</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 智能体认知评估卡片 */}
      {cognitiveAgents.length === 0 ? (
        <Card>
          <CardContent className="text-center py-16">
            <Brain className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
            <p className="text-lg mb-2">暂无智能体数据</p>
            <p className="text-sm text-muted-foreground">请先注册 Agent</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {cognitiveAgents.map(agent => (
            <Card key={agent.id}>
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-blue-500" />
                    {agent.name}
                  </CardTitle>
                  <Badge variant={getStatusBadgeVariant(agent.status)}>
                    {getStatusLabel(agent.status)}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-5">
                  {/* 认知维度 */}
                  <div className="space-y-3">
                    <h4 className="text-sm font-medium text-foreground">认知维度</h4>
                    <div className="space-y-3">
                      {[{
                        label: '理解深度',
                        value: agent.scores.understanding,
                        color: getScoreColor(agent.scores.understanding),
                      }, {
                        label: '推理能力',
                        value: agent.scores.reasoning,
                        color: getScoreColor(agent.scores.reasoning),
                      }, {
                        label: '记忆保持',
                        value: agent.scores.memory,
                        color: getScoreColor(agent.scores.memory),
                      }, {
                        label: '决策质量',
                        value: agent.scores.decision,
                        color: getScoreColor(agent.scores.decision),
                      }].map(dim => (
                        <div key={dim.label}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-muted-foreground">{dim.label}</span>
                            <span className={`font-bold ${dim.color}`}>{dim.value}%</span>
                          </div>
                          <Progress value={dim.value} className="h-2" />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 当前任务 */}
                  <div className="bg-muted/50 p-3 rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">当前任务</p>
                    <p className="text-sm font-medium">{agent.currentTask}</p>
                  </div>

                  {/* 知识调用 */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">知识调用:</span>
                      <span className="font-mono font-bold">{agent.knowledgeUsed}</span>
                      <span className="text-muted-foreground">次</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">预案:</span>
                      <span className="font-mono font-bold">{agent.plansApplied}</span>
                      <span className="text-muted-foreground">个</span>
                    </div>
                  </div>

                  {/* 预警 */}
                  {agent.scores.decision < 80 && (
                    <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <div className="text-xs">
                        <p className="font-medium mb-1">注意</p>
                        <p>决策质量低于 80%，建议增强知识注入</p>
                      </div>
                    </div>
                  )}
                  {agent.scores.decision >= 90 && (
                    <div className="flex items-start gap-2 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700">
                      <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <div className="text-xs">
                        <p className="font-medium mb-1">优秀</p>
                        <p>认知状态优秀，可承担更复杂任务</p>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 知识调用热图 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-500" />
            知识调用热力
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-4">
            {heatData.map(item => {
              const intensity = item.calls / item.max
              return (
                <div key={item.name} className="flex flex-col items-center gap-2">
                  <div
                    className="w-full h-16 rounded-lg flex items-center justify-center text-sm font-bold text-white"
                    style={{
                      backgroundColor: `rgba(59, 130, 246, ${intensity * 0.8 + 0.2})`,
                    }}
                  >
                    {item.calls}
                  </div>
                  <p className="text-xs text-muted-foreground text-center">{item.name}</p>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

interface CognitiveScores {
  understanding: number
  reasoning: number
  memory: number
  decision: number
}

interface CognitiveAgent {
  id: string
  name: string
  scores: CognitiveScores
  status: string
  currentTask: string
  knowledgeUsed: number
  plansApplied: number
  assessment?: any
  fetchFailed: boolean
}
