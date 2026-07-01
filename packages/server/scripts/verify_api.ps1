<#
API 端点验证脚本 (P6-2)
验证所有关键 API 端点的可用性和响应。
用法: pwsh -File scripts\verify_api.ps1 [-BaseUrl http://localhost:8097]
#>

param(
    [string]$BaseUrl = "http://localhost:8097"
)

$passCount = 0
$failCount = 0
$totalCount = 0

function Test-Endpoint {
    param(
        [string]$Path,
        [string]$Method = "GET",
        [string]$Description,
        [string]$Body = $null,
        [switch]$ExpectData
    )

    $script:totalCount++
    $uri = "$BaseUrl$Path"

    try {
        $params = @{
            Uri = $uri
            Method = $Method
            TimeoutSec = 10
            UseBasicParsing = $true
            ErrorAction = "Stop"
        }

        if ($Body) {
            $params.Body = $Body
            $params.ContentType = "application/json"
        }

        $response = Invoke-RestMethod @params

        $script:passCount++

        # 尝试获取响应摘要
        $summary = ""
        if ($response -is [System.Collections.IList]) {
            $summary = "[$($response.Count) items]"
        } elseif ($response -is [PSCustomObject]) {
            $props = $response.PSObject.Properties | Select-Object -First 3 | ForEach-Object {
                $v = $_.Value
                if ($v -is [string] -and $v.Length -gt 50) { $v = $v.Substring(0, 50) + "..." }
                "$($_.Name)=$v"
            }
            $summary = "{{$($props -join ', ')}}"
        }

        Write-Host "  ✓ $Method $Path → 200 $summary" -ForegroundColor Green
    }
    catch {
        $script:failCount++
        $errorMsg = $_.Exception.Message
        if ($errorMsg -match "(\d{3})") {
            $statusStr = "HTTP $($Matches[1])"
        } else {
            $statusStr = "ERR"
        }
        Write-Host "  ✗ $Method $Path → $statusStr" -ForegroundColor Red
        Write-Host "    $errorMsg" -ForegroundColor DarkGray
    }
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Grever API 端点验证" -ForegroundColor Cyan
Write-Host " 基地址: $BaseUrl" -ForegroundColor Cyan
Write-Host " 时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- 健康检查 ---
Write-Host "[健康检查]" -ForegroundColor Yellow
Test-Endpoint "/api/v1/health" -Description "健康检查"

# --- 核心 CRUD 列表 ---
Write-Host ""
Write-Host "[核心资源列表]" -ForegroundColor Yellow
Test-Endpoint "/api/v1/goals/" -Description "目标列表"
Test-Endpoint "/api/v1/projects/" -Description "项目列表"
Test-Endpoint "/api/v1/tasks/" -Description "任务列表"
Test-Endpoint "/api/v1/agents/" -Description "智能体列表"
Test-Endpoint "/api/v1/agents/online" -Description "在线智能体"
Test-Endpoint "/api/v1/scenarios/" -Description "场景库"
Test-Endpoint "/api/v1/industry-tags/" -Description "行业标签"
Test-Endpoint "/api/v1/industry-tags/_industries" -Description "行业列表"
Test-Endpoint "/api/v1/workflows/" -Description "工作流列表"
Test-Endpoint "/api/v1/disputes/" -Description "裁决列表"
Test-Endpoint "/api/v1/disputes/stats" -Description "裁决统计"
Test-Endpoint "/api/v1/skills" -Description "技能列表"
Test-Endpoint "/api/v1/settings/" -Description "系统设置"
Test-Endpoint "/api/v1/mcp" -Description "MCP 服务"
Test-Endpoint "/api/v1/mcp-servers" -Description "MCP 服务器列表"
Test-Endpoint "/api/v1/capabilities" -Description "能力列表"
Test-Endpoint "/api/v1/tasks/statuses" -Description "任务状态列表"
Test-Endpoint "/api/v1/tasks/labels/all" -Description "任务标签"
Test-Endpoint "/api/v1/human-input/pending" -Description "待处理人工输入"
Test-Endpoint "/api/v1/human-input/stats" -Description "人工输入统计"
Test-Endpoint "/api/v1/attachments" -Description "附件列表"
Test-Endpoint "/api/v1/artifacts/" -Description "产物列表"

# --- 写入操作测试 ---
Write-Host ""
Write-Host "[写入操作]" -ForegroundColor Yellow
Test-Endpoint "/api/v1/goals/" -Method "POST" -Description "创建目标" -Body '{"title": "API验证测试目标", "description": "自动化验证"}'

# --- OpenAPI 文档 ---
Write-Host ""
Write-Host "[文档]" -ForegroundColor Yellow
Test-Endpoint "/openapi.json" -Description "OpenAPI 文档"

# --- 汇总 ---
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 总计: $totalCount 个端点" -ForegroundColor White
Write-Host " 通过: $passCount" -ForegroundColor Green
Write-Host " 失败: $failCount" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Green" })
Write-Host "============================================" -ForegroundColor Cyan

if ($failCount -gt 0) {
    Write-Host ""
    Write-Host "⚠ 有 $failCount 个端点验证失败" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host ""
    Write-Host "✓ 所有端点验证通过！" -ForegroundColor Green
    exit 0
}
