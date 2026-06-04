/**
 * SSE Client Service - P5-02/P5-07
 * Agent 专用 SSE 实时事件客户端
 *
 * 支持：
 * - SSE 实时推送（trigger_mode=sse）
 * - 自动重连（心跳检测）
 * - 降级到轮询（trigger_mode=polling）
 * - 增量事件拉取（Polling 模式）
 */


// ==================== 事件类型（P5-02） ====================

export type AgentEventType =
  | 'task_assigned'
  | 'task_created'
  | 'task_updated'
  | 'task_completed'
  | 'task_blocked'
  | 'task_unblocked'
  | 'dispute_raised'
  | 'dispute_resolved'
  | 'agent_status_changed'
  | 'mode_switched'
  | 'goal_updated'
  | 'workflow_started'
  | 'workflow_completed'
  | 'workflow_failed'
  | 'workflow_paused'
  | 'workflow_resumed'
  | 'step_started'
  | 'step_completed'
  | 'step_failed'
  | 'step_blocked'
  | 'connected'   // SSE 连接成功
  | 'ping'        // 心跳 comment

export interface AgentEvent {
  event_id: string
  event_type: string
  agent_id?: string
  timestamp: string
  payload: {
    task_id?: string
    task_title?: string
    goal_id?: string
    from_status?: string
    to_status?: string
    dispute_id?: string
    blocked_reason?: string
    workflow_id?: string
    step_id?: string
    extra?: Record<string, any>
  }
}

// ==================== Polling 响应 ====================

export interface PollResponse {
  events: AgentEvent[]
  has_more: boolean
  last_event_id: string | null
  degraded: boolean
  mode_switched: boolean
  trigger_mode: 'sse' | 'polling'
  count: number
}

// ==================== SSE Client ====================

export type EventHandler = (event: AgentEvent) => void

interface Subscription {
  handler: EventHandler
  eventTypes?: string[]
}

export class SseClient {
  private agentId: string
  private eventSource: EventSource | null = null
  private subscriptions: Subscription[] = []
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  private heartbeatTimeout: ReturnType<typeof setTimeout> | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private baseReconnectDelay = 1000
  private isConnecting = false
  private _isConnected = false

  // Polling 模式
  private pollInterval: ReturnType<typeof setInterval> | null = null
  private pollIntervalSeconds = 10
  private lastEventId: string | null = null
  private triggerMode: 'sse' | 'polling' = 'sse'
  private isPolling = false

  constructor(agentId: string) {
    this.agentId = agentId
  }

  // ---- SSE 连接 ----

  connect(): void {
    if (this.triggerMode === 'polling') {
      this.startPolling()
      return
    }

    if (this.eventSource || this.isConnecting) {
      return
    }

    this.isConnecting = true
    this._createSseConnection()
  }

