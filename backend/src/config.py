"""
FlowForge v0.1 - 配置模块
从环境变量加载配置，提供默认值。
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ==================== 数据库 ====================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:zyx2003@localhost:5432/flowforge",
)

# ==================== LLM / DeepSeek API ====================
ANTHROPIC_BASE_URL = os.getenv(
    "ANTHROPIC_BASE_URL",
    "https://api.deepseek.com/anthropic",
)
ANTHROPIC_API_KEY = os.getenv(
    "ANTHROPIC_API_KEY",
    os.getenv("ANTHROPIC_API_KEY", ""),
)
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "deepseek-v4-pro")

# ==================== 应用 ====================
APP_TITLE = "FlowForge API"
APP_VERSION = "0.1.0"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ==================== 执行 ====================
EXECUTION_TIMEOUT_SECONDS = int(os.getenv("EXECUTION_TIMEOUT", "300"))
MAX_RETRIES_PER_NODE = int(os.getenv("MAX_RETRIES_PER_NODE", "2"))
