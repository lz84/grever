import { useState, useEffect } from "react"
import { GRASP } from "../../shared/api/paths"
import { Brain, Plus, Search, RefreshCw, Loader2, CheckCircle, XCircle } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/components/ui/card"
import { Badge } from "@/shared/components/ui/badge"
import { Button } from "@/shared/components/ui/button"
import { Input } from "@/shared/components/ui/input"
import { Label } from "@/shared/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/components/ui/table"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/shared/components/ui/tabs"
import { Textarea } from "@/shared/components/ui/textarea"

interface CognitiveEntry {
  id: string
  type: string
  query: string
  response: string
  sources: string[]
  confidence: number
  created_at: string
  agent_id: string
}

export function CognitiveCenter() {
  const [loading, setLoading] = useState(false)
  const [entries, setEntries] = useState<CognitiveEntry[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [filterType, setFilterType] = useState("all")
  const [showCreate, setShowCreate] = useState(false)
  const [newQuery, setNewQuery] = useState("")
  const [newResponse, setNewResponse] = useState("")
  const [newSources, setNewSources] = useState("")
  const [page, setPage] = useState(1)
  const pageSize = 20

  useEffect(() => {
    loadEntries()
  }, [filterType])

  const loadEntries = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: "100" })
      if (filterType !== "all") params.append("type", filterType)

      const res = await fetch(GRASP.COGNITION_LIST + `?${params}`)
      if (res.ok) {
        const data = await res.json()
        setEntries(data.entries || [])
      }
    } catch {
      setEntries([])
    } finally {
      setLoading(false)
    }
  }

  const filteredEntries = entries.filter((e) => {
    const matchesSearch =
      !searchQuery ||
      e.query.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.response.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesSearch
  })

  const paginatedEntries = filteredEntries.slice(
    (page - 1) * pageSize,
    page * pageSize
  )

  const totalPages = Math.ceil(filteredEntries.length / pageSize)

  const handleCreateEntry = async () => {
    if (!newQuery.trim()) return
    try {
      const res = await fetch(GRASP.COGNITION_LIST, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: newQuery,
          response: newResponse,
          sources: newSources.split("\n").map((s) => s.trim()).filter(Boolean),
          type: "knowledge",
          confidence: 0.95,
        }),
      })
      if (res.ok) {
        setNewQuery("")
        setNewResponse("")
        setNewSources("")
        setShowCreate(false)
        loadEntries()
      }
    } catch (err) {
      console.error("Failed to create entry:", err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Brain className="h-8 w-8" />
            认知中心
          </h1>
          <p className="text-muted-foreground mt-1">
            管理和查询认知知识库
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadEntries} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Button onClick={() => setShowCreate(!showCreate)}>
            <Plus className="mr-2 h-4 w-4" />
            添加知识
          </Button>
        </div>
      </div>

      {/* Create new entry */}
      {showCreate && (
        <Card>
          <CardHeader>
            <CardTitle>添加认知条目</CardTitle>
            <CardDescription>向知识库添加新的问答对</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="new-query">问题</Label>
              <Textarea
                id="new-query"
                placeholder="输入问题..."
                rows={2}
                value={newQuery}
                onChange={(e) => setNewQuery(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-response">回答</Label>
              <Textarea
                id="new-response"
                placeholder="输入回答..."
                rows={3}
                value={newResponse}
                onChange={(e) => setNewResponse(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-sources">来源 (每行一个)</Label>
              <Textarea
                id="new-sources"
                placeholder="https://example.com&#10;文档链接..."
                rows={2}
                value={newSources}
                onChange={(e) => setNewSources(e.target.value)}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCreate(false)}>
                取消
              </Button>
              <Button onClick={handleCreateEntry} disabled={!newQuery.trim()}>
                保存
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filter bar */}
      <div className="flex gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="搜索知识库..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>
        <Select value={filterType} onValueChange={setFilterType}>
          <SelectTrigger className="w-[160px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="knowledge">知识</SelectItem>
            <SelectItem value="faq">FAQ</SelectItem>
            <SelectItem value="procedure">流程</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Entries list */}
      {loading ? (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </CardContent>
        </Card>
      ) : filteredEntries.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            暂无知识条目
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="space-y-3">
            {paginatedEntries.map((entry) => (
              <Card key={entry.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-base">{entry.query}</CardTitle>
                        <Badge variant="outline">{entry.type}</Badge>
                        {entry.confidence >= 0.8 ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-amber-500" />
                        )}
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{entry.response}</p>
                  {entry.sources && entry.sources.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {entry.sources.map((source, i) => (
                        <Badge key={i} variant="secondary" className="text-xs">
                          {source}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
                    <span>Agent: {entry.agent_id}</span>
                    <span>{new Date(entry.created_at).toLocaleString()}</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                上一页
              </Button>
              <span className="text-sm text-muted-foreground">
                {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                下一页
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default CognitiveCenter;