  private _createSseConnection(): void {
    const url = `/api/v1/events/stream?agent_id=${encodeURIComponent(this.agentId)}`

    try {
      this.eventSource = new EventSource(url)
    } catch (e) {
      console.error('[SseClient] Failed to create EventSource:', e)
      this._scheduleReconnect()
      return
    }

    this.eventSource.onopen = () => {
      console.log('[SseClient] SSE connected:', url)
      this.isConnecting = false
      this._isConnected = true
      this.reconnectAttempts = 0
      this._resetHeartbeatTimer()
    }

    this.eventSource.onerror = (err) => {
      console.error('[SseClient] SSE error:', err)
      this.isConnecting = false
      this._isConnected = false
      this._clearHeartbeatTimer()
      this._cleanup()
      // 检测是否应该降级到 polling
      this._handleDisconnect()
    }

    this.eventSource.onmessage = (e) => {
      // 收到 comment (心跳 ": ping\n\n")
      if (!e.data || e.data.trim() === '') {
        return
      }
      this._resetHeartbeatTimer()
    }

    // 监听所有事件类型
    const eventTypes: AgentEventType[] = [
      'task_assigned',
      'task_created',
      'task_updated',
      'task_completed',
      'task_blocked',
      'task_unblocked',
      'dispute_raised',
      'dispute_resolved',
      'agent_status_changed',
      'mode_switched',
      'goal_updated',
      'workflow_started',
      'workflow_completed',
      'workflow_failed',
      'workflow_paused',
      'workflow_resumed',
      'step_started',
      'step_completed',
      'step_failed',
      'step_blocked',
      'connected',
    ]

    for (const eventType of eventTypes) {
      if (this.eventSource) {
        this.eventSource.addEventListener(eventType, (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data)
            const event: AgentEvent = {
              event_id: data.event_id || e.lastEventId || '',
              event_type: data.event_type || eventType,
              agent_id: data.agent_id,
              timestamp: data.timestamp || data.created_at || new Date().toISOString(),
              payload: data.payload || data,
            }
            this._dispatch(event)

            // 收到 connected 事件
            if (eventType === 'connected') {
              this._isConnected = true
              this.reconnectAttempts = 0
            }

            // 检查 mode_switched 事件
            if (eventType === 'mode_switched' && data.payload) {
              const newMode = data.payload.to_status || data.payload.extra?.trigger_mode
              if (newMode === 'polling') {
                console.log('[SseClient] Received mode_switched to polling, degrading...')
                this._degradeToPolling()
              }
            }
          } catch (err) {
            console.error('[SseClient] Failed to parse event:', err)
          }
        })
      }
    }
  }

  // ---- 心跳检测 ----

  private _resetHeartbeatTimer(): void {
    this._clearHeartbeatTimer()
    // 20 秒无任何消息（包括心跳 comment）视为断连
    this.heartbeatTimeout = setTimeout(() => {
      console.warn('[SseClient] Heartbeat timeout, reconnecting...')
      this._handleDisconnect()
    }, 20000)
  }

  private _clearHeartbeatTimer(): void {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout)
      this.heartbeatTimeout = null
    }
  }

  private _handleDisconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this._scheduleReconnect()
    } else {
      // 达到最大重试次数，降级到轮询
      console.warn('[SseClient] Max reconnect attempts, degrading to polling...')
      this._degradeToPolling()
    }
  }

  private _degradeToPolling(): void {
    this._cleanup()
    this.triggerMode = 'polling'
    this.isPolling = true
    this.startPolling()
    // 通知订阅者模式已切换
    this._dispatch({
      event_id: `mode-switch-${Date.now()}`,
      event_type: 'mode_switched',
      agent_id: this.agentId,
      timestamp: new Date().toISOString(),
      payload: {
        from_status: 'sse',
        to_status: 'polling',
        extra: { degraded: true },
      },
    })
  }

  // ---- 轮询模式 ----

  startPolling(): void {
    if (this.pollInterval) {
      return
    }

    console.log('[SseClient] Starting polling mode')
    this.isPolling = true
    this._isConnected = true // polling 模式视为"连接"

    this._poll().catch(console.error)

    // 定期轮询
    this.pollInterval = setInterval(() => {
      this._poll().catch(console.error)
    }, this.pollIntervalSeconds * 1000)
  }

  stopPolling(): void {
    if (this.pollInterval) {
      clearInterval(this.pollInterval)
      this.pollInterval = null
    }
    this.isPolling = false
  }

  setPollInterval(seconds: number): void {
    this.pollIntervalSeconds = seconds
    if (this.isPolling && this.pollInterval) {
      // 重启轮询
      this.stopPolling()
      this.startPolling()
    }
  }

  private async _poll(): Promise<void> {
    try {
      const params = new URLSearchParams({ agent_id: this.agentId, limit: '50' })
      if (this.lastEventId) {
        // 需要将 lastEventId 转换为 since 时间戳
        // 这里简化为直接传 lastEventId，后端自行处理
        params.set('since', this.lastEventId)
      }

      const response = await fetch(`/api/v1/events/pull?${params.toString()}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      })

      if (!response.ok) {
        console.error('[SseClient] Poll failed:', response.status)
        return
      }

      const data: PollResponse = await response.json()

      // 处理降级通知
      if (data.degraded || data.mode_switched) {
        console.log('[SseClient] Server indicated degraded mode')
      }

      // 派发事件
      for (const evt of data.events) {
        this._dispatch(evt)
        this.lastEventId = evt.event_id
      }
    } catch (err) {
      console.error('[SseClient] Poll error:', err)
    }
  }

  // ---- 自动重连 ----

  private _scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[SseClient] Max reconnect attempts reached, degrading to polling')
      this._degradeToPolling()
      return
    }

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
    }

    const delay = this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts)
    this.reconnectAttempts++

    console.log(`[SseClient] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    this.reconnectTimeout = setTimeout(() => {
      this.isConnecting = false
      if (this.triggerMode === 'sse') {
        this._createSseConnection()
      } else {
        this._degradeToPolling()
      }
    }, delay)
  }

  private _cleanup(): void {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
    this._isConnected = false
  }

  // ---- 事件分发 ----

  private _dispatch(event: AgentEvent): void {
    for (const sub of this.subscriptions) {
      if (!sub.eventTypes || sub.eventTypes.length === 0) {
        sub.handler(event)
      } else if (sub.eventTypes.includes(event.event_type)) {
        sub.handler(event)
      }
    }
  }

  // ---- 公开 API ----

  /**
   * 订阅事件
   * @param handler 事件处理函数
   * @param eventTypes 可选，只监听这些事件类型；空或 undefined 表示全部
   * @returns 取消订阅函数
   */
  subscribe(handler: EventHandler, eventTypes?: string[]): () => void {
    const sub: Subscription = { handler, eventTypes: eventTypes || [] }
    this.subscriptions.push(sub)

    return () => {
      const idx = this.subscriptions.indexOf(sub)
      if (idx >= 0) {
        this.subscriptions.splice(idx, 1)
      }
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this._cleanup()
    this.stopPolling()
    this.reconnectAttempts = this.maxReconnectAttempts
    this.subscriptions = []
  }

  get isConnected(): boolean {
    return this._isConnected
  }

  get currentMode(): 'sse' | 'polling' {
    return this.triggerMode
  }
}

// ==================== 客户端工厂 ====================

const _clients = new Map<string, SseClient>()

export function getSseClient(agentId: string): SseClient {
  if (!_clients.has(agentId)) {
    _clients.set(agentId, new SseClient(agentId))
  }
  return _clients.get(agentId)!
}

export function removeSseClient(agentId: string): void {
  const client = _clients.get(agentId)
  if (client) {
    client.disconnect()
    _clients.delete(agentId)
  }
}
