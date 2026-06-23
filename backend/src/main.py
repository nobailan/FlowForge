"""
FlowForge v0.1 — 后端入口
启动方式:
    cd backend
    python -m src.main
    python run.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api.router:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
