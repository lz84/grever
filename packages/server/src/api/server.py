"""FastAPI 应用入口 — 只做创建 app + 注册路由（≤ 50 行铁律）"""

import os, sys
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI

_project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
load_dotenv(_project_root / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from persistence.base import DatabaseConfig
from reins.common import ReinsServer
from persistence.database import DatabaseManager
from api.app_state import set_reins, set_db_manager, setup_cors
from api.lifespan import lifespan_handler
from api.error_handler import register_exception_handlers
from api.initialization import check_initialization
from api.routers import get_routers


def create_app() -> FastAPI:
    db_path = os.environ.get("SQLITE_PATH")
    if not db_path:
        _print_init_error("未设置 SQLITE_PATH 环境变量", "请创建 .env 文件或运行初始化脚本")
        raise RuntimeError("SQLITE_PATH 未设置")
    if not check_initialization(db_path):
        os.environ["REINS_INIT_MODE"] = "true"
    reins = ReinsServer(db_config=DatabaseConfig(provider="sqlite", path=db_path))
    db = DatabaseManager(DatabaseConfig(provider="sqlite", path=db_path))
    set_reins(reins); set_db_manager(db)
    app = FastAPI(lifespan=lifespan_handler)
    setup_cors(app)
    for r in get_routers():
        app.include_router(r["router"], prefix=r.get("prefix", ""), tags=r.get("tags", [])) if isinstance(r, dict) else app.include_router(r)
    register_exception_handlers(app)
    @app.get("/")
    def root():
        return {"service": "Grever Reins API", "status": "running"}
    
    @app.get("/health")
    def health():
        return {"status": "healthy"}
    
    @app.get("/api/v1/health")
    def api_v1_health():
        return {"status": "healthy"}
    return app

def _print_init_error(title: str, detail: str) -> None:
    s = "=" * 60
    print(f"\n{s}\n  ❌ 错误：{title}\n{s}\n  {detail}:\n\n  cd packages/server\n  python scripts/init_nexus.py\n\n  或手动设置环境变量：export SQLITE_PATH=/path/to/reins.db\n{s}\n", file=sys.stderr)

app = create_app()
