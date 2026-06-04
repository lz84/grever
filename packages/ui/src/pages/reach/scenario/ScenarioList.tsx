import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, RefreshCw, AlertCircle, Search, Star, Loader2, Plus, ChevronDown } from 'lucide-react';
import { Pagination } from '@/shared/components/ui/pagination';
import { scenariosApi, Scenario } from '../../../shared/utils/api';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { executorTypeLabel } from '@/shared/utils/scenariosApi'

const CATEGORY_LABELS: Record<string, string> = {
  earthquake: '地震',
  fire: '火灾',
  chemical: '化学品',
  flood: '防汛',
  general: '通用',
};

const CATEGORY_VARIANTS: Record<string, string> = {
  earthquake: 'destructive',
  fire: 'warning',
  chemical: 'secondary',
  flood: 'info',
  general: 'secondary',
};

const STATUS_LABELS: Record<string, string> = {
  active: '活跃',
  archived: '归档',
  draft: '草稿',
  deprecated: '已废弃',
};

const STATUS_VARIANTS: Record<string, string> = {
  active: 'success',
  archived: 'secondary',
  draft: 'warning',
  deprecated: 'destructive',
};

const LEVEL_LABELS: Record<string, string> = {
  goal: 'Goal级',
  project: 'Project级',
};

const LEVEL_VARIANTS: Record<string, string> = {
  goal: 'info',
  project: 'secondary',
};

const TRUST_LEVEL_VARIANTS: Record<string, string> = {
  high: 'success',
  medium: 'warning',
  low: 'secondary',
};

const SOURCE_LABELS: Record<string, string> = {
  manual: '手动创建',
  ai_generated: 'AI生成',
  execution_flowback: '执行回流',
  cognitive_derived: '认知推导',
  execution_derived: '执行推导',
  template: '模板创建',
  evolved: '自动演化',
};

function getSuccessRateColor(rate: number): string {
  if (rate >= 90) return 'text-green-600';
  if (rate >= 70) return 'text-blue-600';
  if (rate >= 50) return 'text-orange-600';
  return 'text-red-600';
}

function formatDuration(ms: number): string {
  const mins = Math.round(ms / 60000);
  return `${mins} 分钟`;
}

const ITEMS_PER_PAGE = 10;

