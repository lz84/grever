/**
 * EvaluationDecomposeHITL.tsx
 * 
 * E-1~E-4 HITL 问答页面
 * 
 * 用户在创建 Goal 后，如果 Agent 返回 insufficient + Tier 0 问题，
 * 则跳转到此页面进行问答交互。
 * 
 * 流程：
 * 1. 用户回答 Tier 0 问题
 * 2. 提交答案 (E-3)
 * 3. 获取最终分解结果 (E-4)
 * 4. 显示分解预览
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, ArrowRight, Loader2, CheckCircle, AlertCircle,
  Brain, MessageSquare, ChevronDown, ChevronUp,
} from 'lucide-react';
import {
  Card, CardContent, CardHeader, CardTitle,
} from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';
import { Textarea } from '@/shared/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/components/ui/select';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from '@/shared/components/ui/dialog';
import { evaluationDecomposeApi, type Tier0Question, goalHitlApi } from '@/shared/utils/api';
import { goalsApi } from '@/shared/utils/api';
import { toast } from 'sonner';

// ============================================================================
// Types
// ============================================================================

interface Answer {
  question_id: string;
  answer: string;
}

interface DecompositionProject {
  name: string;
  description?: string;
  tasks: Array<{ title: string; type: string; description?: string }>;
}

interface FinalResult {
  readiness: string;
  projects: DecompositionProject[];
  assumptions: string[];
  default_applied: boolean;
  agent_message: string;
}

// ============================================================================
// Question Card Component
// ============================================================================

function QuestionCard({
  question,
  answer,
  onAnswer,
  index,
}: {
  question: Tier0Question;
  answer: string;
  onAnswer: (qid: string, value: string) => void;
  index: number;
}) {
  const categoryColors: Record<string, string> = {
    scope: 'border-l-blue-400 bg-blue-50',
    constraint: 'border-l-amber-400 bg-amber-50',
    resource: 'border-l-emerald-400 bg-emerald-50',
    quality: 'border-l-purple-400 bg-purple-50',
    general: 'border-l-slate-400 bg-slate-50',
  };

  const colorClass = categoryColors[question.category] || categoryColors.general;

  return (
    <Card className={`border-l-4 ${colorClass}`}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="outline" className="text-xs">
                Q{index + 1}
              </Badge>
              <Badge variant="secondary" className="text-xs">
                {question.category}
              </Badge>
              <Badge variant="outline" className="text-xs capitalize">
                {question.question_type}
              </Badge>
            </div>
            <CardTitle className="text-base font-medium">
              {question.question_text}
            </CardTitle>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {question.question_type === 'text' && (
          <Textarea
            value={answer}
            onChange={(e) => onAnswer(question.question_id, e.target.value)}
            placeholder="请输入你的回答..."
            rows={3}
            className="mb-2"
          />
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
    </Card>
  );
}

// ============================================================================
// Decomposition Preview Component
// ============================================================================

function DecompositionPreview({
  result,
  onConfirm,
  onCancel,
}: {
  result: FinalResult;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="space-y-4">
      {/* Status Banner */}
      {result.default_applied && (
        <Card className="border-amber-400 bg-amber-50">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-amber-800">
              <AlertCircle className="w-5 h-5" />
              <span className="font-medium">使用了默认分解模板</span>
            </div>
            <p className="text-sm text-amber-700 mt-1">
              由于信息不足，系统使用了默认分解模板。请确认以下分解结果是否合适。
            </p>
          </CardContent>
        </Card>
      )}

      {/* Agent Message */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="w-4 h-4 text-blue-500" />
            Agent 分析结果
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{result.agent_message}</p>
        </CardContent>
      </Card>

      {/* Assumptions */}
      {result.assumptions && result.assumptions.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-500" />
              假设条件
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {result.assumptions.map((a, i) => (
                <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">•</span>
                  {a}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Projects */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-emerald-500" />
          分解结果 ({result.projects.length} 个项目)
        </h3>
        {result.projects.map((project, pi) => (
          <Card key={pi}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">
                📁 {project.name}
              </CardTitle>
              {project.description && (
                <p className="text-xs text-muted-foreground">{project.description}</p>
              )}
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                {project.tasks && project.tasks.map((task, ti) => (
                  <div key={ti} className="flex items-center gap-2 text-sm">
                    <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0" />
                    <span>{task.title}</span>
                    <Badge variant="outline" className="text-[10px] h-4">
                      {task.type}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-3 justify-end pt-4 border-t">
        <Button variant="outline" onClick={onCancel}>
          返回修改
        </Button>
        <Button onClick={onConfirm}>
          <CheckCircle className="w-4 h-4 mr-1" />
          确认分解
        </Button>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function EvaluationDecomposeHITL() {
  const { goalId } = useParams<{ goalId: string }>();
  const [searchParams] = useSearchParams();
  const planningSessionId = searchParams.get('planning_session_id');
  const navigate = useNavigate();

  // State
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [phase, setPhase] = useState<'questions' | 'preview'>('questions');
  const [questions, setQuestions] = useState<Tier0Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [agentMessage, setAgentMessage] = useState<string>('');
  const [result, setResult] = useState<FinalResult | null>(null);
  const [goalInfo, setGoalInfo] = useState<{ title: string; description: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch initial status and Tier 0 questions
  const loadStatus = useCallback(async () => {
    if (!planningSessionId || !goalId) {
      setError('Missing required parameters');
      setLoading(false);
      return;
    }
    try {
      // Load status and questions in parallel
      const [status, questionsData] = await Promise.all([
        evaluationDecomposeApi.getStatus(planningSessionId),
        goalHitlApi.getPendingQuestions(goalId).catch(() => null),
      ]);

      // Set agent message if available
      const questionsList = Array.isArray(questionsData) ? questionsData : (questionsData as any)?.questions || []
      if (questionsList.length > 0) {
        setQuestions(questionsList);
      } else if (status.tier0_questions_count > 0) {
        // Fallback: if no questions loaded, show placeholder message
        setAgentMessage('请回答以下问题以帮助我更好地理解您的需求：');
        setQuestions([]);
      }

      setLoading(false);
    } catch (e: any) {
      setError(e.message || 'Failed to load status');
      setLoading(false);
    }
  }, [planningSessionId, goalId]);

  // Fetch goal info
  const loadGoalInfo = useCallback(async () => {
    if (!goalId) return;
    try {
      const goals = await goalsApi.list();
      const goal = goals.find((g: any) => g.id === goalId);
      if (goal) {
        setGoalInfo({ title: goal.title || '', description: goal.description || '' });
      }
    } catch (e) {
      console.error('Failed to load goal info:', e);
    }
  }, [goalId]);

  useEffect(() => {
    loadStatus();
    loadGoalInfo();
  }, [loadStatus, loadGoalInfo]);

  // Handle answer change
  const handleAnswer = useCallback((questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  }, []);

  // Check if all required questions are answered
  const allAnswered = questions.every((q) => answers[q.question_id]?.trim());

  // Submit E-3 and get E-4 result
  const handleSubmit = async () => {
    if (!planningSessionId || !goalId) return;
    setSubmitting(true);
    try {
      // Convert answers to the format expected by the API
      const answersArray = Object.entries(answers).map(([question_id, answer]) => ({
        question_id,
        answer,
      }));

      // Submit answers to the backend
      const result = await goalHitlApi.submitAnswers(goalId, answersArray as any);
      console.log('Submit result:', result);

      // If the response indicates sufficient data, get the final decomposition
      if (result.sufficient && result.decomposition) {
        setResult(result.decomposition);
        setPhase('preview');
        toast.success('分解完成！');
      } else if (result.remaining_questions && result.remaining_questions.length > 0) {
        // Still have remaining questions
        setQuestions(result.remaining_questions);
        setAnswers({});
        toast.info('还有问题需要回答');
      }

      setSubmitting(false);
    } catch (e: any) {
      toast.error(e.message || '提交失败');
      setSubmitting(false);
    }
  };

  // Confirm decomposition and navigate to decompose page
  const handleConfirm = () => {
    if (!goalId) return;
    navigate(`/goals/${goalId}/decompose`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">加载中...</span>
      </div>
    );
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
    );
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
                目标分解问答
              </h1>
              {goalInfo && (
                <p className="text-sm text-muted-foreground">
                  目标: {goalInfo.title}
                </p>
              )}
            </div>
          </div>
          <Badge variant="outline" className="text-xs">
            {planningSessionId?.slice(0, 12)}...
          </Badge>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-3xl mx-auto p-6">
        {phase === 'questions' && (
          <>
            {/* Agent Message */}
            {agentMessage && (
              <Card className="mb-6 bg-blue-50 border-blue-200">
                <CardContent className="pt-4">
                  <div className="flex items-start gap-2">
                    <Brain className="w-5 h-5 text-blue-500 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-blue-800 mb-1">Agent 分析</p>
                      <p className="text-sm text-blue-900">{agentMessage}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Questions */}
            {questions.length === 0 ? (
              <Card>
                <CardContent className="pt-6 flex flex-col items-center justify-center py-12">
                  <MessageSquare className="w-12 h-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground mb-4 text-center">
                    暂无待回答的问题。
                    <br />
                    您可以直接确认分解结果，或返回目标详情页。
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
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">
                      已回答 {Object.keys(answers).filter(k => answers[k]?.trim()).length} / {questions.length} 个问题
                    </p>
                    {/* Progress bar */}
                    <div className="w-48 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 transition-all duration-300"
                        style={{
                          width: `${questions.length > 0 ? (Object.keys(answers).filter(k => answers[k]?.trim()).length / questions.length) * 100 : 0}%`,
                        }}
                      />
                    </div>
                  </div>
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
          </>
        )}

        {phase === 'preview' && result && (
          <DecompositionPreview
            result={result}
            onConfirm={handleConfirm}
            onCancel={() => setPhase('questions')}
          />
        )}
      </div>
    </div>
  );
}
