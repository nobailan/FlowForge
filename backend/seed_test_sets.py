"""
FlowForge v0.7 — 测试集一键导入
将 evaluation/ 目录下所有 testset_*.json 导入数据库。

用法:
    python seed_test_sets.py
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.database import SessionLocal, init_db
from src.models import TestSet

TESTSET_DIR = os.path.join(os.path.dirname(__file__), "..", "evaluation")


def seed():
    init_db()
    db = SessionLocal()

    count = 0
    for fname in sorted(os.listdir(TESTSET_DIR)):
        if not fname.startswith("testset_") or not fname.endswith(".json"):
            continue

        path = os.path.join(TESTSET_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        name = data.get("name", fname)
        description = data.get("description", "")
        test_cases = data.get("test_cases", [])

        # 检查是否已存在
        existing = db.query(TestSet).filter(TestSet.name == name).first()
        if existing:
            print(f"  SKIP (exists): {name}")
            continue

        ts = TestSet(name=name, description=description, test_cases=test_cases)
        db.add(ts)
        db.commit()
        print(f"  CREATED: {name} ({len(test_cases)} questions) — {description}")
        count += 1

    print(f"\nDone. {count} test sets imported.")
    db.close()


if __name__ == "__main__":
    seed()
