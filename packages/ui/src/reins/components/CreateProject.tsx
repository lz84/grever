import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Plus, Loader2 } from "lucide-react"
import { projectsApi, goalsApi } from "@/shared/utils/api"
import type { Project, Goal } from "@/shared/utils/api"
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
import { toast } from "sonner"

const CreateProjectSchema = z.object({
  name: z.string().min(2, { message: "名称至少 2 个字符" }).max(200),
  description: z.string().max(2000).optional(),
  goal_id: z.string().min(1, { message: "请选择关联目标" }),
  priority: z.enum(["low", "medium", "high", "critical"]).optional(),
})

type CreateProjectData = z.infer<typeof CreateProjectSchema>

interface CreateProjectProps {
  onCreated?: (project: Project) => void
  onCancel?: () => void
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export function CreateProject({ onCreated, onCancel, open = true, onOpenChange }: CreateProjectProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [goals, setGoals] = useState<Goal[]>([])

  const form = useForm<CreateProjectData>({
    resolver: zodResolver(CreateProjectSchema),
    mode: "onChange",
    defaultValues: {
      name: "",
      description: "",
      goal_id: "",
      priority: "medium",
    },
  })

  useEffect(() => {
    goalsApi.list().then(setGoals).catch(console.error)
  }, [])

  const onSubmit = async (data: CreateProjectData) => {
    setIsSubmitting(true)
    try {
      const newProject = await projectsApi.create({
        name: data.name,
        description: data.description || "",
        goal_id: data.goal_id,
        priority: data.priority,
      })
      form.reset()
      if (newProject && onCreated) onCreated(newProject)
      onOpenChange?.(false)
      toast.success("工程创建成功")
    } catch (e: any) {
      toast.error(`创建失败: ${e.message}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = () => {
    form.reset()
    onCancel?.()
    onOpenChange?.(false)
  }

  const formContent = (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>工程名称 *</FormLabel>
              <FormControl>
                <Input placeholder="输入工程名称" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>工程描述</FormLabel>
              <FormControl>
                <Textarea placeholder="详细描述工程内容..." rows={3} {...field} value={field.value || ""} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="goal_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>关联目标 *</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="选择关联目标" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {goals.map((g) => (
                    <SelectItem key={g.id} value={g.id}>
                      {g.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="priority"
          render={({ field }) => (
            <FormItem>
              <FormLabel>优先级</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="选择优先级" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="low">低</SelectItem>
                  <SelectItem value="medium">中</SelectItem>
                  <SelectItem value="high">高</SelectItem>
                  <SelectItem value="critical">紧急</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleCancel} disabled={isSubmitting}>
            取消
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> 创建中...</>
            ) : (
              <><Plus className="mr-2 h-4 w-4" /> 创建工程</>
            )}
          </Button>
        </DialogFooter>
      </form>
    </Form>
  )

  if (onOpenChange !== undefined) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>创建工程</DialogTitle>
            <DialogDescription>填写工程信息，创建后系统将自动分配任务</DialogDescription>
          </DialogHeader>
          {formContent}
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <div className="rounded-lg border p-4 space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <Plus className="h-5 w-5" />
        <h3 className="text-lg font-semibold">创建工程</h3>
      </div>
      {formContent}
    </div>
  )
}

export default CreateProject
