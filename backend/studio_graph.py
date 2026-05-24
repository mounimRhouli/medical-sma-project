"""LangGraph Studio entrypoint.

This file lets ``langgraph dev`` run from the backend directory while the
application keeps its project-root imports such as ``backend.app.graph``.

Two graph instances are exposed:
  - ``medical_graph``   : the main workflow (used by langgraph.json)
  - ``medical_graph_debug`` : same graph compiled with MemorySaver for
    standalone testing outside Studio (used by studio_demo.py)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from backend.app.graph import build_graph  # noqa: E402

medical_graph = build_graph().compile(
    interrupt_before=["physician_review"],
)

medical_graph_debug = build_graph().compile(
    checkpointer=MemorySaver(),
    interrupt_before=["physician_review"],
)
