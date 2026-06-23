"""
FlowForge v0.1 — 一键启动脚本
用法: python run.py
"""
import sys
import subprocess
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON = r"E:\anaconda3\envs\graph\python"
BACKEND = os.path.join(ROOT, "backend")
FRONTEND = os.path.join(ROOT, "frontend")


def start_backend():
    """在当前终端启动后端（阻塞）。"""
    print("[FlowForge] Starting backend on http://localhost:8000 ...")
    subprocess.run([
        PYTHON, "-m", "uvicorn", "src.api.router:app",
        "--host", "0.0.0.0", "--port", "8000", "--reload",
    ], cwd=BACKEND)


def start_frontend():
    """在当前终端启动前端（阻塞）。"""
    print("[FlowForge] Starting frontend on http://localhost:5173 ...")
    subprocess.run(["npm", "run", "dev"], cwd=FRONTEND, shell=True)


def print_help():
    print("""
╔══════════════════════════════════════════════╗
║           FlowForge v0.1 启动指南             ║
╠══════════════════════════════════════════════╣
║                                              ║
║  终端 1 — 后端 (二选一):                      ║
║    cd backend                                ║
║    python run.py                             ║
║  或: python run.py backend                   ║
║                                              ║
║  终端 2 — 前端:                              ║
║    cd frontend && npm run dev                ║
║                                              ║
║  后端 → http://localhost:8000/docs            ║
║  前端 → http://localhost:5173                 ║
║                                              ║
╚══════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "backend":
        start_backend()
    elif cmd == "frontend":
        start_frontend()
    else:
        print_help()
