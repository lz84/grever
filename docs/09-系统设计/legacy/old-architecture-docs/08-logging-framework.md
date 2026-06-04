# Nexus 统一日志框架设计

**版本**: v1.0  
**日期**: 2026-04-03  
**任务**: [P0] 通用组件-日志框架设计  
**执行人**: 麻子  
**状态**: 设计完成

---

## 一、概述

### 1.1 设计目标

Nexus 统一日志框架为五兄弟（悟·御·化·达·鉴）提供全链路日志能力，确保：

- **跨层追踪**：traceId 贯穿 Grasp→Reins→Evo→Reach→Vigil 全链路
- **统一格式**：所有 Agent 输出格式一致，便于解析和检索
- **灵活输出**：支持 console/file 双重输出，生产环境可扩展
- **安全合规**：Vigil 层日志需脱敏，敏感信息自动过滤

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **结构化优先** | 输出 JSON 格式，便于机器解析 |
| **traceId 必传** | 任何跨 Agent 操作必须携带 traceId |
| **日志分级** | debug/info/warn/error 四级，按场景启用 |
| **敏感脱敏** | 密钥、token、个人信息自动替换 |
| **低侵入** | 框架应被引用而非被继承，不影响业务逻辑 |

---

## 二、日志格式规范

### 2.1 统一日志格式（JSON）

```json
{
  "ts": "2026-04-03T09:37:31.639Z",
  "level": "info",
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "spanId": "1a2b3c4d",
  "layer": "reins",
  "agentId": "876b9322-0fbe-4cd0-97c2-9244a4e3b905",
  "agentName": "谷子",
  "taskId": "cbe80ee6-1b0d-420b-9425-dbc4c3517084",
  "message": "任务执行完成",
  "data": {},
  "duration": 1234,
  "error": null
}
```

### 2.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ts` | ISO8601 | ✅ | 时间戳，UTC |
| `level` | string | ✅ | debug/info/warn/error |
| `traceId` | string | ✅ | 全链路追踪 ID |
| `spanId` | string | ✅ | 当前 span ID |
| `parentSpanId` | string | ❌ | 父 span ID，用于构建链路树 |
| `layer` | string | ✅ | 所属层级：grasp/reins/evo/reach/vigil |
| `agentId` | string | ✅ | Agent 唯一标识 |
| `agentName` | string | ✅ | Agent 显示名 |
| `taskId` | string | ❌ | 关联任务 ID |
| `message` | string | ✅ | 日志消息 |
| `data` | object | ❌ | 扩展数据 |
| `duration` | number | ❌ | 操作耗时（毫秒） |
| `error` | object | ❌ | 错误详情 |

### 2.3 traceId 生成规则

```
traceId = {uuid-v4}
spanId = {8位随机hex}
```

- **traceId**：在入口生成，贯穿整个请求生命周期
- **spanId**：每个操作单元生成一个新的 span，span 嵌套形成链路树
- **parentSpanId**：记录父 span，支持链路回溯

---

## 三、traceId 链路设计

### 3.1 链路传播模型

```
用户发起请求
    ↓
[Reins] 生成 traceId，记录 span-1（任务拆解）
    ↓ fork
    ├→ [Grasp] span-2（认知查询）
    │       ↓
    │   [Grasp] span-2.1（实体识别）
    │
    ├→ [Evo] span-3（经验匹配）
    │       ↓
    │   [Evo] span-3.1（胶囊提取）
    │
    └→ [Vigil] span-4（权限检查）
            ↓
        [Vigil] span-4.1（行为审计）
```

### 3.2 traceId 注入点

| 入口 | 注入位置 | 说明 |
|------|----------|------|
| HTTP 请求 | 请求头 `X-Trace-Id` | 外部调用必须传递 traceId |
| Agent 启动 | 内部生成 | 无外部 traceId 时自动生成 |
| 任务创建 | Reins | 任务创建时生成根 traceId |
| 子任务分发 | 各 Agent | 从父任务继承 traceId |

### 3.3 链路上下文传递

```typescript
interface LogContext {
  traceId: string;
  spanId: string;
  parentSpanId?: string;
  layer: Layer;
  agentId: string;
  taskId?: string;
}

// 上下文在 Agent 间传递时通过消息协议携带
interface AgentMessage {
  type: string;
  payload: any;
  logContext: LogContext;  // traceId 链路上下文
}
```

---

## 四、输出规范

### 4.1 输出目标

