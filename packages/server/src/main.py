"""
Nexus Reins 主程序
启动 Reins 服务端
"""

import asyncio
import uvicorn
from fastapi import FastAPI
from api.server import create_app
from reins.common import ReinsServer
from persistence.base import DatabaseConfig
from reins.common.database import DB_PATH

def main():
    """主函数"""
    # 创建数据库配置
    db_config = DatabaseConfig(
        provider="sqlite",
        path=DB_PATH
    )
    
    # 创建 Reins Server
    reins_server = ReinsServer(db_config=db_config)
    
    # 创建 FastAPI 应用
    app = create_app()
    
    # 设置应用的 state
    app.state.reins_server = reins_server
    
    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8097)

if __name__ == "__main__":
    main()