import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  Target,
  Activity,
  ChevronLeft,
  ChevronRight,
  Brain,
  FileText,
  Bot,
  Wrench,
  ChevronDown,
  MessageSquare,
  Settings,
} from 'lucide-react'

interface SidebarProps {
  collapsed: boolean
  onToggleCollapsed: (collapsed: boolean) => void
}

// 两库三中心架构
const navGroups = [
  {
    label: '工作台',
    icon: Target,
    path: '/',
    children: null,
  },
  {
    label: '驾驭中心',
    icon: Activity,
    path: '/coordination/goals',
    children: [
      { label: '目标', path: '/coordination/goals' },
      { label: '工程', path: '/coordination/projects' },
      { label: '任务', path: '/coordination/tasks' },
      { label: '方案对比', path: '/solutions' },
    ],
  },
  {
    label: '裁决中心',
    icon: MessageSquare,
    path: '/rulings',
    children: null,
  },
  {
    label: '认知中心',
    icon: Brain,
    path: '/cognitive/center',
    children: [
      { label: '认知库', path: '/cognitive/knowledge' },
      { label: '评估', path: '/cognitive/assessment' },
      { label: '数据导入', path: '/cognitive/inject' },
    ],
  },
  {
    label: '场景库',
    icon: FileText,
    path: '/scenarios/center',
    children: [
      { label: '场景列表', path: '/scenarios' },
      { label: '收藏', path: '/scenarios/starred' },
    ],
  },
  {
    label: '能力库',
    icon: Wrench,
    path: '/system/capabilities',
    children: [
      { label: '智能体能力', path: '/system/capabilities' },
      { label: '能力标签库', path: '/industry/tags' },
      { label: '行业包', path: '/industry/packs' },
    ],
  },
  {
    label: '智能体',
    icon: Bot,
    path: '/system/agents',
    children: null,
  },
  {
    label: '系统设置',
    icon: Settings,
    path: '/system/settings',
    children: null,
  },
]

export default function Sidebar({ collapsed, onToggleCollapsed }: SidebarProps) {
  const location = useLocation()
  
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => {
    // Auto-expand the group that matches current route
    const defaults = new Set<string>()
    for (const group of navGroups) {
      if (group.children && group.children.length > 0) {
        const isActive = group.path === '/'
          ? location.pathname === '/'
          : location.pathname.startsWith(group.path)
        if (isActive) defaults.add(group.label)
      }
    }
    return defaults
  })

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  const toggleGroup = (label: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev)
      if (next.has(label)) next.delete(label)
      else next.add(label)
      return next
    })
  }

  return (
    <>
      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 h-full z-50
          bg-white border-r border-slate-200
          transition-all duration-300 ease-in-out
          flex flex-col
          ${collapsed ? 'w-[68px]' : 'w-[220px]'}
        `}
      >
        {/* Logo / Brand */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-100 flex-shrink-0">
          <div className="flex items-center space-x-2 overflow-hidden">
            <div className="w-8 h-8 bg-slate-900 rounded-sm flex items-center justify-center flex-shrink-0">
              <Target className="text-white w-5 h-5" />
            </div>
            {!collapsed && (
              <span className="text-lg font-bold tracking-tight text-slate-900 italic whitespace-nowrap">
                Grever<span className="text-blue-600 font-normal">OS</span>
              </span>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 overflow-y-auto">
          <ul className="space-y-1 px-2">
            {navGroups.map((group) => {
              const Icon = group.icon
              const groupActive = isActive(group.path)
              const hasChildren = group.children && group.children.length > 0
              const isExpanded = expandedGroups.has(group.label)

              return (
                <li key={group.label}>
                  {/* Group header */}
                  <button
                    onClick={() => {
                      if (hasChildren) {
                        toggleGroup(group.label)
                      } else {
                        window.location.hash = ''
                        ;(document.querySelector(`a[href="${group.path}"]`) as HTMLElement)?.click()
                      }
                    }}
                    className={`
                      w-full flex items-center gap-3 px-3 py-2.5 rounded-md
                      transition-colors duration-150
                      ${groupActive
                        ? 'bg-blue-50 text-blue-600 font-semibold'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                      }
                      ${collapsed ? 'justify-center' : ''}
                    `}
                    title={collapsed ? group.label : undefined}
                  >
                    <Icon size={18} className="flex-shrink-0" />
                    {!collapsed && (
                      <>
                        <Link
                          to={group.path}
                          className="flex-1 text-left text-sm whitespace-nowrap"
                          onClick={(e) => {
                            if (hasChildren) e.stopPropagation()
                          }}
                        >
                          {group.label}
                        </Link>
                        {hasChildren && (
                          <ChevronDown
                            size={14}
                            className={`transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                          />
                        )}
                      </>
                    )}
                  </button>

                  {/* Children */}
                  {hasChildren && !collapsed && isExpanded && (
                    <ul className="ml-8 mt-1 space-y-0.5">
                      {group.children.map((child) => {
                        const childActive = isActive(child.path)
                        return (
                          <li key={child.path}>
                            <Link
                              to={child.path}
                              className={`
                                block px-3 py-1.5 rounded-md text-xs
                                transition-colors duration-150
                                ${childActive
                                  ? 'bg-blue-50 text-blue-600 font-medium'
                                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'
                                }
                              `}
                            >
                              {child.label}
                            </Link>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Collapse toggle */}
        <div className="hidden md:flex border-t border-slate-100 p-2 flex-shrink-0">
          <button
            onClick={() => onToggleCollapsed(!collapsed)}
            className="w-full flex items-center justify-center py-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-sm transition-colors"
            title={collapsed ? '展开侧边栏' : '收起侧边栏'}
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>
      </aside>
    </>
  )
}
