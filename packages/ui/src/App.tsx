import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ErrorBoundary } from './shared/components/ErrorBoundary'
import MainLayout from './layout/MainLayout'

// shared
import Dashboard from './pages/system/Dashboard'
import Settings from './pages/system/Settings'
import VisualBoard from './pages/system/VisualBoard'
import WorkflowDiagram from './pages/reins/WorkflowDiagram'

// reins - 驾驭域
import GoalList from './pages/reins/goal/GoalList'
import GoalDetail from './pages/reins/goal/GoalDetail'
import CreateGoal from './pages/reins/goal/CreateGoal'
import GoalDecomposePage from './pages/reins/goal/GoalDecomposePage'
import DecomposePreview from './pages/reins/DecomposePreview'
import ProjectList from './pages/reins/project/ProjectList'
import ProjectDetail from './pages/reins/project/ProjectDetail'
import ProjectDiagram from './pages/reins/project/ProjectDiagram'
import ProjectTreePage from './pages/reins/project/ProjectTreePage'
import TaskList from './pages/reins/task/TaskList'
import TaskDetail from './pages/reins/task/TaskDetail'
import CreateTask from './pages/reins/task/CreateTask'
import EnhancedTaskDetail from './pages/reins/task/EnhancedTaskDetail'
import ExecutionMonitoring from './pages/reins/execution/ExecutionMonitoring'
import ExecutionDetail from './pages/reins/execution/ExecutionDetail'
import ExecutionReportModal from './pages/reins/execution/ExecutionReportModal'
import AgentList from './pages/reins/agent/AgentList'
import GoalTreeView from './pages/reins/goal/GoalTreeView'
import TraceViewer from './pages/reins/TraceViewer'

// grasp - 认知域
import CognitiveCenter from './pages/grasp/CognitiveCenter'
import CognitiveKnowledge from './pages/grasp/CognitiveKnowledge'
import CognitiveAssessment from './pages/grasp/CognitiveAssessment'
import CognitiveInject from './pages/grasp/CognitiveInject'

// reach - 拓展域
import ScenarioList from './pages/reach/scenario/ScenarioList'
import ScenarioDetail from './pages/reach/scenario/ScenarioDetail'
import ScenarioFavorites from './pages/reach/scenario/ScenarioFavorites'
import ScenarioCenter from './pages/reach/scenario/ScenarioCenter'
import ScenarioCreate from './pages/reach/scenario/ScenarioCreate'
import IndustryTagsPage from './pages/reach/IndustryTagsPage'
import IndustryPacksPage from './pages/reach/IndustryPacksPage'
import HumanInputDashboard from './pages/reins/human-input/HumanInputDashboard'
import { HumanInputAnalytics } from './pages/reins/human-input/HumanInputAnalytics'
import HumanInputPage from './pages/reins/human-input/HumanInputPage'
import CapabilitiesPage from './pages/reach/CapabilitiesPage'
import ArtifactList from './pages/reach/ArtifactList'
import SkillsPage from './pages/reach/SkillsPage'

// evo - 进化域
import SolutionList from './pages/evo/SolutionList'
import SolutionCenter from './pages/evo/SolutionCenter'

// vigil - 安全域
import SecurityCenter from './pages/vigil/SecurityCenter'
import RulingsPage from './pages/vigil/RulingsPage'

// shared components
import HumanInputStatsWidget from './shared/components/HumanInputStatsWidget'

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Routes>
        {/* Main layout with sidebar */}
        <Route element={<MainLayout />}>
          {/* 工作台 */}
          <Route path="/" element={<Dashboard />} />

          {/* 协同中心 */}
          <Route path="/coordination/goals" element={<GoalList />} />
          <Route path="/coordination/goals/new" element={<CreateGoal />} />
          <Route path="/coordination/goals/:id" element={<GoalDetail />} />
          <Route path="/goals/:id/solutions" element={<SolutionList />} />
          <Route path="/solutions" element={<SolutionCenter />} />
          <Route path="/goals/:id/decompose-preview" element={<DecomposePreview />} />
          <Route path="/coordination/projects" element={<ProjectList />} />
          <Route path="/coordination/projects/:id" element={<ProjectDetail />} />
          <Route path="/coordination/projects/:id/diagram" element={<ProjectDiagram />} />
          <Route path="/coordination/projects/:id/tree" element={<ProjectTreePage />} />
          <Route path="/coordination/tasks" element={<TaskList />} />
          <Route path="/coordination/tasks/:id" element={<TaskDetail />} />
          <Route path="/coordination/tasks/create" element={<CreateTask />} />
          <Route path="/coordination/tasks/enhanced/:id" element={<EnhancedTaskDetail />} />
          <Route path="/coordination/executions" element={<ExecutionMonitoring />} />
          <Route path="/coordination/executions/:taskId" element={<ExecutionDetail />} />

          {/* 认知中心 */}
          <Route path="/cognitive/center" element={<CognitiveCenter />} />
          <Route path="/cognitive/knowledge" element={<CognitiveKnowledge />} />
          <Route path="/cognitive/assessment" element={<CognitiveAssessment />} />
          <Route path="/cognitive/inject" element={<CognitiveInject />} />

          {/* 场景库 */}
          <Route path="/scenarios/center" element={<ScenarioCenter />} />
          <Route path="/scenarios" element={<ScenarioList />} />
          <Route path="/scenarios/starred" element={<ScenarioFavorites />} />
          <Route path="/scenarios/:id" element={<ScenarioDetail />} />
          <Route path="/scenarios/new" element={<ScenarioCreate />} />

          {/* 安全中心 */}
          <Route path="/security" element={<SecurityCenter />} />
          <Route path="/human-input" element={<HumanInputDashboard />} />
          <Route path="/human-input/pending" element={<HumanInputPage />} />
          <Route path="/human-input/analytics" element={<HumanInputAnalytics />} />
          {/* 系统管理 */}
          <Route path="/system/agents" element={<AgentList />} />
          <Route path="/system/capabilities" element={<CapabilitiesPage />} />
          <Route path="/industry/tags" element={<IndustryTagsPage />} />
          <Route path="/industry/packs" element={<IndustryPacksPage />} />
          <Route path="/system/artifacts" element={<ArtifactList />} />

          {/* 可视化 */}
          <Route path="/visual/dashboard" element={<VisualBoard />} />
          <Route path="/visual/traces" element={<TraceViewer />} />
          <Route path="/goals/:id/tree" element={<GoalDecomposePage />} />
          <Route path="/rulings" element={<RulingsPage />} />

          {/* 系统设置 */}
          <Route path="/system/settings" element={<Settings />} />

        </Route>

        {/* Full-screen pages (no sidebar/header) */}
        <Route path="/workflows/:id/diagram" element={<WorkflowDiagram />} />
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  )
}
