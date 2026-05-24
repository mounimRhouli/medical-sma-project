"""
Shared state definitions for the Medical Clinical Orientation Workflow.
Defines MedicalState (TypedDict) used by all LangGraph nodes,
plus Pydantic models for structured data exchange.
"""

from typing import Annotated, List, Optional
from typing_extensions import TypedDict, Literal
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class QuestionAnswer(BaseModel):
    """Représente une paire question-réponse du questionnaire patient."""
    question: str
    answer: str


class PatientInfo(BaseModel):
    """Informations de base du patient."""
    name: str = ""
    age: int = 0
    initial_case: str = ""


class FinalReportModel(BaseModel):
    """Modèle structuré du rapport clinique final."""
    patient_info: dict = Field(default_factory=dict)
    questions_and_answers: List[dict] = Field(default_factory=list)
    diagnostic_summary: str = ""
    interim_care: str = ""
    physician_treatment: str = ""
    conclusion: str = ""
    disclaimer: str = "⚠️ Ce système ne remplace pas une consultation médicale."


class MedicalState(TypedDict, total=False):
    """État partagé du workflow médical multi-agents."""
    messages: Annotated[list, add_messages]
    next: Literal["diagnostic_agent", "physician_review", "report_agent", "FINISH"]
    patient_info: dict
    question_count: int
    questions_and_answers: List[dict]
    current_question: str
    diagnostic_summary: str
    interim_care: str
    physician_treatment: str
    final_report: str
    final_report_json: dict
    consultation_status: Literal[
        "started", "questioning",
        "awaiting_physician", "report_generated", "completed"
    ]
    thread_id: str
    error: Optional[str]
