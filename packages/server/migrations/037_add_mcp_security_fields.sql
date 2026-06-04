-- 添加MCP服务器的安全相关字段
ALTER TABLE mcp_servers ADD COLUMN auth_type VARCHAR(20) DEFAULT 'none';
ALTER TABLE mcp_servers ADD COLUMN api_key TEXT;
ALTER TABLE mcp_servers ADD COLUMN rate_limit INT DEFAULT 0;
ALTER TABLE mcp_servers ADD COLUMN ssl_verify BOOLEAN DEFAULT 1;