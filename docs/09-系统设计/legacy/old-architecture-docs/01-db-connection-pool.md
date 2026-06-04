# Nexus 数据库连接池设计

**版本**: v1.0  
**作者**: 麻子  
**最后更新**: 2026-04-03  
**Issue**: MAK-69

---

## 1. 概述

本文档描述 Nexus 平台数据库连接池的设计方案，包括连接池配置参数、健康检查机制和自动重连策略。连接池是数据库访问层的核心组件，合理的设计能够显著提升系统性能、保证系统稳定性。

---

## 2. 连接池配置参数

### 2.1 配置参数定义

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `pool.minSize` | 5 | 最小空闲连接数，连接池启动时预创建的连接数 |
| `pool.maxSize` | 50 | 最大连接数，连接池允许的最大并发连接数 |
| `pool.idleTimeout` | 300000 | 空闲超时（毫秒），连接空闲超过此时间后被回收，默认 5 分钟 |
| `pool.connectionTimeout` | 30000 | 连接超时（毫秒），获取连接等待的最大时间，默认 30 秒 |
| `pool.idleTestInterval` | 60000 | 空闲连接检查间隔（毫秒），定期检查空闲连接是否仍然有效，默认 1 分钟 |

### 2.2 配置示例（YAML 格式）

```yaml
database:
  host: "${DB_HOST:localhost}"
  port: "${DB_PORT:5432}"
  database: "${DB_NAME:nexus}"
  username: "${DB_USER:nexus}"
  password: "${DB_PASSWORD:secret}"
  
pool:
  minSize: 5
  maxSize: 50
  idleTimeout: 300000      # 5 分钟
  connectionTimeout: 30000  # 30 秒
  idleTestInterval: 60000   # 1 分钟
```

### 2.3 参数设计原则

**最小连接数（minSize）**：
- 根据正常负载下的并发需求设置
- 过小：频繁创建/销毁连接，增加开销
- 过大：占用不必要的数据库资源

**最大连接数（maxSize）**：
- 根据数据库服务器的处理能力设置
- 考虑数据库的 max_connections 配置
- 建议设为数据库处理能力的 50%~80%

**空闲超时（idleTimeout）**：
- 平衡资源释放和连接重建开销
- 生产环境建议 5~10 分钟
- 过长会占用无用连接，过短会导致频繁重建

**连接超时（connectionTimeout）**：
- 控制获取连接的最大等待时间
- 应大于正常查询时间的最大值
- 超时后应快速失败，避免线程阻塞

---

## 3. 健康检查机制

### 3.1 健康检查策略

采用**分层健康检查**策略，包括：

1. **连接获取时检查**：从连接池获取连接时，验证连接有效性
2. **空闲连接定期检查**：后台线程定期检查空闲连接
3. **全局健康探测**：定时执行数据库健康探测

### 3.2 连接获取时检查

当应用代码从连接池请求连接时：

```
1. 从空闲队列获取连接
2. 执行快速有效性验证（socket 检查）
3. 若连接已关闭或无效，从连接池移除并重试
4. 最多重试 max(3, 最大重试次数) 次
5. 若仍失败，尝试创建新连接
```

**实现代码示意**：

```python
def acquire_connection(self):
    for attempt in range(self.max_retries):
        conn = self._get_from_idle_queue()
        if conn is None:
            conn = self._create_new_connection()
        
        if self._is_connection_valid(conn):
            return conn
        else:
            self._remove_invalid_connection(conn)
    
    raise ConnectionPoolExhaustedError("Failed to acquire valid connection")
```

### 3.3 空闲连接定期检查

后台线程定期扫描空闲连接：

```
检查周期：idleTestInterval（默认 60 秒）

扫描逻辑：
1. 遍历所有空闲连接
2. 对空闲时间超过 idleTimeout 的连接：
   - 关闭并移除该连接
3. 对空闲时间超过 idleTimeout / 2 的连接：
   - 执行 ping 命令验证有效性
   - 若无效，关闭并移除
   - 若有效，保留在池中
4. 若当前连接数低于 minSize，补充新连接
```

### 3.4 全局健康探测

定时执行数据库健康探测，用于监控和告警：

```
探测周期：5 分钟

探测内容：
1. 执行 SELECT 1 查询
2. 记录响应时间
3. 若响应时间超过阈值或查询失败：
   - 触发告警通知
   - 若连续失败 N 次，标记数据库为不可用
```

### 3.5 健康检查配置

```yaml
healthCheck:
  enabled: true
  testOnBorrow: true          # 获取连接时检查
  testOnReturn: false         # 归还连接时检查
  testWhileIdle: true          # 空闲时定期检查
  idleTestInterval: 60000     # 空闲检查间隔（毫秒）
  validationInterval: 300000  # 全局探测间隔（毫秒）
  validationQuery: "SELECT 1" # 健康检查 SQL
  validationTimeout: 5000     # 健康检查超时（毫秒）
```

---

## 4. 自动重连策略

### 4.1 重连触发条件

以下情况会触发自动重连：

| 触发条件 | 检测方式 | 处理策略 |
|----------|----------|----------|
| 连接获取时发现连接已断开 | 执行查询失败 | 标记连接失效，重试获取 |
| 空闲连接超过 idleTimeout | 后台扫描 | 关闭过期连接 |
| 数据库服务器短暂不可用 | 连续健康检查失败 | 指数退避重连 |
| 网络抖动导致连接中断 | Socket 异常 | 快速重试 + 重连 |

