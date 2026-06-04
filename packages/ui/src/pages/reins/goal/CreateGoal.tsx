import { useState, useEffect } from "react"
import { GRASP } from "../../../shared/api/paths"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Brain, Plus, Loader2, Zap, Settings, FileText } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { goalsApi, type Goal, AttachmentUploaderApi } from "@/shared/utils/api"
import { solutionsApi } from "@/evo/services/solutions"
import { Button } from "@/shared/components/ui/button"
import { Input } from "@/shared/components/ui/input"
import { Label } from "@/shared/components/ui/label"
import { Textarea } from "@/shared/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/shared/components/ui/form"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog"
import { AttachmentUploader } from "@/reins/components/AttachmentUploader"
import { toast } from "sonner"

const CreateGoalSchema = z.object({
  title: z.string().min(2, { message: "标题至少 2 个字符" }).max(200, { message: "标题最多 200 个字符" }),
  description: z.string().max(2000, { message: "描述最多 2000 个字符" }).optional(),
  priority: z.enum(["low", "medium", "high", "critical"], {
    required_error: "请选择优先级",
    invalid_type_error: "请选择优先级",
  }),
  deadline: z.string().optional(),
  workspace_path: z.string().min(1, { message: "工作目录不能为空" }),
  mode: z.enum(["normal", "exploration", "optimization"]).optional(),
  optimization_target: z.enum(["duration", "cost", "overall"]).optional(),
  convergence_threshold: z.coerce.number().min(0.01).max(1).optional(),
  max_rounds: z.coerce.number().int().min(1).max(100).optional(),
})

type CreateGoalData = z.infer<typeof CreateGoalSchema>

