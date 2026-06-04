/**
 * Nexus 全局配置
 * 所有后端地址、端口统一在此定义
 * 环境变量来源：packages/ui/.env
 * 修改后需要重启 Vite dev server
 */

// 后端 API 地址（开发环境走 Vite 代理，生产环境用完整 URL）
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// Nexus Gateway 地址（智能体注册/连接用）
export const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8093'

// 开发环境判断
export const isDev = import.meta.env.DEV

// 方便一次性打印所有配置（调试用）
export function dumpConfig() {
  return {
    API_BASE_URL,
    GATEWAY_URL,
    isDev,
  }
}