| 输出目标 | 场景 | 配置 |
|----------|------|------|
| **console** | 开发调试 | 始终开启，输出格式化文本 |
| **file** | 生产环境 | 按层级分流，滚动写入 |
| **（扩展）** | ELK/Grafana | 通过 file 输出或直接推送 |

### 4.2 console 输出格式

开发环境输出人类可读格式：

```
2026-04-03 17:37:31 [INFO] [Reins/谷子] a1b2c3d4 span-1a2b 任务执行完成 {"duration":1234}
2026-04-03 17:37:32 [DEBUG] [Grasp] a1b2c3d4 span-2c3d 认知查询完成 {"entities":3}
2026-04-03 17:37:33 [ERROR] [Vigil] a1b2c3d4 span-4e5f 越权操作被拦截 {"operation":"delete","resource":"user"}
```

格式：`{时间} [{级别}] [{层级/Agent}] {traceId} {spanId} {消息} {数据}`

### 4.3 file 输出格式

生产环境输出 JSON Lines（每行一个 JSON）：

```
{"ts":"...","level":"info",...}
{"ts":"...","level":"debug",...}
{"ts":"...","level":"error",...}
```

### 4.4 文件分流策略

| 层级 | 文件路径 | 说明 |
|------|----------|------|
| info | `logs/nexus-{date}.log` | 日常运行日志 |
| warn | `logs/nexus-{date}-warn.log` | 警告日志 |
| error | `logs/nexus-{date}-error.log` | 错误日志 |
| all | `logs/nexus-{date}-all.log` | 全量日志（可选） |

### 4.5 文件滚动策略

```
滚动周期：每天一个新文件
保留期限：7 天（可配置）
文件大小：单文件无限制（按天滚动）
压缩：旧文件 gzip 压缩
```

### 4.6 日志配置示例

```typescript
interface LoggerConfig {
  level: 'debug' | 'info' | 'warn' | 'error';
  outputs: ('console' | 'file')[];
  console: {
    pretty: boolean;  // 开发环境 true，生产 false
  };
  file: {
    dir: string;           // 日志目录
    maxDays: number;        // 保留天数
    separateLevels: boolean; // 按层级分流
  };
  redact: string[];  // 敏感字段正则，如 ["token", "key", "secret", "password"]
}

const defaultConfig: LoggerConfig = {
  level: 'info',
  outputs: ['console', 'file'],
  console: { pretty: true },
  file: { dir: 'logs', maxDays: 7, separateLevels: true },
  redact: ['token', 'key', 'secret', 'password', 'authorization', 'x-api-key'],
};
```

---

## 五、敏感信息脱敏

### 5.1 脱敏规则

| 字段类型 | 脱敏方式 | 示例 |
|----------|----------|------|
| API Key/Token | `**REDACTED**` | `sk-xxx` → `**REDACTED**` |
| 密码 | `**REDACTED**` | `Aa123456` → `**REDACTED**` |
| 邮箱 | 部分隐藏 | `user@example.com` → `u**r@example.com` |
| 手机号 | 部分隐藏 | `13800138000` → `138****8000` |
| 身份证 | 部分隐藏 | `110101199001011234` → `110101********1234` |

### 5.2 脱敏实现

```typescript
// 递归扫描并脱敏敏感字段
function redactObject(obj: any, path = ''): any {
  if (obj === null || obj === undefined) return obj;
  
  if (typeof obj === 'string') {
    // 检查是否匹配敏感字段名
    for (const pattern of redactPatterns) {
      if (pattern.test(path)) {
        return '**REDACTED**';
      }
    }
    // 检查是否是 URL 中的 token
    if (/=[A-Za-z0-9_-]{20,}/.test(obj)) {
      return obj.replace(/=([A-Za-z0-9_-]{20,})/, '=**REDACTED**');
    }
    return obj;
  }
  
  if (typeof obj === 'object') {
    const result = Array.isArray(obj) ? [] : {};
    for (const [key, value] of Object.entries(obj)) {
      result[key] = redactObject(value, path ? `${path}.${key}` : key);
    }
    return result;
  }
  
  return obj;
}
```

---

## 六、框架选型

### 6.1 参考方案

| 框架 | 语言 | 特点 | 适用场景 |
|------|------|------|----------|
| **Pino** | Node.js | 最高性能，JSON 输出，traceId 支持好 | 高并发 API 服务 |
| **Winston** | Node.js | 最流行，格式灵活，传输器丰富 | 通用场景 |
| **Roarr** | Node.js | 结构化 JSON，链路追踪友好 | 需要链路追踪的应用 |

### 6.2 推荐方案：Pino

**选择理由**：