export default function ScenarioList() {
  const navigate = useNavigate();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [sortBy, setSortBy] = useState<string>('success_rate');
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);

  // Track expanded rows by scenario id
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const toggleRow = (id: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Load starred from localStorage
  const [starredIds, setStarredIds] = useState(new Set());
  useEffect(() => {
    try {
      const stored = localStorage.getItem('nexus_starred_scenarios');
      if (stored) {
        const parsed = JSON.parse(stored);
        setStarredIds(new Set(Object.keys(parsed)));
      }
    } catch {}
  }, []);

  const toggleStar = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const stored = JSON.parse(localStorage.getItem('nexus_starred_scenarios') || '{}');
    if (stored[id]) {
      delete stored[id];
    } else {
      const scenario = scenarios.find(s => s.id === id);
      if (scenario) {
        stored[id] = {
          name: scenario.name,
          category: scenario.category,
          status: scenario.status,
          version: scenario.version,
          description: scenario.scenario_desc,
          starredAt: new Date().toISOString(),
        };
      }
    }
    localStorage.setItem('nexus_starred_scenarios', JSON.stringify(stored));
    setStarredIds(new Set(Object.keys(stored)));
  };

  const loadScenarios = async () => {
    setLoading(true);
    try {
      const page = currentPage - 1;
      const pageSize = ITEMS_PER_PAGE;
      const res = await scenariosApi.list({
        source: sourceFilter || undefined,
        category: categoryFilter || undefined,
        status: statusFilter || undefined,
        page: page + 1,
        page_size: pageSize,
      });
      if (res.items) {
        setScenarios(res.items);
        setTotal(res.total || res.items.length);
      } else {
        setScenarios([]);
        setTotal(0);
      }
      setError(null);
    } catch (err) {
      console.error('Failed to load scenarios:', err);
      setError('加载场景失败，请稍后重试');
      setScenarios([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadScenarios();
  }, [currentPage, categoryFilter, statusFilter, sourceFilter]);

  const filteredScenarios = useMemo(() => {
    let result = [...scenarios];
    if (categoryFilter) result = result.filter(s => s.category === categoryFilter);
    if (statusFilter) result = result.filter(s => s.status === statusFilter);
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(s =>
        s.name.toLowerCase().includes(q) ||
        s.scenario_desc.toLowerCase().includes(q)
      );
    }
    result.sort((a, b) => {
      if (sortBy === 'success_rate') return b.success_rate - a.success_rate;
      if (sortBy === 'usage_count') return b.usage_count - a.usage_count;
      if (sortBy === 'avg_duration_ms') return (a.avg_duration_ms ?? 0) - (b.avg_duration_ms ?? 0);
      if (sortBy === 'updated_at') return new Date(b.updated_at ?? 0).getTime() - new Date(a.updated_at ?? 0).getTime();
      return 0;
    });
    return result;
  }, [scenarios, categoryFilter, statusFilter, searchQuery, sortBy]);

  const totalPages = Math.max(1, Math.ceil(total / ITEMS_PER_PAGE));
  const paginatedScenarios = filteredScenarios.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  const handleReset = () => {
    setSearchQuery('');
    setCategoryFilter('');
    setStatusFilter('');
    setSourceFilter('');
    setSortBy('success_rate');
    setCurrentPage(1);
  };

  const categories = ['earthquake', 'fire', 'chemical', 'flood', 'general'];
  const statuses = ['active', 'archived', 'draft'];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <FileText className="w-5 h-5 text-muted-foreground" />
            场景库
          </h1>
          <p className="text-sm text-muted-foreground mt-1">从认知中抽取的标准化场景</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate('/scenarios/starred')}>
            <Star className="w-4 h-4" />
            收藏
          </Button>
          <Button onClick={() => navigate('/scenarios/new')}>
            <Plus className="w-4 h-4" />
            创建场景
          </Button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-md px-4 py-3 text-destructive text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={e => { setSearchQuery(e.target.value); setCurrentPage(1) }}
            placeholder="搜索场景..."
            className="pl-10"
          />
        </div>

        <Select value={categoryFilter || 'all'} onValueChange={(v) => { setCategoryFilter(v); setCurrentPage(1); }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="全部分类" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部分类</SelectItem>
            {categories.map(c => (
              <SelectItem key={c} value={c}>{CATEGORY_LABELS[c]}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={statusFilter || 'all'} onValueChange={(v) => { setStatusFilter(v); setCurrentPage(1); }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            {statuses.map(s => (
              <SelectItem key={s} value={s}>{STATUS_LABELS[s]}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={sourceFilter || 'all'} onValueChange={(v) => { setSourceFilter(v); setCurrentPage(1); }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="全部来源" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部来源</SelectItem>
            <SelectItem value="manual">手动创建</SelectItem>
            <SelectItem value="ai_generated">AI生成</SelectItem>
            <SelectItem value="execution_flowback">执行回流</SelectItem>
            <SelectItem value="cognitive_derived">认知推导</SelectItem>
            <SelectItem value="execution_derived">执行推导</SelectItem>
            <SelectItem value="template">模板创建</SelectItem>
            <SelectItem value="evolved">自动演化</SelectItem>
          </SelectContent>
        </Select>

        <Select value={sortBy} onValueChange={setSortBy}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="排序方式" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="success_rate">按成功率排序</SelectItem>
            <SelectItem value="usage_count">按使用次数</SelectItem>
            <SelectItem value="avg_duration_ms">按平均耗时</SelectItem>
            <SelectItem value="updated_at">按更新时间</SelectItem>
          </SelectContent>
        </Select>

        {(categoryFilter || statusFilter || sourceFilter || searchQuery) && (
          <Button variant="ghost" size="sm" onClick={handleReset}>
            重置筛选
          </Button>
        )}

        <Button variant="outline" size="icon" onClick={loadScenarios} title="刷新">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-lg border overflow-hidden">
        {filteredScenarios.length === 0 ? (
          <div className="text-center py-16">
            <FileText className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground">未找到匹配的场景</p>
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>场景名称</TableHead>
                  <TableHead>分类</TableHead>
                  <TableHead>等级</TableHead>
                  <TableHead>可信度</TableHead>
                  <TableHead>来源</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>版本</TableHead>
                  <TableHead>项目数</TableHead>
                  <TableHead>执行模式</TableHead>
                  <TableHead>能力标签</TableHead>
                  <TableHead>成功率</TableHead>
                  <TableHead>平均耗时</TableHead>
                  <TableHead>使用次数</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedScenarios.map((scenario: any) => {
                  const isExpanded = expandedRows.has(scenario.id);
                  const hasRequirements = scenario.agent_requirements && scenario.agent_requirements.length > 0;
                  
                  return (
                    <>
                      <TableRow
                        key={scenario.id}
                        className="cursor-pointer"
                        onClick={() => navigate(`/scenarios/${scenario.id}`)}
                      >
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={(e) => toggleStar(scenario.id, e)}
                              className="text-muted-foreground hover:text-yellow-500"
                            >
                              <Star className={`w-4 h-4 ${starredIds.has(scenario.id) ? 'fill-yellow-400 text-yellow-400' : ''}`} />
                            </button>
                            <span className="font-medium text-foreground hover:text-primary">
                              {scenario.name}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={CATEGORY_VARIANTS[scenario.category] as any}>
                            {CATEGORY_LABELS[scenario.category]}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {scenario.level && (
                            <Badge variant={LEVEL_VARIANTS[scenario.level] as any}>
                              {LEVEL_LABELS[scenario.level]}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {scenario.trust_level && (
                            <Badge variant={TRUST_LEVEL_VARIANTS[scenario.trust_level] as any}>
                              {scenario.trust_level}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <span className="text-xs text-muted-foreground">
                            {SOURCE_LABELS[scenario.source] || scenario.source}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge variant={STATUS_VARIANTS[scenario.status] as any}>
                            {STATUS_LABELS[scenario.status]}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <span className="text-foreground">{scenario.version}</span>
                        </TableCell>
                        <TableCell>
                          <span className="text-foreground">{scenario.project_count ?? 0}</span>
                        </TableCell>
                        <TableCell>
                          {scenario.executor_type && (
                            <Badge variant="outline" className="text-xs">
                              {executorTypeLabel(scenario.executor_type)}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {scenario.goal_capability_tags ? (
                            <div className="flex flex-wrap gap-1 max-w-[200px]">
                              {Object.keys(scenario.goal_capability_tags).slice(0, 3).map((key: string) => (
                                <Badge key={key} variant="outline" className="text-[10px] px-1 py-0">
                                  {key}
                                </Badge>
                              ))}
                              {Object.keys(scenario.goal_capability_tags).length > 3 && (
                                <span className="text-[10px] text-muted-foreground">+{Object.keys(scenario.goal_capability_tags).length - 3}</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <span className={`font-medium ${getSuccessRateColor(scenario.success_rate)}`}>
                            {scenario.success_rate.toFixed(1)}%
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className="text-foreground">{formatDuration(scenario.avg_duration_ms)}</span>
                        </TableCell>
                        <TableCell>
                          <span className="text-foreground">{scenario.usage_count}次</span>
                        </TableCell>
                      </TableRow>
                      {hasRequirements && (
                        <TableRow 
                          key={`${scenario.id}-expand`}
                          className="bg-muted cursor-pointer"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleRow(scenario.id);
                          }}
                        >
                          <TableCell colSpan={12}>
                            <div className="flex items-center text-sm">
                              <span className="mr-2 font-medium">Agent需求:</span>
                              {isExpanded ? '收起' : '展开'}
                              <ChevronDown className={`w-4 h-4 ml-1 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                            </div>
                            {isExpanded && (
                              <div className="mt-2 pl-4">
                                <ul className="list-disc list-inside text-sm">
                                  {scenario.agent_requirements.map((req: any, idx: number) => (
                                    <li key={idx} className="text-muted-foreground">{req}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </TableCell>
                        </TableRow>
                      )}
                    </>
                  )
                })}
              </TableBody>
            </Table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-6 py-3 border-t">
                <div className="text-sm text-muted-foreground">
                  显示第 {(currentPage - 1) * ITEMS_PER_PAGE + 1} - {Math.min(currentPage * ITEMS_PER_PAGE, total)} 项，共 {total} 项
                </div>
                <Pagination 
                  currentPage={currentPage} 
                  totalPages={totalPages} 
                  onPageChange={setCurrentPage} 
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
