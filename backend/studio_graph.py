"""LangGraph Studio entrypoint.

This file lets `langgraph dev` run from the backend directory while the
application keeps its project-root imports such as `backend.app.graph`.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.graph import build_graph  # noqa: E402

medical_graph = build_graph().compile(
    interrupt_before=["physician_review"],
)