interface CreateGoalProps {
  onCreated?: (goal: Goal) => void
  onCancel?: () => void
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export function CreateGoal({ onCreated, onCancel, open = true, onOpenChange }: CreateGoalProps) {
  const navigate = useNavigate()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [graspInjected, setGraspInjected] = useState(false)
  const [graspLoading, setGraspLoading] = useState(false)
  const [createdGoalId, setCreatedGoalId] = useState<string>("")

  const form = useForm<CreateGoalData>({
    resolver: zodResolver(CreateGoalSchema),
    mode: "onChange",
    defaultValues: {
      mode: "normal",
      workspace_path: "",
      optimization_target: undefined,
      convergence_threshold: undefined,
      max_rounds: undefined,
    },
  })

  // Grasp 认知注入：当用户输入标题时，自动从认知库获取相关上下文
  useEffect(() => {
    const title = form.watch("title")
    if (title && title.length > 5) {
      const timer = setTimeout(async () => {
        setGraspLoading(true)
        try {
          const res = await fetch(GRASP.KNOWLEDGE_LIST + `?q=${encodeURIComponent(title)}&limit=3`)
          if (res.ok) {
            const data = await res.json()
            if (data.cognitions && data.cognitions.length > 0) {
              const existingDesc = form.getValues("description") || ""
              const graspContent = data.cognitions
                .map((c: any) => c.content || "")
                .filter(Boolean)
                .join("\n\n")
              if (graspContent && !existingDesc.includes(graspContent.substring(0, 50))) {
                form.setValue("description", existingDesc ? `${existingDesc}\n\n--- 认知注入 ---\n${graspContent}` : graspContent)
                setGraspInjected(true)
              }
            }
          }
        } catch {
          // 忽略认知注入错误
        } finally {
          setGraspLoading(false)
        }
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [form.watch("title")])

  const onSubmit = async (data: CreateGoalData) => {
    setIsSubmitting(true)
    try {
      const newGoal = await goalsApi.create({
        ...data,
        description: data.description || "",
        workspace_type: "local",
        workspace_path: data.workspace_path,
      })
      
      // 设置 createdGoalId 用于附件上传
      if (newGoal?.id) {
        setCreatedGoalId(newGoal.id)
      }
      
      // If exploration or optimization mode, set the goal mode via API
      if (newGoal?.id && (data.mode === "exploration" || data.mode === "optimization")) {
        try {
          await solutionsApi.setGoalMode(newGoal.id, {
            mode: data.mode,
            optimization_target: data.optimization_target,
            convergence_threshold: data.convergence_threshold,
            max_rounds: data.max_rounds,
          })
        } catch (modeErr) {
          console.warn(`Failed to set ${data.mode} mode:`, modeErr)
          toast.warning(`目标已创建，但${data.mode === 'exploration' ? '探索' : '迭代'}模式参数设置失败，可稍后重试`)
        }
      }
      form.reset()
      setGraspInjected(false)
      if (newGoal && onCreated) {
        onCreated(newGoal)
      }
      onOpenChange?.(false)
      // 作为独立页面时，跳转到目标详情页
      if (newGoal?.id) {
        navigate(`/coordination/goals/${newGoal.id}`)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = () => {
    form.reset()
    setGraspInjected(false)
    onCancel?.()
    onOpenChange?.(false)
    // 作为独立页面时，返回目标列表
    navigate("/coordination/goals")
  }

  const currentMode = form.watch("mode")
  const isExploration = currentMode === "exploration"
  const isOptimization = currentMode === "optimization"
  const isAdvancedMode = isExploration || isOptimization

  const formContent = (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>目标标题 *</FormLabel>
              <FormControl>
                <Input placeholder="输入目标标题" {...field} />
              </FormControl>
              <FormDescription>至少 2 个字符，最多 200 个字符</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>目标描述</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="详细描述目标内容..."
                  rows={4}
                  {...field}
                  value={field.value || ""}
                />
              </FormControl>
              {graspInjected && (
                <div className="flex items-center gap-1 text-xs text-blue-500">
                  <Brain className="h-3 w-3" />
                  <span>已注入 Grasp 认知上下文</span>
                  {graspLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                </div>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="priority"
            render={({ field }) => (
              <FormItem>
                <FormLabel>优先级 *</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="选择优先级" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="low">🟢 低</SelectItem>
                    <SelectItem value="medium">🟡 中</SelectItem>
                    <SelectItem value="high">🟠 高</SelectItem>
                    <SelectItem value="critical">🔴 紧急</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="deadline"
            render={({ field }) => (
              <FormItem>
                <FormLabel>截止日期</FormLabel>
                <FormControl>
                  <Input type="date" {...field} value={field.value || ""} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="workspace_path"
          render={({ field }) => (
            <FormItem>
              <FormLabel>工作目录 *</FormLabel>
              <FormControl>
                <Input placeholder="例如：D:\work\projects\goal-001" {...field} />
              </FormControl>
              <FormDescription>目标的工作目录路径，本地路径（必填）</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* ── Mode Selection ─────────────────────────────────── */}
        <FormField
          control={form.control}
          name="mode"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="flex items-center gap-1.5">
                <Zap className="w-4 h-4 text-amber-500" />
                运行模式
              </FormLabel>
              <div className="flex gap-2">
                {[
                  { value: "normal" as const, label: "常规模式", desc: "标准执行流程" },
                  { value: "optimization" as const, label: "迭代模式", desc: "持续优化，逐步收敛" },
                  { value: "exploration" as const, label: "探索模式", desc: "多方案探索，找到最优解" },
                ].map(opt => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => field.onChange(opt.value)}
                    className={`flex-1 p-3 rounded-lg border-2 text-left transition-all ${
                      field.value === opt.value
                        ? "border-blue-500 bg-blue-50"
                        : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <div className="text-sm font-medium text-slate-800">{opt.label}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{opt.desc}</div>
                  </button>
                ))}
              </div>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* ── Exploration/Optimization Mode Fields ────────────────────────── */}
        {isAdvancedMode && (
          <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4 space-y-4">
            <div className="flex items-center gap-1.5 text-amber-800 text-sm font-medium">
              <Settings className="w-4 h-4" />
              {isExploration ? '探索模式参数' : '迭代模式参数'}
            </div>

            <FormField
              control={form.control}
              name="optimization_target"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>优化目标</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="选择优化目标" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="duration">🏃 最短工期</SelectItem>
                      <SelectItem value="cost">💰 最低成本</SelectItem>
                      <SelectItem value="overall">⚖️ 综合最优</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormDescription>探索模式将以此目标进行方案优化</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="convergence_threshold"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>收敛阈值</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="0.01"
                        min="0.01"
                        max="1"
                        placeholder="0.05"
                        {...field}
                        value={field.value || ""}
                        onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : undefined)}
                      />
                    </FormControl>
                    <FormDescription>默认 0.05（5%），改进低于此值时触发收敛</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="max_rounds"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>最大轮次</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="1"
                        min="1"
                        max="100"
                        placeholder="10"
                        {...field}
                        value={field.value || ""}
                        onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                      />
                    </FormControl>
                    <FormDescription>最大迭代轮次，默认 10</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          </div>
        )}

        {/* ── Attachment Upload (Sprint 84) ─────────────────────────────────── */}
        <div>
          <h4 className="flex items-center gap-2 text-sm font-medium mb-1">
            <FileText className="h-4 w-4 text-slate-500" />
            附件 (可选)
          </h4>
          <p className="text-xs text-slate-500 mb-2">
            上传相关文档、截图等附件。创建目标后会自动关联。
          </p>
        </div>

        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4">
          <AttachmentUploader
            entityType="goal"
            entityId={createdGoalId || ''}
            maxSize={50 * 1024 * 1024}
            onUploadComplete={(att) => {
              console.log('Attachment uploaded:', att)
            }}
          />
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleCancel} disabled={isSubmitting}>
            取消
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                创建中...
              </>
            ) : (
              <>
                <Plus className="mr-2 h-4 w-4" />
                创建目标
              </>
            )}
          </Button>
        </DialogFooter>
      </form>
    </Form>
  )

  // If Dialog control is provided, wrap in Dialog
  if (onOpenChange !== undefined) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-2xl max-h-[95vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-blue-500" />
              创建目标
            </DialogTitle>
            <DialogDescription>
              填写目标信息，创建后系统将自动分解任务
            </DialogDescription>
          </DialogHeader>
          {formContent}
        </DialogContent>
      </Dialog>
    )
  }

  // Otherwise, render inline form
  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="flex items-center gap-2 mb-4">
        <Brain className="h-5 w-5 text-blue-500" />
        <h3 className="text-lg font-semibold">创建目标</h3>
      </div>
      {formContent}
    </div>
  )
}

export default CreateGoal
