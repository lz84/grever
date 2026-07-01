/**
 * HITLQuestionPage.tsx - Sprint 2 s2-5
 * Human-in-the-Loop Question Page for Planning Session Tier-0 Questions
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Loader2, CheckCircle, Brain, MessageSquare,
  AlertCircle, ArrowRight, ChevronDown, ChevronUp,
} from 'lucide-react'
import {
  Card, CardContent, CardHeader, CardTitle,
} from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Textarea } from '@/shared/components/ui/textarea'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/components/ui/select'
import { toast } from 'sonner'
import { goalHitlApi, type Tier0Question } from '@/shared/utils/api'

// Types

interface SessionInfo {
  sessionId: string
  goalId: string
  goalTitle: string
}

interface ProjectQuestion {
  question_id: string
  question_text: string
  question_type: string
  options?: string[]
  category: string
  reason?: string
  impact?: string
  answered: boolean
  answer?: string
}

// Question Card Component
function QuestionCard({
  question,
  answer,
  onAnswer,
  index,
}: {
  question: Tier0Question
  answer: string
  onAnswer: (qid: string, value: string) => void
  index: number
}) {
  const [expanded, setExpanded] = useState(false)

  const categoryColors: Record<string, string> = {
    scope: 'border-l-blue-400 bg-blue-50',
    constraint: 'border-l-amber-400 bg-amber-50',
    resource: 'border-l-emerald-400 bg-emerald-50',
    quality: 'border-l-purple-400 bg-purple-50',
    general: 'border-l-slate-400 bg-slate-50',
  }

  const colorClass = categoryColors[question.category] || categoryColors.general

  return (
    <Card className={`border-l-4 ${colorClass}`}>
      <CardHeader className="pb-2 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="outline" className="text-xs">
                Q{index + 1}
              </Badge>
              <Badge variant="secondary" className="text-xs">
                {question.category}
              </Badge>
            </div>
            <CardTitle className="text-base font-medium">
              {question.question_text}
            </CardTitle>
            {question.reason && (
              <div className="flex items-center gap-1 text-xs text-amber-600 mt-2">
                <AlertCircle className="w-3 h-3" />
                <span className="font-medium">原因/影响: </span>
                <span className="text-amber-500">{question.reason}</span>
                {question.impact && <span className="ml-1">({question.impact})</span>}
              </div>
            )}
          </div>
          <div className="flex items-center gap-1">
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronUp className="w-4 h-4 text-muted-foreground" />
            )}
          </div>
        </div>
      </CardHeader>
      {expanded && (
        <CardContent>
          {question.question_type === 'text' && (
            <div className="space-y-2">
              <Textarea
                value={answer}
                onChange={(e) => onAnswer(question.question_id, e.target.value)}
                placeholder="请输入你的回答..."
                rows={3}
                className="mb-2"
              />
            </div>
          )}
          {question.question_type === 'choice' && question.options && (
            <Select value={answer} onValueChange={(v) => onAnswer(question.question_id, v)}>
              <SelectTrigger>
                <SelectValue placeholder="请选择..." />
              </SelectTrigger>
              <SelectContent>
                {question.options.map((opt: string, i: number) => (
                  <SelectItem key={i} value={opt}>{opt}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {question.question_type === 'boolean' && (
            <div className="flex gap-2">
              <Button
                variant={answer === 'yes' ? 'default' : 'outline'}
                size="sm"
                onClick={() => onAnswer(question.question_id, 'yes')}
              >
                <CheckCircle className="w-4 h-4 mr-1" /> 是
              </Button>
              <Button
                variant={answer === 'no' ? 'default' : 'outline'}
                size="sm"
                onClick={() => onAnswer(question.question_id, 'no')}
              >
                <AlertCircle className="w-4 h-4 mr-1" /> 否
              </Button>
            </div>
          )}
          {question.question_type === 'number' && (
            <input
              type="number"
              value={answer}
              onChange={(e) => onAnswer(question.question_id, e.target.value)}
              placeholder="请输入数字..."
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
            />
          )}
        </CardContent>
      )}
    </Card>
  )
}

// Main Component
export default function HITLQuestionPage() {
  const { sessionId } = useParams<{ sessionId?: string }>()
  const navigate = useNavigate()

  // State
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [questions, setQuestions] = useState<Tier0Question[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [goalId, setGoalId] = useState<string>('')

  // Load questions from API
  const loadQuestions = useCallback(async () => {
    if (!sessionId) {
      setError('Missing planning_session_id')
      setLoading(false)
      return
    }

    try {
      // First, get session info to extract goal_id
      const sessionData = await fetch(`/api/v1/planning-sessions/${sessionId}`).then(res => res.json())
      
      if (!sessionData || !sessionData.goal_id) {
        throw new Error('Failed to fetch session info')
      }
      
      const goalId = sessionData.goal_id
      setGoalId(goalId)
      
      // Fetch pending questions for this goal
      const questionsData = await goalHitlApi.getPendingQuestions(goalId)
      
      setSessionInfo({
        sessionId,
        goalId,
        goalTitle: sessionData.goal_title || '未知目标',
      })
      
      setQuestions(Array.isArray(questionsData) ? questionsData : (questionsData as any)?.questions || [])
      setLoading(false)
    } catch (e: any) {
      setError(e.message || '加载问题失败')
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => {
    loadQuestions()
  }, [loadQuestions])

  // Handle answer change
  const handleAnswer = useCallback((questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }))
  }, [])

  // Check if all questions are answered
  const allAnswered = questions.every((q) => answers[q.question_id]?.trim())

  // Submit answers
  const handleSubmit = async () => {
    if (!goalId) return
    setSubmitting(true)
    try {
      // Convert answers to the format expected by the API
      const answersArray = Object.entries(answers).map(([question_id, answer]) => ({
        question_id,
        answer,
      }))

      // Submit answers to the backend
      await goalHitlApi.submitAnswers(goalId, answersArray as any)

      toast.success('问题已提交！')
      setTimeout(() => {
        navigate(-1) // Go back
      }, 1500)
    } catch (e: any) {
      toast.error(e.message || '提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">加载问题中...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertCircle className="w-8 h-8 text-destructive mb-4" />
        <p className="text-destructive mb-4">{error}</p>
        <Button variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-4 h-4 mr-1" /> 返回
        </Button>
      </div>
    )
  }

  return (
    <div className="w-full min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between max-w-3xl mx-auto">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <Brain className="w-5 h-5 text-blue-500" />
                等待你确认以下问题
              </h1>
              {sessionInfo && (
                <p className="text-sm text-muted-foreground">
                  目标: {sessionInfo.goalTitle}
                </p>
              )}
            </div>
          </div>
          {sessionId && (
            <Badge variant="outline" className="text-xs">
              {sessionId.slice(0, 12)}...
            </Badge>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-3xl mx-auto p-6">
        {/* Introduction */}
        <Card className="mb-6 bg-blue-50 border-blue-200">
          <CardContent className="pt-6">
            <div className="flex items-start gap-2">
              <MessageSquare className="w-5 h-5 text-blue-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-blue-800 mb-2">为了提供更准确的分解，我需要了解一些额外信息。请回答以下问题：</p>
                <p className="text-sm text-blue-900">
                  请根据你的实际情况回答，这将直接影响分解方案的合理性和可行性。
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Questions */}
        {questions.length === 0 ? (
          <Card>
            <CardContent className="pt-6 flex flex-col items-center justify-center py-12">
              <MessageSquare className="w-12 h-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4 text-center">
                暂无待回答的问题。
              </p>
              <Button variant="outline" onClick={() => navigate(-1)}>
                返回
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            <div className="space-y-4 mb-6">
              {questions.map((q, i) => (
                <QuestionCard
                  key={q.question_id}
                  question={q}
                  answer={answers[q.question_id] || ''}
                  onAnswer={handleAnswer}
                  index={i}
                />
              ))}
            </div>

            {/* Submit */}
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                已回答 {Object.keys(answers).length} / {questions.length} 个问题
              </p>
              <Button
                onClick={handleSubmit}
                disabled={!allAnswered || submitting}
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                    提交中...
                  </>
                ) : (
                  <>
                    提交答案
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </>
                )}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
