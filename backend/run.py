"""
FlowForge backend — 启动入口
用法: cd backend && python run.py
"""
import sys
import os

# 确保 backend 目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # 环境检测
    if sys.version_info < (3, 10):
        print(f"[FlowForge] WARNING: Python {sys.version} detected. Recommended: 3.11+")
        print(f"[FlowForge] Current executable: {sys.executable}")

    try:
        import uvicorn
    except ImportError:
        print("[FlowForge] ERROR: uvicorn not found. Install dependencies first:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    print(f"[FlowForge] Python: {sys.executable}")
    print(f"[FlowForge] Starting on http://localhost:8000 ...")
    uvicorn.run(
        "src.api.router:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
