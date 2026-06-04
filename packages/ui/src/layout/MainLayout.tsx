import Sidebar from '../shared/components/Sidebar'
import NotificationBell from '../shared/components/NotificationBell'
import { useLocation, Outlet } from 'react-router-dom'
import { Search } from 'lucide-react'
import { useState } from 'react'
import { Toaster } from "@/shared/components/ui/sonner"

const routeTitles: Record<string, string> = {
  '/': '工作台',
  '/coordination/goals': '驾驭中心 / 目标管理',
  '/coordination/goals/new': '驾驭中心 / 新建目标',
  '/coordination/projects': '驾驭中心 / 工程管理',
  '/coordination/tasks': '驾驭中心 / 任务',
  '/coordination/executions': '驾驭中心 / 执行',
  '/coordination/disputes': '驾驭中心 / 争议管理',
  '/rulings': '裁决中心',
  '/scenarios': '场景库 / 场景列表',
  '/scenarios/starred': '场景库 / 收藏',
  '/scenarios/:id': '场景库 / 场景详情',
  '/scenarios/center': '场景库',
  '/system/agents': '智能体',
  '/system/capabilities': '能力库',
  '/system/settings': '系统设置',
  '/cognitive/center': '认知中心',
  '/cognitive/knowledge': '认知中心 / 认知库',
  '/cognitive/assessment': '认知中心 / 评估',
  '/cognitive/inject': '认知中心 / 数据导入',
  '/solutions': '驾驭中心 / 方案对比',
  '/industry/tags': '能力库 / 能力标签',
  '/industry/packs': '能力库 / 行业包',
}

export default function MainLayout() {
  const location = useLocation()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const title = routeTitles[location.pathname] || 'NexusOS'

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar collapsed={sidebarCollapsed} onToggleCollapsed={setSidebarCollapsed} />

      {/* Main content area with margin-left for sidebar */}
      <div className={`transition-all duration-300 ${sidebarCollapsed ? 'ml-[68px]' : 'ml-[220px]'}`}>
        {/* Top bar */}
        <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-40 flex items-center justify-between px-6">
          <div>
            <h1 className="text-lg font-bold text-slate-900">{title}</h1>
          </div>
          <div className="flex items-center space-x-4">
            <div className="relative group">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
              <input
                className="bg-slate-100 border-none rounded-full py-2 pl-10 pr-4 text-sm w-64 focus:ring-2 focus:ring-blue-500/20 transition-all outline-none"
                placeholder="搜索目标、任务..."
                type="text"
              />
            </div>
            <NotificationBell placement="header" />
            <div className="flex items-center space-x-3 border-l border-slate-200 pl-4 text-sm">
              <div className="flex flex-col items-end">
                <span className="font-semibold text-slate-900">管理员</span>
                <span className="text-xs text-slate-500">
                  {new Date().toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <div className="w-9 h-9 rounded-full bg-slate-200 border-2 border-white shadow-sm flex items-center justify-center text-slate-600 font-bold">
                管
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
      <Toaster />
    </div>
  )
}
