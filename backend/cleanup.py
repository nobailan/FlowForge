"""Cleanup stuck executions and OpenCode sessions before restart."""
import asyncio, aiohttp, sys, os
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
        async with aiohttp.ClientSession() as s:
            async with s.get('http://localhost:4096/session?directory=E:/agentProject/harness_lab') as r:
                if r.status != 200:
                    print(f"OpenCode: skip (status {r.status})")
                    return
                sessions = await r.json()
            for sess in sessions:
                async with s.delete(f'http://localhost:4096/session/{sess["id"]}?directory=E:/agentProject/harness_lab') as _:
                    pass
            print(f"OpenCode: cleaned {len(sessions)} sessions")
    except Exception as e:
        print(f"OpenCode: skip ({e})")

asyncio.run(clean_opencode())
