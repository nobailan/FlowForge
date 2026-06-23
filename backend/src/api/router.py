"""
FlowForge v0.1 - FastAPI 应用工厂
组装所有路由，返回可启动的 ASGI 应用。
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import APP_TITLE, APP_VERSION, DEBUG
from ..database import init_db
from ..engine.registry import get_registry

# 导入所有节点模块触发注册
from ..nodes import (  # noqa: F401
    llm_node_factory,
    tool_node_factory,
    retriever_node_factory,
    subagent_node_factory,
    condition_node_factory,
    loop_node_factory,
)

from .graph import router as graph_router
from .execute import router as execute_router
from .evaluate import router as evaluate_router
from .templates import router as templates_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期：启动时初始化数据库，关闭时清理资源。"""
    # startup
    init_db()
    registry = get_registry()
    types = registry.list_all()
    print(f"[FlowForge] {len(types)} node types registered: "
          f"{[t.name for t in types]}")
    yield
    # shutdown (预留)


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""
    app = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        debug=DEBUG,
        lifespan=lifespan,
    )

    # CORS —— 允许前端开发服务器
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(graph_router, prefix="/api/graphs", tags=["Graphs"])
    app.include_router(execute_router, prefix="/api/execute", tags=["Execute"])
    app.include_router(evaluate_router, prefix="/api/evaluate", tags=["Evaluate"])
    app.include_router(templates_router, prefix="/api/templates", tags=["Templates"])

    # 健康检查
    @app.get("/api/health")
    def health_check():
        registry = get_registry()
        return {
            "status": "ok",
            "version": APP_VERSION,
            "node_types": [t.name for t in registry.list_all()],
        }

    return app


# 模块级 app 实例（供 uvicorn 直接引用）
app = create_app()
