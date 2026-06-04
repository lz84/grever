import { useState } from "react"
import { Shield, AlertTriangle, CheckCircle, Clock, RefreshCw, Key, Lock, Unlock, Eye, EyeOff } from "lucide-react"
import { Button } from "@/shared/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/components/ui/card"
import { Badge } from "@/shared/components/ui/badge"
import { Input } from "@/shared/components/ui/input"
import { Label } from "@/shared/components/ui/label"
import { Textarea } from "@/shared/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select"
import { Switch } from "@/shared/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/components/ui/table"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/shared/components/ui/tabs"

interface SecurityEvent {
  id: string
  type: string
  severity: string
  source: string
  timestamp: string
  description: string
  resolved: boolean
}

interface ApiKey {
  id: string
  name: string
  key_preview: string
  permissions: string[]
  created: string
  expires: string
  last_used: string
  active: boolean
}

interface SecurityPolicy {
  id: string
  name: string
  description: string
  enabled: boolean
  level: string
}

export function SecurityCenter() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([
    {
      id: "key_1",
      name: "Production API Key",
      key_preview: "sk_live_•••••••••••••••••ABC123",
      permissions: ["read", "write", "delete"],
      created: "2025-01-15",
      expires: "2026-01-15",
      last_used: "2025-03-28",
      active: true,
    },
  ])

  const [securityEvents, setSecurityEvents] = useState<SecurityEvent[]>([
    {
      id: "evt_001",
      type: "认证失败",
      severity: "high",
      source: "192.168.1.105",
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      description: "连续5次密码错误，账户已锁定",
      resolved: false,
    },
    {
      id: "evt_002",
      type: "异常访问",
      severity: "medium",
      source: "10.0.0.42",
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      description: "短时间内大量请求，已触发限流",
      resolved: true,
    },
  ])

  const [policies, setPolicies] = useState<SecurityPolicy[]>([
    {
      id: "pol_1",
      name: "强制双因素认证",
      description: "所有用户必须启用双因素认证",
      enabled: true,
      level: "high",
    },
    {
      id: "pol_2",
      name: "IP白名单",
      description: "仅允许白名单IP访问管理后台",
      enabled: false,
      level: "medium",
    },
  ])

  const [newKeyName, setNewKeyName] = useState("")
  const [newKeyPerms, setNewKeyPerms] = useState("read,write")

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "bg-red-100 text-red-800 border-red-200"
      case "medium":
        return "bg-amber-100 text-amber-800 border-amber-200"
      case "low":
        return "bg-blue-100 text-blue-800 border-blue-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const handleRotateKey = (keyId: string) => {
    setApiKeys((keys) =>
      keys.map((k) =>
        k.id === keyId
          ? {
              ...k,
              key_preview: "sk_live_•••••••••••••••••XYZ789",
              created: new Date().toISOString().split("T")[0],
            }
          : k
      )
    )
  }

  const handleRevokeKey = (keyId: string) => {
    setApiKeys((keys) => keys.filter((k) => k.id !== keyId))
  }

  const handleTogglePolicy = (policyId: string) => {
    setPolicies((policies) =>
      policies.map((p) =>
        p.id === policyId ? { ...p, enabled: !p.enabled } : p
      )
    )
  }

  const handleCreateKey = () => {
    if (!newKeyName.trim()) return
    const newKey: ApiKey = {
      id: `key_${Date.now()}`,
      name: newKeyName,
      key_preview: "sk_live_•••••••••••••••••" + Math.random().toString(36).substring(8).toUpperCase(),
      permissions: newKeyPerms.split(",").map((p) => p.trim()),
      created: new Date().toISOString().split("T")[0],
      expires: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split("T")[0],
      last_used: "从未",
      active: true,
    }
    setApiKeys([...apiKeys, newKey])
    setNewKeyName("")
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Shield className="h-8 w-8" />
            安全中心
          </h1>
          <p className="text-muted-foreground mt-1">
            管理API密钥、监控安全事件、配置安全策略
          </p>
        </div>
        <Button variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      {/* Security overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">活跃密钥</CardTitle>
            <Key className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{apiKeys.filter((k) => k.active).length}</div>
            <p className="text-xs text-muted-foreground">已授权的 API 密钥</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">安全事件</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {securityEvents.filter((e) => !e.resolved).length}
            </div>
            <p className="text-xs text-muted-foreground">待处理安全事件</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">已解决</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {securityEvents.filter((e) => e.resolved).length}
            </div>
            <p className="text-xs text-muted-foreground">已处理的安全事件</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">活跃策略</CardTitle>
            <Lock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {policies.filter((p) => p.enabled).length}
            </div>
            <p className="text-xs text-muted-foreground">已启用的安全策略</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="api-keys" className="space-y-4">
        <TabsList>
          <TabsTrigger value="api-keys">API密钥</TabsTrigger>
          <TabsTrigger value="events">安全事件</TabsTrigger>
          <TabsTrigger value="policies">安全策略</TabsTrigger>
        </TabsList>

        {/* API Keys Tab */}
        <TabsContent value="api-keys" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>API密钥管理</CardTitle>
              <CardDescription>创建、轮换和撤销API密钥</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Create new key */}
              <div className="rounded-lg border p-4 space-y-3">
                <h4 className="font-medium">创建新密钥</h4>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="space-y-1">
                    <Label htmlFor="key-name">密钥名称</Label>
                    <Input
                      id="key-name"
                      placeholder="例如: Production Key"
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="key-perms">权限 (逗号分隔)</Label>
                    <Input
                      id="key-perms"
                      placeholder="read, write, delete"
                      value={newKeyPerms}
                      onChange={(e) => setNewKeyPerms(e.target.value)}
                    />
                  </div>
                  <div className="flex items-end">
                    <Button onClick={handleCreateKey} disabled={!newKeyName.trim()}>
                      创建密钥
                    </Button>
                  </div>
                </div>
              </div>

              {/* Key list */}
              <div className="space-y-3">
                {apiKeys.map((key) => (
                  <div key={key.id} className="rounded-lg border p-4">
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{key.name}</span>
                          <Badge variant={key.active ? "default" : "secondary"}>
                            {key.active ? "活跃" : "已撤销"}
                          </Badge>
                        </div>
                        <p className="font-mono text-sm text-muted-foreground">
                          {key.key_preview}
                        </p>
                        <div className="flex gap-4 text-xs text-muted-foreground">
                          <span>权限: {key.permissions.join(", ")}</span>
                          <span>创建: {key.created}</span>
                          <span>过期: {key.expires}</span>
                          <span>最后使用: {key.last_used}</span>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRotateKey(key.id)}
                        >
                          <RefreshCw className="mr-1 h-3 w-3" />
                          轮换
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleRevokeKey(key.id)}
                        >
                          撤销
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Events Tab */}
        <TabsContent value="events" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>安全事件</CardTitle>
              <CardDescription>监控和响应安全事件</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>严重程度</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>来源</TableHead>
                    <TableHead>时间</TableHead>
                    <TableHead>描述</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {securityEvents.map((event) => (
                    <TableRow key={event.id}>
                      <TableCell>
                        <Badge className={getSeverityColor(event.severity)}>
                          {event.severity === "high" ? "高" : event.severity === "medium" ? "中" : "低"}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{event.type}</TableCell>
                      <TableCell className="font-mono text-xs">{event.source}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(event.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell className="max-w-xs truncate text-sm">
                        {event.description}
                      </TableCell>
                      <TableCell>
                        <Badge variant={event.resolved ? "default" : "destructive"}>
                          {event.resolved ? "已解决" : "待处理"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {!event.resolved && (
                          <Button variant="outline" size="sm">
                            标记已解决
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Policies Tab */}
        <TabsContent value="policies" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>安全策略</CardTitle>
              <CardDescription>配置和管理安全策略</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {policies.map((policy) => (
                <div key={policy.id} className="flex items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{policy.name}</span>
                      <Badge className={getSeverityColor(policy.level)}>
                        {policy.level === "high" ? "高" : policy.level === "medium" ? "中" : "低"}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{policy.description}</p>
                  </div>
                  <Switch checked={policy.enabled} onCheckedChange={() => handleTogglePolicy(policy.id)} />
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default SecurityCenter;
