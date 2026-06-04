/**
 * Nexus API 服务层 - 安全中心 API
 * 调用真实后端 API
 * 
 * ⚠️ 所有路径从 api/paths.ts 导入
 */

import { request } from './api'
import { SECURITY, DASHBOARD } from '../api/paths'

// ==================== 类型定义 ====================

export interface Alert {
  id: string
  level: 'critical' | 'warning' | 'info'
  message: string
  timestamp: string
  status: 'active' | 'resolved'
  details?: string
}

export interface AuditLog {
  id: string
  timestamp: string
  user: string
  action: string
  result: string
  details?: string
  ip_address?: string
}

export interface SystemMetrics {
  cpu_usage: number
  memory_usage: number
  sse_connections: number
  average_latency_ms: number
  active_workflows: number
  pending_tasks: number
}

export interface ExecutionTrendItem {
  date: string
  count: number
}

// ==================== 安全中心 API ====================

export const securityApi = {
  getAlerts: (params?: { level?: 'critical' | 'warning' | 'info'; status?: 'active' | 'resolved'; page?: number; page_size?: number }) => {
    return request<{ total: number; items: Alert[] }>(SECURITY.SECURITY_ALERTS, { params: params || {} })
  },
  getAlert: (id: string) => {
    return request<Alert>(SECURITY.GET_ALERT(id))
  },
  createAlert: (data: Partial<Alert>) => {
    return request<Alert>(SECURITY.CREATE_ALERT, { method: 'POST', body: JSON.stringify(data) })
  },
  updateAlertStatus: (id: string, status: 'active' | 'resolved' | 'closed') => {
    return request<Alert>(SECURITY.UPDATE_ALERT(id), { method: 'PATCH', body: JSON.stringify({ status }) })
  },
  deleteAlert: (id: string) => {
    return request(SECURITY.REMOVE_ALERT(id), { method: 'DELETE' })
  },
  getAuditLogs: (params?: { resource_type?: string; resource_id?: string; operation?: string; operator?: string; start_time?: string; end_time?: string; page?: number; page_size?: number }) => {
    return request<{ total: number; items: AuditLog[] }>(SECURITY.SECURITY_AUDIT_LOGS, { params: params || {} })
  },
  getSystemMetrics: (): Promise<SystemMetrics | null> => {
    return Promise.resolve<SystemMetrics | null>(null)
  },
  resolveAlert: (id: string) => {
    return request<{ success: boolean }>(`${SECURITY.SECURITY_ALERTS}/${id}/resolve`, { method: 'PATCH', body: JSON.stringify({ status: 'resolved' }) })
  },
  getActiveAlertCount: (): Promise<number> => {
    return securityApi.getAlerts({ status: 'active' }).then(data => data.total).catch(() => 0)
  },
  getExecutionTrend: (days: number = 7): Promise<ExecutionTrendItem[]> => {
    return request<ExecutionTrendItem[]>(`${DASHBOARD.STATS}/execution-trend?days=${days}`)
  },
}
