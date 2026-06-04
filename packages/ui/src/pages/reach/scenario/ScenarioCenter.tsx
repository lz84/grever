import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { goalsApi, scenariosApi, type Goal, type Scenario } from "@/shared/utils/api"
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
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card"
import { Badge } from "@/shared/components/ui/badge"
import CreateGoal from "@/pages/reins/goal/CreateGoal"

const ScenarioFormSchema = z.object({
  title: z.string().min(2, "标题至少 2 个字符").max(200, "标题最多 200 个字符"),
  description: z.string().max(2000, "描述最多 2000 个字符").optional(),
  goal_id: z.string().min(1, "请选择关联目标"),
  priority: z.enum(["low", "medium", "high", "critical"], {
    required_error: "请选择优先级",
  }),
  tags: z.string().optional(),
})

type ScenarioFormData = z.infer<typeof ScenarioFormSchema>

export function ScenarioCenter() {
  const [goals, setGoals] = useState<Goal[]>([])
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [isSubmittingScenario, setIsSubmittingScenario] = useState(false)
  const [showCreateGoal, setShowCreateGoal] = useState(false)
  const [selectedGoalId, setSelectedGoalId] = useState<string>("")

  const {
    register: registerScenario,
    handleSubmit: handleSubmitScenario,
    reset: resetScenario,
    setValue: setValueScenario,
    watch: watchScenario,
    formState: { errors: errorsScenario },
  } = useForm<ScenarioFormData>({
    resolver: zodResolver(ScenarioFormSchema),
    defaultValues: {
      priority: "medium",
      goal_id: "",
    },
  })

  const goalId = watchScenario("goal_id")

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [goalsData, scenariosData] = await Promise.all([
        goalsApi.list(),
        scenariosApi.list(),
      ])
      setGoals(Array.isArray(goalsData) ? goalsData : [])
      setScenarios(Array.isArray(scenariosData) ? scenariosData : [])
    } catch (err) {
      console.error("Failed to load data:", err)
      setGoals([])
      setScenarios([])
    }
  }

  const onSubmitScenario = async (data: ScenarioFormData) => {
    setIsSubmittingScenario(true)
    try {
      const payload = {
        ...data,
        description: data.description || "",
        tags: data.tags?.split(",").map((t) => t.trim()).filter(Boolean) || [],
      }
      const newScenario = await scenariosApi.create(payload as any)
      setScenarios((prev) => [...prev, newScenario])
      resetScenario()
      setSelectedGoalId("")
    } catch (err) {
      console.error("Failed to create scenario:", err)
    } finally {
      setIsSubmittingScenario(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">场景中心</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: Create Scenario Form */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>创建场景</CardTitle>
              <CardDescription>创建一个新的测试场景</CardDescription>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={handleSubmitScenario(onSubmitScenario)}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label htmlFor="scenario-title">场景标题 *</Label>
                  <Input
                    id="scenario-title"
                    placeholder="输入场景标题"
                    {...registerScenario("title")}
                  />
                  {errorsScenario.title && (
                    <p className="text-sm text-red-500">
                      {errorsScenario.title.message}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="scenario-goal">关联目标 *</Label>
                    <Button
                      type="button"
                      variant="link"
                      className="h-auto p-0 text-xs"
                      onClick={() => setShowCreateGoal(!showCreateGoal)}
                    >
                      {showCreateGoal ? "关闭" : "+ 创建新目标"}
                    </Button>
                  </div>
                  {showCreateGoal && (
                    <div className="mb-2">
                      <CreateGoal
                        onCreated={(g: Goal) => {
                          setGoals((prev) => [...prev, g])
                          setValueScenario("goal_id", g.id)
                          setShowCreateGoal(false)
                        }}
                        onCancel={() => setShowCreateGoal(false)}
                      />
                    </div>
                  )}
                  <Select
                    value={goalId}
                    onValueChange={(v) => setValueScenario("goal_id", v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="选择关联目标" />
                    </SelectTrigger>
                    <SelectContent>
                      {goals.map((g) => (
                        <SelectItem key={g.id} value={g.id}>
                          {g.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errorsScenario.goal_id && (
                    <p className="text-sm text-red-500">
                      {errorsScenario.goal_id.message}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="scenario-description">场景描述</Label>
                  <Textarea
                    id="scenario-description"
                    placeholder="详细描述场景..."
                    rows={3}
                    {...registerScenario("description")}
                  />
                  {errorsScenario.description && (
                    <p className="text-sm text-red-500">
                      {errorsScenario.description.message}
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="scenario-priority">优先级 *</Label>
                    <Select
                      defaultValue="medium"
                      onValueChange={(v) =>
                        setValueScenario("priority", v as any)
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="选择优先级" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">🟢 低</SelectItem>
                        <SelectItem value="medium">🟡 中</SelectItem>
                        <SelectItem value="high">🟠 高</SelectItem>
                        <SelectItem value="critical">🔴 紧急</SelectItem>
                      </SelectContent>
                    </Select>
                    {errorsScenario.priority && (
                      <p className="text-sm text-red-500">
                        {errorsScenario.priority.message}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="scenario-tags">标签 (逗号分隔)</Label>
                    <Input
                      id="scenario-tags"
                      placeholder="api, frontend"
                      {...registerScenario("tags")}
                    />
                    {errorsScenario.tags && (
                      <p className="text-sm text-red-500">
                        {errorsScenario.tags.message}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => resetScenario()}
                    disabled={isSubmittingScenario}
                  >
                    重置
                  </Button>
                  <Button type="submit" disabled={isSubmittingScenario}>
                    {isSubmittingScenario ? "创建中..." : "创建场景"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Right: Scenario List */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>场景列表</CardTitle>
              <CardDescription>
                {scenarios.length} 个场景
              </CardDescription>
            </CardHeader>
            <CardContent>
              {scenarios.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  暂无场景，请创建一个
                </p>
              ) : (
                <div className="space-y-3">
                  {scenarios.map((scenario) => (
                    <div
                      key={scenario.id}
                      className="rounded-lg border p-3"
                    >
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <p className="font-medium">
                            {scenario.title}
                          </p>
                          {scenario.description && (
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {scenario.description}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1">
                        <Badge variant="outline" className="text-xs">
                          {scenario.priority || "medium"}
                        </Badge>
                        {scenario.tags?.map((tag) => (
                          <Badge
                            key={tag}
                            variant="secondary"
                            className="text-xs"
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default ScenarioCenter;
