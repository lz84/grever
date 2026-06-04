import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Search, Target, FolderKanban, ListTodo, Loader2, AlertCircle } from 'lucide-react';
import { goalsApi, projectsApi, tasksApi } from '../utils/api';
import type { Goal, Project, Task } from '../utils/api';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/shared/components/ui/command';
import { Badge } from '@/shared/components/ui/badge';

interface SearchResult {
  type: 'goal' | 'project' | 'task'
  data: Goal | Project | Task
}

export default function GlobalSearch() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Debounce search input (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (query.trim().length > 0) {
        handleSearch(query);
      } else {
        setResults([]);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // Keyboard shortcut to open
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setIsOpen((open) => !open);
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  const handleSearch = async (searchQuery: string) => {
    try {
      setLoading(true);
      setError(null);
      
      // 并行搜索目标、工程、任务
      const [goals, projects, tasks] = await Promise.all([
        goalsApi.list({ status: undefined }),
        projectsApi.list({ status: undefined }),
        tasksApi.list(),
      ]);

      const searchResults: SearchResult[] = [];
      
      // 搜索目标
      goals.forEach(goal => {
        const matchFields = [
          goal.title,
          goal.description,
          goal.status,
        ].filter(Boolean).join(' ');
        
        if (matchFields.toLowerCase().includes(searchQuery.toLowerCase())) {
          searchResults.push({ type: 'goal', data: goal as Goal });
        }
      });
      
      // 搜索工程
      projects.forEach(project => {
        const matchFields = [
          project.name,
          project.description,
          project.status,
        ].filter(Boolean).join(' ');
        
        if (matchFields.toLowerCase().includes(searchQuery.toLowerCase())) {
          searchResults.push({ type: 'project', data: project as Project });
        }
      });
      
      // 搜索任务
      tasks.forEach(task => {
        const matchFields = [
          task.title,
          task.description,
          task.status,
          task.assigned_agent,
        ].filter(Boolean).join(' ');
        
        if (matchFields.toLowerCase().includes(searchQuery.toLowerCase())) {
          searchResults.push({ type: 'task', data: task as Task });
        }
      });
      
      setResults(searchResults.slice(0, 10)); // Limit to 10 results
    } catch (e: any) {
      setError(e.message || '搜索失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = useCallback(() => {
    setIsOpen(false);
    setQuery('');
    setResults([]);
    setError(null);
  }, []);

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'goal': return <Target className="w-4 h-4 text-blue-500" />;
      case 'project': return <FolderKanban className="w-4 h-4 text-green-500" />;
      case 'task': return <ListTodo className="w-4 h-4 text-purple-500" />;
      default: return null;
    }
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      goal: '目标',
      project: '工程',
      task: '任务',
    };
    return labels[type] || type;
  };

  const getResultTitle = (result: SearchResult) => {
    if (result.type === 'goal') return (result.data as Goal).title;
    if (result.type === 'project') return (result.data as Project).name;
    if (result.type === 'task') return (result.data as Task).title;
    return '';
  };

  const getResultLink = (result: SearchResult) => {
    if (result.type === 'goal') return `/coordination/goals/${(result.data as Goal).id}`;
    if (result.type === 'project') return `/coordination/projects/${(result.data as Project).id}`;
    if (result.type === 'task') return `/coordination/tasks/${(result.data as Task).id}`;
    return '#';
  };

  const getResultDescription = (result: SearchResult) => {
    if (result.type === 'goal') return (result.data as Goal).description;
    if (result.type === 'project') return (result.data as Project).description;
    if (result.type === 'task') return (result.data as Task).description;
    return '';
  };

  const getResultStatus = (result: SearchResult) => {
    if (result.type === 'goal') return (result.data as Goal).status;
    if (result.type === 'project') return (result.data as Project).status;
    if (result.type === 'task') return (result.data as Task).status;
    return '';
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground border rounded-md hover:bg-muted/50 transition-colors w-64"
      >
        <Search className="w-4 h-4" />
        <span className="flex-1 text-left">搜索目标、工程、任务...</span>
        <kbd className="text-xs bg-muted px-1.5 py-0.5 rounded border">
          ⌘K
        </kbd>
      </button>

      <CommandDialog open={isOpen} onOpenChange={setIsOpen}>
        <div className="flex items-center border-b px-3">
          <Search className="mr-2 h-4 w-4 shrink-0 text-muted-foreground" />
          <input
            type="text"
            placeholder="搜索目标、工程、任务..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="flex-1 py-3 text-sm outline-none bg-transparent placeholder:text-muted-foreground"
          />
          {loading && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
        </div>
        
        <CommandList className="max-h-80 overflow-y-auto">
          {error && (
            <div className="flex items-center gap-2 p-4 text-destructive text-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}
          
          <CommandEmpty>
            {query.trim().length > 0 ? '未找到匹配的结果' : '输入关键词开始搜索'}
          </CommandEmpty>
          
          {results.length > 0 && (
            <>
              <CommandGroup heading="目标">
                {results.filter(r => r.type === 'goal').map(result => (
                  <CommandItem key={`${result.type}-${result.data.id}`} asChild>
                    <Link
                      to={getResultLink(result)}
                      onClick={handleClose}
                      className="flex items-start gap-3 p-3 cursor-pointer"
                    >
                      <div className="mt-0.5">{getTypeIcon(result.type)}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm truncate">{getResultTitle(result)}</span>
                          <Badge variant="secondary" className="text-xs shrink-0">
                            {getTypeLabel(result.type)}
                          </Badge>
                        </div>
                        {getResultDescription(result) && (
                          <div className="text-xs text-muted-foreground truncate mt-1">
                            {getResultDescription(result)}
                          </div>
                        )}
                      </div>
                    </Link>
                  </CommandItem>
                ))}
              </CommandGroup>
              
              <CommandGroup heading="工程">
                {results.filter(r => r.type === 'project').map(result => (
                  <CommandItem key={`${result.type}-${result.data.id}`} asChild>
                    <Link
                      to={getResultLink(result)}
                      onClick={handleClose}
                      className="flex items-start gap-3 p-3 cursor-pointer"
                    >
                      <div className="mt-0.5">{getTypeIcon(result.type)}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm truncate">{getResultTitle(result)}</span>
                          <Badge variant="secondary" className="text-xs shrink-0">
                            {getTypeLabel(result.type)}
                          </Badge>
                        </div>
                        {getResultDescription(result) && (
                          <div className="text-xs text-muted-foreground truncate mt-1">
                            {getResultDescription(result)}
                          </div>
                        )}
                      </div>
                    </Link>
                  </CommandItem>
                ))}
              </CommandGroup>
              
              <CommandGroup heading="任务">
                {results.filter(r => r.type === 'task').map(result => (
                  <CommandItem key={`${result.type}-${result.data.id}`} asChild>
                    <Link
                      to={getResultLink(result)}
                      onClick={handleClose}
                      className="flex items-start gap-3 p-3 cursor-pointer"
                    >
                      <div className="mt-0.5">{getTypeIcon(result.type)}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm truncate">{getResultTitle(result)}</span>
                          <Badge variant="secondary" className="text-xs shrink-0">
                            {getTypeLabel(result.type)}
                          </Badge>
                        </div>
                        {getResultDescription(result) && (
                          <div className="text-xs text-muted-foreground truncate mt-1">
                            {getResultDescription(result)}
                          </div>
                        )}
                      </div>
                    </Link>
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}
        </CommandList>
      </CommandDialog>
    </>
  );
}
