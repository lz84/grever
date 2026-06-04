import React, { Component, type ReactNode } from 'react'
import { Button } from '@/shared/components/ui/button'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
          <div className="max-w-md w-full p-8 bg-white rounded-lg border border-red-200 shadow-sm">
            <div className="text-center">
              <div className="text-4xl mb-4">⚠️</div>
              <h2 className="text-xl font-bold text-red-700 mb-2">页面渲染出错</h2>
              <p className="text-sm text-slate-500 mb-4 font-mono">
                {this.state.error?.message || '未知错误'}
              </p>
              <div className="flex gap-3 justify-center">
                <Button variant="outline" onClick={() => window.location.href = '/'}>
                  返回首页
                </Button>
                <Button onClick={this.handleReset}>
                  重试
                </Button>
              </div>
              <details className="mt-4 text-left">
                <summary className="text-xs text-slate-400 cursor-pointer">技术详情</summary>
                <pre className="mt-2 p-2 bg-slate-100 rounded text-xs text-red-600 overflow-auto max-h-40">
                  {this.state.error?.stack}
                </pre>
              </details>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
