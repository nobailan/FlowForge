"""
FlowForge v0.1 - 执行 API
REST 端点 + WebSocket 端点。
"""
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi import Depends

from ..schemas import ExecuteRequest, ExecuteResponse, ExecutionResult
from ..engine.executor import FlowExecutor
from ..engine.monitor import ws_manager, NodeEvent
from ..database import get_db, SessionLocal
from ..models import ExecutionRun, Architecture

router = APIRouter()


@router.post("/", response_model=ExecuteResponse)
async def execute_flow(data: ExecuteRequest, background_tasks: BackgroundTasks,
                       db: Session = Depends(get_db)):
    """执行一个画布流程。"""
    run = ExecutionRun(
        architecture_id=None,
        status="running",
        input_data={"input_text": data.input_text, "canvas_data": data.canvas_data.model_dump()},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    executor = FlowExecutor(data.canvas_data.model_dump(), execution_id=run.id)

    # 后台执行 — 使用独立的 DB session，避免请求级 session 提前关闭
    async def run_execution():
        bg_db = SessionLocal()
        try:
            result = await executor.execute(data.input_text)
            bg_run = bg_db.query(ExecutionRun).filter(ExecutionRun.id == run.id).first()
            if bg_run:
                bg_run.status = "completed"
                bg_run.output_data = {
                    "final_output": result["final_output"],
                    "node_outputs": result.get("node_outputs", {}),
                    "total_tool_calls": result.get("total_tool_calls", 0),
                }
                bg_run.total_latency_ms = result.get("total_latency_ms", 0)
                bg_run.total_tokens = result.get("total_tokens", 0)
                bg_run.node_events = result.get("all_events", [])
                bg_db.commit()
        except Exception as e:
            bg_run = bg_db.query(ExecutionRun).filter(ExecutionRun.id == run.id).first()
            if bg_run:
                bg_run.status = "failed"
                bg_run.error_message = str(e)
                bg_db.commit()
        finally:
            bg_db.close()

    background_tasks.add_task(run_execution)

    return ExecuteResponse(execution_id=executor.execution_id, status="running")


@router.get("/{execution_id}", response_model=ExecutionResult)
def get_execution(execution_id: str, db: Session = Depends(get_db)):
    """获取执行结果。"""
    run = db.query(ExecutionRun).filter(ExecutionRun.id == execution_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ExecutionResult(
        id=run.id,
        architecture_id=run.architecture_id,
        status=run.status,
        input_data=run.input_data,
        output_data=run.output_data,
        total_latency_ms=run.total_latency_ms,
        total_tokens=run.total_tokens,
        node_events=run.node_events or [],
        error_message=run.error_message or "",
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


@router.get("/{execution_id}/events")
def get_execution_events(execution_id: str, db: Session = Depends(get_db)):
    """获取执行的所有节点事件。"""
    run = db.query(ExecutionRun).filter(ExecutionRun.id == execution_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Execution not found")
    return run.node_events or []


@router.websocket("/{execution_id}/ws")
async def websocket_execution(websocket: WebSocket, execution_id: str):
    """WebSocket 端点 —— 实时接收节点执行事件。"""
    await websocket.accept()
    await ws_manager.connect(execution_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("{"):
                # 客户端可能发送控制消息
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(execution_id, websocket)
    except Exception:
        await ws_manager.disconnect(execution_id, websocket)
