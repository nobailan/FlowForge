"""Cleanup stuck executions and OpenCode sessions before restart."""
import asyncio, httpx, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import SessionLocal
from src.models import ExecutionRun

# 1. Clean DB
db = SessionLocal()
running = db.query(ExecutionRun).filter(ExecutionRun.status == 'running').all()
for r in running:
    db.delete(r)
if running:
    db.commit()
print(f"DB: cleaned {len(running)} stuck runs")
db.close()

# 2. Clean OpenCode
async def clean_opencode():
    try:
        async with httpx.AsyncClient() as cl:
            r = await cl.get('http://localhost:4096/session?directory=E:/agentProject/harness_lab', timeout=5)
            sessions = r.json()
            for s in sessions:
                await cl.delete(
                    f'http://localhost:4096/session/{s["id"]}?directory=E:/agentProject/harness_lab',
                    timeout=5)
            print(f"OpenCode: cleaned {len(sessions)} sessions")
    except Exception as e:
        print(f"OpenCode: skip (server not running)")

asyncio.run(clean_opencode())
