/**
 * EventStream Service - SSE 实时事件客户端
 * 连接后端 /api/v1/events/stream，接收工作流/步骤状态变更事件
 */

import { useState, useEffect, useRef } from 'react'

// ==================== 事件类型 ====================

export type ReinsEventType =
  | 'step_started'
  | 'step_completed'
  | 'step_failed'
  | 'step_blocked'
  | 'workflow_started'
  | 'workflow_completed'
  | 'workflow_failed'
  | 'workflow_paused'
  | 'workflow_resumed'
  | 'workflow_cancelled'
  | 'conflict_detected'
  | 'step_added'
  | 'steps_blocked'
  | 'connected'

export interface ReinsEvent {
  event_type: ReinsEventType
  workflow_id: string
  timestamp: string
  step_id: string
  data: Record<string, any>
  event_id: string
}

// ==================== 事件总线 Hook ====================

type EventHandler = (event: ReinsEvent) => void

interface Subscription {
  handler: EventHandler
  eventTypes?: ReinsEventType[]
}

class EventStreamService {
  private eventSource: EventSource | null = null
  private subscriptions: Subscription[] = []
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private baseReconnectDelay = 1000
  private workflowId: string | null = null
  private isConnecting = false

  /**
   * 连接到 SSE 事件流
   * @param workflowId 可选，监听特定工作流事件；不传则监听所有事件
   */
  connect(workflowId?: string): void {
    if (this.eventSource || this.isConnecting) {
      return
    }

    this.workflowId = workflowId || null
    this.isConnecting = true
    this._createConnection()
  }

  private _createConnection(): void {
    const url = this.workflowId
      ? `/api/v1/events/stream?workflow_id=${encodeURIComponent(this.workflowId)}`
      : '/api/v1/events/stream'

    try {
      this.eventSource = new EventSource(url)
    } catch (e) {
      console.error('[EventStream] Failed to create EventSource:', e)
      this._scheduleReconnect()
      return
    }

    this.eventSource.onopen = () => {
      console.log('[EventStream] Connected to', url)
      this.isConnecting = false
      this.reconnectAttempts = 0
    }

    this.eventSource.onerror = (err) => {
      console.error('[EventStream] SSE error:', err)
      this.isConnecting = false
      this._cleanup()
      this._scheduleReconnect()
    }

    // 监听所有已知事件类型
    const eventTypes: ReinsEventType[] = [
      'step_started',
      'step_completed',
      'step_failed',
      'step_blocked',
      'workflow_started',
      'workflow_completed',
      'workflow_failed',
      'workflow_paused',
      'workflow_resumed',
      'workflow_cancelled',
      'conflict_detected',
      'step_added',
      'steps_blocked',
      'connected',
    ]

    for (const eventType of eventTypes) {
      this.eventSource.addEventListener(eventType, (e: MessageEvent) => {
        try {
          const event: ReinsEvent = JSON.parse(e.data)
          this._dispatch(event)
        } catch (err) {
          console.error('[EventStream] Failed to parse event:', err)
        }
      })
    }
  }

  private _dispatch(event: ReinsEvent): void {
    for (const sub of this.subscriptions) {
      if (!sub.eventTypes || sub.eventTypes.length === 0) {
        // 全局订阅
        sub.handler(event)
      } else if (sub.eventTypes.includes(event.event_type)) {
        // 类型过滤订阅
        sub.handler(event)
      }
    }
  }

  private _scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[EventStream] Max reconnect attempts reached, giving up')
      return
    }

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
    }

    const delay = this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts)
    this.reconnectAttempts++

    console.log(`[EventStream] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    this.reconnectTimeout = setTimeout(() => {
      this.isConnecting = false
      this._createConnection()
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
  }

  /**
   * 订阅事件
   * @param handler 事件处理函数
   * @param eventTypes 可选，只监听这些事件类型；空数组或空表示全部
   * @returns 取消订阅函数
   */
  subscribe(handler: EventHandler, eventTypes?: ReinsEventType[]): () => void {
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
    this.reconnectAttempts = this.maxReconnectAttempts // 阻止自动重连
    this.subscriptions = []
  }

  /**
   * 切换监听的 workflow_id
   */
  watchWorkflow(workflowId: string): void {
    const wasConnected = this.eventSource !== null
    this._cleanup()
    this.workflowId = workflowId
    if (wasConnected) {
      this.reconnectAttempts = 0
      this._createConnection()
    }
  }

  get isConnected(): boolean {
    return this.eventSource !== null && this.isConnecting === false
  }
}

// 单例
export const eventStream = new EventStreamService()

// ==================== React Hook ====================

/**
 * useEventStream - React Hook 用于在组件中订阅 SSE 事件
 *
 * 用法:
 *   const { events, isConnected } = useEventStream(['step_started', 'step_completed'])
 */
export function useEventStream(
  eventTypes?: ReinsEventType[],
  workflowId?: string,
): {
  events: ReinsEvent[]
  isConnected: boolean
  latestEvent: ReinsEvent | null
} {
  const [events, setEvents] = useState<ReinsEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const eventsRef = useRef<ReinsEvent[]>([])

  useEffect(() => {
    // 连接
    if (workflowId) {
      eventStream.connect(workflowId)
    } else {
      eventStream.connect()
    }

    const unsubscribe = eventStream.subscribe((event) => {
      if (event.event_type === 'connected') {
        setIsConnected(true)
        return
      }

      eventsRef.current = [...eventsRef.current.slice(-99), event]
      setEvents([...eventsRef.current])
    }, eventTypes)

    setIsConnected(eventStream.isConnected)

    return () => {
      unsubscribe()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowId])

  return {
    events,
    isConnected,
    latestEvent: events.length > 0 ? events[events.length - 1] : null,
  }
}
