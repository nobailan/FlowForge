"""
FlowForge v0.1 - 评估 API
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..models import Architecture, EvaluationRun, TestSet
from ..schemas import (
    EvaluateRequest,
    EvaluationResult,
    EvalSummary,
    EvalDetail,
    CompareRequest,
    CompareResult,
    TestSetCreate,
    TestSetOut,
)
from ..evaluator.runner import EvaluationRunner
from ..evaluator.metrics import compute_metrics
from ..evaluator.comparator import compare_evaluations

router = APIRouter()


@router.post("/", response_model=EvaluationResult, status_code=201)
async def run_evaluation(data: EvaluateRequest, background_tasks: BackgroundTasks,
                         db: Session = Depends(get_db)):
    """启动一次评估运行。"""
    # 验证架构存在
    arch = db.query(Architecture).filter(Architecture.id == data.architecture_id).first()
    if not arch:
        raise HTTPException(status_code=404, detail="Architecture not found")

    # 验证测试集存在
    ts = db.query(TestSet).filter(TestSet.id == data.testset_id).first()
    if not ts:
        raise HTTPException(status_code=404, detail="Test set not found")

    # 创建评估记录
    eval_run = EvaluationRun(
        architecture_id=data.architecture_id,
        testset_name=ts.name,
        status="running",
    )
    db.add(eval_run)
    db.commit()
    db.refresh(eval_run)

    # 后台执行评估 — 使用独立 DB session
    async def run_eval():
        bg_db = SessionLocal()
        try:
            runner = EvaluationRunner(arch.canvas_data, ts.test_cases)
            result = await runner.run()
            bg_run = bg_db.query(EvaluationRun).filter(EvaluationRun.id == eval_run.id).first()
            if bg_run:
                bg_run.status = "completed"
                bg_run.summary = result["summary"]
                bg_run.detail_results = result["details"]
                bg_db.commit()
        except Exception as e:
            bg_run = bg_db.query(EvaluationRun).filter(EvaluationRun.id == eval_run.id).first()
            if bg_run:
                bg_run.status = "failed"
                bg_run.summary = {"error": str(e)}
                bg_db.commit()
        finally:
            bg_db.close()

    background_tasks.add_task(run_eval)

    return EvaluationResult(
        id=eval_run.id,
        architecture_id=eval_run.architecture_id,
        testset_name=eval_run.testset_name,
        status=eval_run.status,
        summary=EvalSummary(),
        detail_results=[],
        started_at=eval_run.started_at.isoformat() if eval_run.started_at else None,
        completed_at=eval_run.completed_at.isoformat() if eval_run.completed_at else None,
    )


@router.get("/runs/{run_id}", response_model=EvaluationResult)
def get_evaluation(run_id: str, db: Session = Depends(get_db)):
    """获取评估结果。"""
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    return EvaluationResult(
        id=run.id,
        architecture_id=run.architecture_id,
        testset_name=run.testset_name,
        status=run.status,
        summary=EvalSummary(**run.summary) if run.summary else EvalSummary(),
        detail_results=[EvalDetail(**d) for d in (run.detail_results or [])],
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


@router.get("/runs", response_model=list[EvaluationResult])
def list_evaluations(architecture_id: str | None = None, db: Session = Depends(get_db)):
    """列出评估结果。可选按 architecture_id 过滤。"""
    q = db.query(EvaluationRun)
    if architecture_id:
        q = q.filter(EvaluationRun.architecture_id == architecture_id)
    runs = q.order_by(EvaluationRun.completed_at.desc()).all()

    return [
        EvaluationResult(
            id=r.id,
            architecture_id=r.architecture_id,
            testset_name=r.testset_name,
            status=r.status,
            summary=EvalSummary(**r.summary) if r.summary else EvalSummary(),
            detail_results=[EvalDetail(**d) for d in (r.detail_results or [])],
            started_at=r.started_at.isoformat() if r.started_at else None,
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
        )
        for r in runs
    ]


@router.post("/compare", response_model=CompareResult)
def compare_runs(data: CompareRequest, db: Session = Depends(get_db)):
    """对比多个评估运行。"""
    if len(data.eval_run_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 eval run IDs to compare")

    runs = []
    for rid in data.eval_run_ids:
        run = db.query(EvaluationRun).filter(EvaluationRun.id == rid).first()
        if not run:
            raise HTTPException(status_code=404, detail=f"Evaluation run '{rid}' not found")

        # 获取架构名称
        arch = db.query(Architecture).filter(Architecture.id == run.architecture_id).first()
        arch_name = arch.name if arch else "Unknown"

        runs.append({
            "id": run.id,
            "architecture_id": run.architecture_id,
            "name": arch_name,
            "testset_name": run.testset_name,
            "status": run.status,
            "summary": run.summary or {},
            "details": run.detail_results or [],
        })

    result = compare_evaluations(runs)

    eval_results = [
        EvaluationResult(
            id=r["id"],
            architecture_id=r["architecture_id"],
            testset_name=r["testset_name"],
            status=r["status"],
            summary=EvalSummary(**r["summary"]) if r["summary"] else EvalSummary(),
            detail_results=[EvalDetail(**d) for d in r.get("details", [])],
        )
        for r in runs
    ]

    return CompareResult(runs=eval_results, diff=result)


# ==================== 测试集 CRUD ====================

@router.get("/test-sets", response_model=list[TestSetOut])
def list_test_sets(db: Session = Depends(get_db)):
    """列出所有测试集。"""
    sets = db.query(TestSet).order_by(TestSet.created_at.desc()).all()
    return [
        TestSetOut(
            id=s.id,
            name=s.name,
            description=s.description or "",
            test_cases=s.test_cases or [],
            created_at=s.created_at.isoformat() if s.created_at else None,
        )
        for s in sets
    ]


@router.post("/test-sets", response_model=TestSetOut, status_code=201)
def create_test_set(data: TestSetCreate, db: Session = Depends(get_db)):
    """创建测试集。"""
    ts = TestSet(
        name=data.name,
        description=data.description,
        test_cases=[tc.model_dump() for tc in data.test_cases],
    )
    db.add(ts)
    db.commit()
    db.refresh(ts)
    return TestSetOut(
        id=ts.id,
        name=ts.name,
        description=ts.description or "",
        test_cases=ts.test_cases or [],
        created_at=ts.created_at.isoformat() if ts.created_at else None,
    )


@router.delete("/test-sets/{testset_id}", status_code=204)
def delete_test_set(testset_id: str, db: Session = Depends(get_db)):
    """删除测试集。"""
    ts = db.query(TestSet).filter(TestSet.id == testset_id).first()
    if not ts:
        raise HTTPException(status_code=404, detail="Test set not found")
    db.delete(ts)
    db.commit()