### 4.2 重连算法

#### 4.2.1 指数退避重连（用于数据库服务器不可用）

```
初始重试间隔：1 秒
最大重试间隔：60 秒
退避系数：2
最大重试次数：无限（直到数据库恢复）

重试间隔计算：min(initial_interval * (coefficient ^ attempt), max_interval)

示例：
- 第 1 次：1 秒
- 第 2 次：2 秒
- 第 3 次：4 秒
- ...
- 第 6 次：32 秒
- 第 7+ 次：60 秒（封顶）
```

#### 4.2.2 快速重试（用于临时网络抖动）

```
适用场景：Socket 连接中断、连接被服务器关闭
策略：立即重试 1~2 次，若失败则降级为指数退避重连
```

### 4.3 连接重试配置

```yaml
reconnection:
  enabled: true
  maxRetries: 3                    # 获取连接时的最大重试次数
  retryDelay: 1000                 # 重试延迟（毫秒）
  
  exponentialBackoff:
    enabled: true                  # 启用指数退避
    initialInterval: 1000          # 初始间隔（毫秒）
    maxInterval: 60000             # 最大间隔（毫秒）
    coefficient: 2                 # 退避系数
    maxRetries: -1                 # 最大重试次数，-1 表示无限重试
  
  fastRetry:
    enabled: true                  # 启用快速重试
    maxAttempts: 2                # 快速重试次数
```

### 4.4 重连流程图

```
连接获取请求
     │
     ▼
获取连接失败？
     │
     ├─否─▶ 返回有效连接
     │
     └─是─▶ 检测失败类型
              │
              ├─网络抖动（Socket 错误）
              │    │
              │    └─▶ 快速重试（1~2次）
              │           │
              │           ├─成功─▶ 返回连接
              │           └─失败─▶ 指数退避重连
              │
              ├─连接已关闭（SQL 错误 code: 08006）
              │    │
              │    └─▶ 移除无效连接，重试获取
              │
              └─数据库不可用（连接超时/拒绝）
                   │
                   └─▶ 指数退避重连
```

### 4.5 熔断降级

为防止数据库故障时大量请求堆积，引入熔断机制：

```yaml
circuitBreaker:
  enabled: true
  failureThreshold: 5              # 连续失败次数触发熔断
  successThreshold: 3              # 连续成功次数恢复熔断
  halfOpenMaxCalls: 3              # 半开状态下允许的试探请求数
```

**熔断状态机**：
- **Closed（正常）**：请求正常通过，失败计数累加
- **Open（熔断）**：直接拒绝请求，快速失败
- **HalfOpen（半开）**：允许少量试探请求，探测数据库是否恢复

---

## 5. 连接生命周期

```
连接创建
    │
    ▼
可用状态 ────────────────────────▶ 使用中状态
    │                                    │
    │（归还连接）                         │（执行 SQL）
    │                                    │
    ▼                                    ▼
可用状态 ◀─────────────────────── 使用中状态
    │
    ├── idleTimeout 超时 ──▶ 关闭连接
    │
    ├── 健康检查失败 ──▶ 关闭连接
    │
    └── 连接池关闭 ──▶ 关闭所有连接
```

---

## 6. 监控与告警

### 6.1 关键监控指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| `db.pool.active` | 当前活跃连接数 | > maxSize * 80% |
| `db.pool.idle` | 当前空闲连接数 | < minSize * 50% |
| `db.pool.waiters` | 等待获取连接的线程数 | > 0 持续 30 秒 |
| `db.pool.connection.errors` | 连接错误次数 | > 10 次/分钟 |
| `db.pool.reconnect.count` | 重连次数 | > 50 次/5分钟 |
| `db.query.duration` | 查询耗时 | > 10 秒 |

### 6.2 日志记录

重连事件应记录详细日志：

```python
logger.warning(
    "Database connection reconnection",
    extra={
        "attempt": attempt,
        "next_retry_ms": next_retry_ms,
        "error": str(e),
        "pool_size": current_pool_size,
    }
)
```

---

## 7. 多数据源支持

Nexus 平台支持多个数据库实例，配置示例：

```yaml
datasources:
  primary:
    host: "${DB_PRIMARY_HOST:localhost}"
    port: 5432
    database: "nexus"
    pool:
      minSize: 10
      maxSize: 100
  
  analytics:
    host: "${DB_ANALYTICS_HOST:localhost}"
    port: 5432
    database: "nexus_analytics"
    pool:
      minSize: 5
      maxSize: 30
      idleTimeout: 600000  # 分析库空闲超时更长
```

每个数据源独立管理连接池，互不影响。

---

## 8. 附录

### 8.1 常见数据库错误码

| 数据库 | 错误码 | 说明 |
|--------|--------|------|
| PostgreSQL | 08006 | 连接已断开 |
| PostgreSQL | 08001 | 连接不可用 |
| MySQL | 2006 | MySQL server has gone away |
| MySQL | 2013 | Lost connection during query |

### 8.2 参考资料

- HikariCP Configuration: https://github.com/brettwooldridge/HikariCP
- PostgreSQL Connection Pooling: https://www.postgresql.org/docs/current/runtime-config-connection.html
- 数据库连接池最佳实践

---

**修订历史**：

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-04-03 | 初始版本 | 麻子 |