1. **性能最优**：Pino 比 Winston 快 5-10 倍，适合高并发场景
2. **JSON 原生**：输出即为 JSON Lines，便于 ELK/Grafana 接入
3. **链路友好**：天然支持 traceId 注入和链路传播
4. **轻量**：无多余依赖，符合 Nexus 轻量原则

### 6.3 pino 使用示例

```typescript
import pino from 'pino';

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    level: (label) => ({ level: label }),
  },
  timestamp: () => `,"ts":"${new Date().toISOString()}"`,
  base: {
    layer: 'reins',
    agentId: process.env.AGENT_ID,
    agentName: process.env.AGENT_NAME,
  },
});

// 创建子 logger（继承 base，注入 traceId）
function createChildLogger(traceId: string, spanId: string) {
  return logger.child({ traceId, spanId });
}
```

---

## 七、与 Vigil 的集成

### 7.1 Vigil 日志要求

Vigil（鉴）作为安全层，对日志有特殊要求：

| 要求 | 说明 |
|------|------|
| **全量记录** | Vigil 日志 level 恒为 info，不受全局 level 影响 |
| **操作类型标记** | 区分 read/write/delete/execute 等操作 |
| **资源标识** | 记录操作的资源类型和标识 |
| **结果标注** | 成功/失败/拦截必须明确标注 |

### 7.2 Vigil 日志扩展字段

```typescript
interface VigilLog extends BaseLog {
  layer: 'vigil';
  operation: 'read' | 'write' | 'delete' | 'execute' | 'authorize';
  resource: {
    type: string;       // user/file/agent/capsule
    id: string;
    name?: string;
  };
  result: 'success' | 'denied' | 'error';
  reason?: string;     // 拒绝原因
  trustScore?: number;  // 操作时信任评分
}
```

---

## 八、API 接口

### 8.1 核心接口

```typescript
// 创建带 traceId 的 logger
function getLogger(config: LoggerConfig): Logger;

// 创建子 logger（注入链路上下文）
function child(parent: Logger, ctx: LogContext): Logger;

// 快捷日志方法
function debug(msg: string, data?: object): void;
function info(msg: string, data?: object): void;
function warn(msg: string, data?: object): void;
function error(msg: string, error?: Error, data?: object): void;

// 链路操作
function startSpan(name: string, parent?: LogContext): LogContext;
function endSpan(ctx: LogContext, durationMs: number): void;

// 敏感信息脱敏
function redact(obj: any): any;
```

### 8.2 使用示例

```typescript
import { getLogger, startSpan } from '@nexus/logger';

// 初始化
const logger = getLogger({
  level: 'info',
  outputs: ['console', 'file'],
  file: { dir: 'logs', maxDays: 7, separateLevels: true },
});

// 业务中使用
const span = startSpan('task-execution');
const childLogger = logger.child({ 
  traceId: span.traceId, 
  spanId: span.spanId,
  layer: 'reins',
  agentId: '876b9322-...',
  agentName: '谷子',
  taskId: 'cbe80ee6-...'
});

childLogger.info('开始执行任务', { taskName: '部署 vLLM' });
// ... 执行逻辑
childLogger.info('任务完成', { duration: 1234 });
```

---

## 九、文件结构

```
nexus-logging/
├── src/
│   ├── index.ts              # 导出公共接口
│   ├── logger.ts             # 核心 logger 实现
│   ├── context.ts            # traceId/span 链路管理
│   ├── redact.ts             # 敏感信息脱敏
│   ├── formatters.ts         # 格式化器
│   └── config.ts             # 配置定义
├── test/
│   ├── logger.test.ts
│   ├── context.test.ts
│   └── redact.test.ts
├── package.json
└── README.md
```

---

## 十、实现计划

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| 1 | 核心 logger + console 输出 | P0 |
| 2 | file 输出 + 滚动策略 | P0 |
| 3 | traceId/span 链路管理 | P0 |
| 4 | 敏感信息脱敏 | P0 |
| 5 | 与各层集成 | P1 |
| 6 | ELK/Grafana 集成 | P2 |

---

## 十一、已验证决策

| 决策 | 理由 |
|------|------|
| Pino 而非 Winston | 性能优先，JSON 原生 |
| JSON Lines 而非单个 JSON | 便于流式处理 |
| 按天滚动而非按大小 | 便于日志检索和清理 |
| traceId UUIDv4 | 足够随机，不碰撞 |
| 脱敏在写入前 | 防止敏感信息泄露 |

---

*本文档为框架设计，框架实现后需更新状态并关联代码仓库。*
