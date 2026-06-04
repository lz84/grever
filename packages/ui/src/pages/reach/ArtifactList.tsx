import { useState, useEffect } from "react"
import { ARTIFACTS } from "../../shared/api/paths"
import { Search, Download, Copy, CheckCircle, Clock, AlertCircle, RefreshCw, FileText, ExternalLink, Loader2 } from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card"
import { Badge } from "@/shared/components/ui/badge"
import { Button } from "@/shared/components/ui/button"
import { Input } from "@/shared/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select"
import { Label } from "@/shared/components/ui/label"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/shared/components/ui/tabs"

interface Artifact {
  id: string
  type: string
  name: string
  path: string
  content_type: string
  size: number
  created_at: string
  agent_id: string
  metadata: Record<string, any>
}

interface ArtifactListProps {
  agentId?: string
}

const ARTIFACT_TYPE_LABELS: Record<string, string> = {
  code_generation: "代码生成",
  test_case: "测试用例",
  documentation: "文档",
  report: "报告",
  log: "日志",
  screenshot: "截图",
  other: "其他",
}

function getArtifactIcon(type: string) {
  const icons: Record<string, JSX.Element> = {
    code_generation: <FileText className="h-4 w-4" />,
    test_case: <CheckCircle className="h-4 w-4" />,
    documentation: <FileText className="h-4 w-4" />,
    report: <FileText className="h-4 w-4" />,
    log: <Clock className="h-4 w-4" />,
    screenshot: <FileText className="h-4 w-4" />,
  }
  return icons[type] || <FileText className="h-4 w-4" />
}

export function ArtifactList({ agentId }: ArtifactListProps) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [loading, setLoading] = useState(false)
  const [filterType, setFilterType] = useState<string>("all")
  const [filterAgent, setFilterAgent] = useState<string>(agentId || "all")
  const [search, setSearch] = useState("")
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const pageSize = 20

  useEffect(() => {
    setLoading(true)
    fetchArtifacts()
  }, [filterType, filterAgent])

  const fetchArtifacts = async () => {
    try {
      const params = new URLSearchParams()
      if (filterType !== "all") params.append("type", filterType)
      if (filterAgent !== "all") params.append("agent_id", filterAgent)
      params.append("limit", "100")

      const res = await fetch(ARTIFACTS.LIST + `?${params}`)
      if (res.ok) {
        const data = await res.json()
        setArtifacts(data.artifacts || [])
      }
    } catch (err) {
      console.error("Failed to fetch artifacts:", err)
      setArtifacts([])
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async (content: string, id: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error("Copy failed:", err)
    }
  }

  const filteredArtifacts = artifacts.filter((a) => {
    const matchesSearch =
      !search || a.name.toLowerCase().includes(search.toLowerCase())
    return matchesSearch
  })

  const paginatedArtifacts = filteredArtifacts.slice(
    (page - 1) * pageSize,
    page * pageSize
  )

  const totalPages = Math.ceil(filteredArtifacts.length / pageSize)

  const handleDownload = (artifact: Artifact) => {
    const url = ARTIFACTS.DOWNLOAD(artifact.id)
    window.open(url, "_blank")
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">工件列表</h2>
        <Button variant="outline" size="sm" onClick={fetchArtifacts}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      {/* Filter bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <Label htmlFor="search" className="sr-only">搜索</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="搜索工件..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>

            <div className="w-[180px]">
              <Label htmlFor="filter-type" className="sr-only">类型</Label>
              <Select value={filterType} onValueChange={setFilterType}>
                <SelectTrigger id="filter-type">
                  <SelectValue placeholder="全部类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部类型</SelectItem>
                  <SelectItem value="code_generation">代码生成</SelectItem>
                  <SelectItem value="test_case">测试用例</SelectItem>
                  <SelectItem value="documentation">文档</SelectItem>
                  <SelectItem value="report">报告</SelectItem>
                  <SelectItem value="log">日志</SelectItem>
                  <SelectItem value="screenshot">截图</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="w-[180px]">
              <Label htmlFor="filter-agent" className="sr-only">Agent</Label>
              <Select value={filterAgent} onValueChange={setFilterAgent}>
                <SelectTrigger id="filter-agent">
                  <SelectValue placeholder="全部 Agent" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部 Agent</SelectItem>
                  <SelectItem value="kouzi">扣子</SelectItem>
                  <SelectItem value="guzi">谷子</SelectItem>
                  <SelectItem value="gangzi">刚子</SelectItem>
                  <SelectItem value="mazi">麻子</SelectItem>
                  <SelectItem value="wenzi">文子</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Artifact list */}
      {loading ? (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </CardContent>
        </Card>
      ) : filteredArtifacts.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            暂无工件
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="space-y-3">
            {paginatedArtifacts.map((artifact) => (
              <Card key={artifact.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      {getArtifactIcon(artifact.type)}
                      <CardTitle className="text-base">{artifact.name}</CardTitle>
                      <Badge variant="outline">
                        {ARTIFACT_TYPE_LABELS[artifact.type] || artifact.type}
                      </Badge>
                    </div>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          handleCopy(
                            JSON.stringify(artifact.metadata, null, 2),
                            artifact.id
                          )
                        }
                      >
                        {copiedId === artifact.id ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDownload(artifact)}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                      {artifact.path && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => window.open(artifact.path, "_blank")}
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-sm text-muted-foreground">
                    <span>类型: {artifact.content_type}</span>
                    <span className="mx-2">·</span>
                    <span>
                      大小: {(artifact.size / 1024).toFixed(1)} KB
                    </span>
                    <span className="mx-2">·</span>
                    <span>
                      Agent: {artifact.agent_id}
                    </span>
                    <span className="mx-2">·</span>
                    <span>
                      {new Date(artifact.created_at).toLocaleString()}
                    </span>
                  </div>
                  {artifact.metadata && Object.keys(artifact.metadata).length > 0 && (
                    <div className="mt-2 rounded bg-muted p-2">
                      <pre className="text-xs text-muted-foreground overflow-auto max-h-20">
                        {JSON.stringify(artifact.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Pagination */}
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

export default ArtifactList;
