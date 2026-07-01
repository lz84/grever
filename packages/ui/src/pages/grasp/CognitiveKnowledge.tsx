import { useState, useEffect } from "react"
import { GRASP } from "../../shared/api/paths"
import { BookOpen, Search, Loader2, Brain, Zap, Lightbulb, Info } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card"
import { Badge } from "@/shared/components/ui/badge"
import { Input } from "@/shared/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select"

interface Cognition {
  cognition_id: string
  type: string
  content: string
  tags: string[]
  confidence: number
  quality_score: number
  source: { agent_id: string; task_id: string; channel: string }
  status: string
  domain: string
  metadata: Record<string, unknown>
  version: number
}

const TYPE_ICONS: Record<string, React.ReactNode> = {
  fact: <Info className="h-4 w-4 text-blue-500" />,
  pattern: <Zap className="h-4 w-4 text-yellow-500" />,
  lesson: <Lightbulb className="h-4 w-4 text-green-500" />,
}

const TYPE_LABELS: Record<string, string> = {
  fact: "事实",
  pattern: "模式",
  lesson: "经验",
}

const STATUS_COLORS: Record<string, string> = {
  published: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  pending_review: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  archived: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200",
}

export function CognitiveKnowledge() {
  const [items, setItems] = useState<Cognition[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState("")
  const [filterType, setFilterType] = useState("all")
  const [filterDomain, setFilterDomain] = useState("all")
  const [domains, setDomains] = useState<string[]>([])

  useEffect(() => {
    loadItems()
  }, [filterType])

  const loadItems = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: "100" })
      if (filterType !== "all") params.append("type", filterType)
      const res = await fetch(`${GRASP.KNOWLEDGE_LIST}?${params}`)
      if (res.ok) {
        const data = await res.json()
        const list: Cognition[] = data.cognitions || []
        setItems(list)
        const d = [...new Set(list.map((c: Cognition) => c.domain).filter(Boolean))]
        setDomains(d)
      } else {
        setItems([])
      }
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  const filteredItems = items.filter((item) => {
    if (search) {
      const q = search.toLowerCase()
      if (
        !item.content.toLowerCase().includes(q) &&
        !item.tags.some((t) => t.toLowerCase().includes(q)) &&
        !item.cognition_id.toLowerCase().includes(q)
      ) {
        return false
      }
    }
    if (filterDomain !== "all" && item.domain !== filterDomain) return false
    return true
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <BookOpen className="h-8 w-8" />
          认知知识库
        </h1>
        <p className="text-muted-foreground mt-1">
          展示系统自动积累的认知（事实、模式、经验），支持搜索和过滤
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索内容、标签、ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={filterType} onValueChange={setFilterType}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="fact">事实</SelectItem>
            <SelectItem value="pattern">模式</SelectItem>
            <SelectItem value="lesson">经验</SelectItem>
          </SelectContent>
        </Select>
        {domains.length > 0 && (
          <Select value={filterDomain} onValueChange={setFilterDomain}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部领域</SelectItem>
              {domains.map((d) => (
                <SelectItem key={d} value={d}>{d}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Stats */}
      <div className="flex gap-4 text-sm text-muted-foreground">
        <span>共 <strong className="text-foreground">{items.length}</strong> 条认知</span>
        <span>筛选后 <strong className="text-foreground">{filteredItems.length}</strong> 条</span>
      </div>

      {/* Items */}
      {loading ? (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </CardContent>
        </Card>
      ) : filteredItems.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            暂无认知条目
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {filteredItems.map((item) => (
            <Card key={item.cognition_id}>
              <CardHeader className="pb-2">
                <div className="flex items-start gap-2">
                  <div className="mt-1">
                    {TYPE_ICONS[item.type] || <Brain className="h-4 w-4 text-muted-foreground" />}
                  </div>
                  <div className="space-y-1 flex-1">
                    <CardTitle className="text-base">{item.content.slice(0, 60)}{item.content.length > 60 ? "..." : ""}</CardTitle>
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="outline">
                        {TYPE_LABELS[item.type] || item.type}
                      </Badge>
                      {item.domain && (
                        <Badge variant="secondary">{item.domain}</Badge>
                      )}
                      <Badge className={STATUS_COLORS[item.status] || ""}>
                        {item.status === "published" ? "已发布" : item.status === "pending_review" ? "待审核" : item.status}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        置信度 {(item.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {item.content.length > 60 && (
                  <p className="text-sm text-muted-foreground line-clamp-3">{item.content}</p>
                )}
                {item.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {item.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">{tag}</Badge>
                    ))}
                  </div>
                )}
                <div className="mt-2 text-xs text-muted-foreground">
                  Agent: {item.source?.agent_id || "—"} | 来源: {item.source?.channel || "—"}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

export default CognitiveKnowledge;
