"""
FlowForge v0.1 - 数据库模型
Architecture, ExecutionRun, EvaluationRun, TestSet
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Architecture(Base):
    """架构配置 —— 画布定义的 Agent 协作模式。"""
    __tablename__ = "architectures"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_new_id)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    canvas_data = Column(JSONB, nullable=False, default=dict)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # 关系
    execution_runs = relationship("ExecutionRun", back_populates="architecture", cascade="all, delete-orphan")
    evaluation_runs = relationship("EvaluationRun", back_populates="architecture", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "canvas_data": self.canvas_data,
            "metadata": self.metadata_,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ExecutionRun(Base):
    """执行记录 —— 一次画布运行的全部信息。"""
    __tablename__ = "execution_runs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_new_id)
    architecture_id = Column(UUID(as_uuid=False), ForeignKey("architectures.id", ondelete="CASCADE"), nullable=True)
    status = Column(String(20), default="pending")  # pending | running | completed | failed
    input_data = Column(JSONB, default=dict)
    output_data = Column(JSONB, default=dict)
    total_latency_ms = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    node_events = Column(JSONB, default=list)
    error_message = Column(Text, default="")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    architecture = relationship("Architecture", back_populates="execution_runs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "architecture_id": self.architecture_id,
            "status": self.status,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "total_latency_ms": self.total_latency_ms,
            "total_tokens": self.total_tokens,
            "node_events": self.node_events,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class EvaluationRun(Base):
    """评估运行 —— 一次架构评测的汇总与详情。"""
    __tablename__ = "evaluation_runs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_new_id)
    architecture_id = Column(UUID(as_uuid=False), ForeignKey("architectures.id", ondelete="CASCADE"), nullable=True)
    testset_name = Column(String(255), default="")
    status = Column(String(20), default="pending")
    summary = Column(JSONB, default=dict)
    detail_results = Column(JSONB, default=list)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    architecture = relationship("Architecture", back_populates="evaluation_runs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "architecture_id": self.architecture_id,
            "testset_name": self.testset_name,
            "status": self.status,
            "summary": self.summary,
            "detail_results": self.detail_results,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class TestSet(Base):
    """测试集 —— 黄金测试用例合集。"""
    __tablename__ = "test_sets"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_new_id)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    test_cases = Column(JSONB, default=list)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "test_cases": self.test_cases,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
