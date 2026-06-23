"""
FlowForge v0.1 - 架构 CRUD API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Architecture
from ..schemas import (
    ArchitectureCreate,
    ArchitectureUpdate,
    ArchitectureSummary,
    ArchitectureDetail,
    CanvasData,
)

router = APIRouter()


@router.get("/", response_model=list[ArchitectureSummary])
def list_architectures(db: Session = Depends(get_db)):
    """列出所有已保存的架构。"""
    archs = db.query(Architecture).order_by(Architecture.updated_at.desc()).all()
    return [
        ArchitectureSummary(
            id=a.id,
            name=a.name,
            description=a.description or "",
            created_at=a.created_at.isoformat() if a.created_at else None,
            updated_at=a.updated_at.isoformat() if a.updated_at else None,
        )
        for a in archs
    ]


@router.post("/", response_model=ArchitectureDetail, status_code=201)
def create_architecture(data: ArchitectureCreate, db: Session = Depends(get_db)):
    """创建新架构。"""
    arch = Architecture(
        name=data.name,
        description=data.description,
        canvas_data=data.canvas_data.model_dump(),
        metadata_={"version": 1, "created_at_iso": ""},
    )
    db.add(arch)
    db.commit()
    db.refresh(arch)
    return _to_detail(arch)


@router.get("/{arch_id}", response_model=ArchitectureDetail)
def get_architecture(arch_id: str, db: Session = Depends(get_db)):
    """获取单个架构详情。"""
    arch = db.query(Architecture).filter(Architecture.id == arch_id).first()
    if not arch:
        raise HTTPException(status_code=404, detail="Architecture not found")
    return _to_detail(arch)


@router.put("/{arch_id}", response_model=ArchitectureDetail)
def update_architecture(arch_id: str, data: ArchitectureUpdate, db: Session = Depends(get_db)):
    """更新架构。"""
    arch = db.query(Architecture).filter(Architecture.id == arch_id).first()
    if not arch:
        raise HTTPException(status_code=404, detail="Architecture not found")

    if data.name is not None:
        arch.name = data.name
    if data.description is not None:
        arch.description = data.description
    if data.canvas_data is not None:
        arch.canvas_data = data.canvas_data.model_dump()
        # 递增版本号
        meta = arch.metadata_ or {}
        meta["version"] = meta.get("version", 1) + 1
        arch.metadata_ = meta

    db.commit()
    db.refresh(arch)
    return _to_detail(arch)


@router.delete("/{arch_id}", status_code=204)
def delete_architecture(arch_id: str, db: Session = Depends(get_db)):
    """删除架构。"""
    arch = db.query(Architecture).filter(Architecture.id == arch_id).first()
    if not arch:
        raise HTTPException(status_code=404, detail="Architecture not found")
    db.delete(arch)
    db.commit()


@router.post("/{arch_id}/duplicate", response_model=ArchitectureDetail, status_code=201)
def duplicate_architecture(arch_id: str, db: Session = Depends(get_db)):
    """复制架构。"""
    arch = db.query(Architecture).filter(Architecture.id == arch_id).first()
    if not arch:
        raise HTTPException(status_code=404, detail="Architecture not found")

    new_arch = Architecture(
        name=f"{arch.name} (copy)",
        description=arch.description,
        canvas_data=dict(arch.canvas_data) if arch.canvas_data else {},
        metadata_={"version": 1, "duplicated_from": arch_id},
    )
    db.add(new_arch)
    db.commit()
    db.refresh(new_arch)
    return _to_detail(new_arch)


def _to_detail(arch: Architecture) -> ArchitectureDetail:
    return ArchitectureDetail(
        id=arch.id,
        name=arch.name,
        description=arch.description or "",
        canvas_data=CanvasData(**arch.canvas_data) if arch.canvas_data else CanvasData(),
        metadata=arch.metadata_ or {},
        created_at=arch.created_at.isoformat() if arch.created_at else None,
        updated_at=arch.updated_at.isoformat() if arch.updated_at else None,
    )
