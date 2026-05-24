"""
FastAPI API — Medical Clinical Orientation Workflow REST API.
Provides 6 endpoints for managing medical consultations with the multi-agent system.
"""

import uuid
import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv(override=True)

from backend.app.graph import medical_graph, checkpointer
from backend.app.state import MedicalState
from backend.app.nodes.diagnostic_agent import MANDATORY_QUESTIONS, diagnostic_agent_node
from backend.app.nodes.report_agent import report_agent_node

app = FastAPI(
    title="SMA Clinique — API d'Orientation Médicale Simulée",
    description=(
        "API REST pour le système multi-agents d'orientation clinique préliminaire. "
        "⚠️ Ce système ne remplace pas une consultation médicale."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_SESSION_STATES: dict[str, MedicalState] = {}


class ConsultationStartRequest(BaseModel):
    """Requête pour démarrer une consultation."""
    thread_id: str = Field(..., min_length=1, description="Identifiant de session")
    patient_name: str = Field(..., min_length=1, description="Nom du patient")
    patient_age: int = Field(..., ge=1, le=120, description="Âge du patient")
    initial_case: str = Field(..., min_length=10, description="Description du cas initial")


class ConsultationResumeRequest(BaseModel):
    """Requête pour reprendre une consultation."""
    thread_id: str = Field(..., min_length=1, description="Identifiant de session")
    answer: str = Field(..., min_length=1, description="Réponse du patient ou avis du médecin")
    role: str = Field(..., pattern="^(patient|physician)$", description="Rôle de l'intervenant")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("patient", "physician"):
            raise ValueError("Le rôle doit être 'patient' ou 'physician'")
        return v


@app.get("/health")
async def health_check():
    """Vérifie l'état de santé de l'API."""
    return {"status": "ok", "service": "Medical Multi-Agent API"}


@app.post("/sessions/start")
async def start_session():
    """
    Crée une nouvelle session de consultation.
    Retourne un thread_id unique pour identifier la session.
    """
    thread_id = str(uuid.uuid4())
    return {
        "thread_id": thread_id,
        "status": "created",
        "message": "Session créée. Appelez /consultation/start pour démarrer.",
    }


@app.post("/consultation/start")
async def start_consultation(request: ConsultationStartRequest):
    """
    Démarre une consultation médicale.
    Initialise l'état du graphe et retourne la première question au patient.
    """
    config = {"configurable": {"thread_id": request.thread_id}}

    initial_state: MedicalState = {
        "messages": [
            HumanMessage(
                content=(
                    f"Nouvelle consultation pour le patient {request.patient_name}, "
                    f"{request.patient_age} ans. "
                    f"Motif de consultation : {request.initial_case}"
                )
            )
        ],
        "patient_info": {
            "name": request.patient_name,
            "age": request.patient_age,
            "initial_case": request.initial_case,
        },
        "question_count": 0,
        "questions_and_answers": [],
        "current_question": "",
        "diagnostic_summary": "",
        "interim_care": "",
        "physician_treatment": "",
        "final_report": "",
        "final_report_json": {},
        "consultation_status": "started",
        "thread_id": request.thread_id,
        "error": None,
    }

    try:
        result = None
        for event in medical_graph.stream(initial_state, config=config):
            result = event

        state = medical_graph.get_state(config)
        current_state = state.values
        API_SESSION_STATES[request.thread_id] = dict(current_state)

        return {
            "thread_id": request.thread_id,
            "status": "questioning",
            "question_number": current_state.get("question_count", 1),
            "question": current_state.get("current_question", ""),
            "total_questions": 5,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du démarrage de la consultation : {str(e)}",
        )


@app.post("/consultation/resume")
async def resume_consultation(request: ConsultationResumeRequest):
    """
    Reprend une consultation en cours.
    Gère les réponses du patient et les avis du médecin.
    """
    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        current_state = API_SESSION_STATES.get(request.thread_id)
        if not current_state:
            state = medical_graph.get_state(config)
            current_state = state.values if state else None

        if not current_state:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune consultation trouvée pour le thread_id : {request.thread_id}",
            )

        if request.role == "patient":
            question_count = current_state.get("question_count", 0)
            questions_and_answers = list(current_state.get("questions_and_answers", []))
            current_question = current_state.get("current_question", "")

            questions_and_answers.append({
                "question": current_question,
                "answer": request.answer,
            })

            answer_message = HumanMessage(
                content=f"[Réponse patient Q{question_count}] {request.answer}"
            )

            if len(questions_and_answers) < 5:
                next_question_count = len(questions_and_answers) + 1
                next_question = MANDATORY_QUESTIONS[len(questions_and_answers)]
                new_state = dict(current_state)
                new_state.update(
                    {
                        "messages": [answer_message],
                        "questions_and_answers": questions_and_answers,
                        "question_count": next_question_count,
                        "current_question": next_question,
                        "consultation_status": "questioning",
                    }
                )
                API_SESSION_STATES[request.thread_id] = new_state
            else:
                diagnostic_state = dict(current_state)
                diagnostic_state.update(
                    {
                        "messages": [answer_message],
                        "questions_and_answers": questions_and_answers,
                        "question_count": 5,
                    }
                )
                diagnostic_result = diagnostic_agent_node(diagnostic_state)
                new_state = dict(diagnostic_state)
                new_state.update(
                    {
                        "messages": diagnostic_result.get("messages", []),
                        "questions_and_answers": questions_and_answers,
                        "question_count": 5,
                        "diagnostic_summary": diagnostic_result.get("diagnostic_summary", ""),
                        "interim_care": diagnostic_result.get("interim_care", ""),
                        "consultation_status": diagnostic_result.get(
                            "consultation_status", "awaiting_physician"
                        ),
                    }
                )
                API_SESSION_STATES[request.thread_id] = new_state

            if new_state.get("consultation_status") == "awaiting_physician":
                return {
                    "thread_id": request.thread_id,
                    "status": "awaiting_physician",
                    "diagnostic_summary": new_state.get("diagnostic_summary", ""),
                    "interim_care": new_state.get("interim_care", ""),
                    "message": "Synthèse générée. En attente de la revue du médecin.",
                }

            return {
                "thread_id": request.thread_id,
                "status": "questioning",
                "question_number": new_state.get("question_count", 0),
                "question": new_state.get("current_question", ""),
                "total_questions": 5,
            }

        elif request.role == "physician":
            physician_message = HumanMessage(
                content=f"[Avis médecin] {request.answer}"
            )

            report_state = dict(current_state)
            report_state.update(
                {
                    "messages": [physician_message],
                    "physician_treatment": request.answer,
                }
            )
            report_result = report_agent_node(report_state)

            new_state = dict(report_state)
            new_state.update(report_result)
            API_SESSION_STATES[request.thread_id] = new_state

            if new_state.get("final_report"):
                return {
                    "thread_id": request.thread_id,
                    "status": "completed",
                    "message": "Rapport final généré avec succès.",
                }

            return {
                "thread_id": request.thread_id,
                "status": "report_generating",
                "message": "Avis médecin enregistré. Génération du rapport final...",
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la reprise de la consultation : {str(e)}",
        )


@app.get("/consultation/{thread_id}")
async def get_consultation_status(thread_id: str):
    """
    Retourne l'état actuel complet de la consultation.
    """
    config = {"configurable": {"thread_id": thread_id}}

    try:
        current_state = API_SESSION_STATES.get(thread_id)
        if not current_state:
            state = medical_graph.get_state(config)
            current_state = state.values if state else None

        if not current_state:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune consultation trouvée pour le thread_id : {thread_id}",
            )

        return {
            "thread_id": thread_id,
            "consultation_status": current_state.get("consultation_status", "unknown"),
            "question_count": current_state.get("question_count", 0),
            "questions_and_answers": current_state.get("questions_and_answers", []),
            "diagnostic_summary": current_state.get("diagnostic_summary", ""),
            "interim_care": current_state.get("interim_care", ""),
            "physician_treatment": current_state.get("physician_treatment", ""),
            "has_final_report": bool(current_state.get("final_report")),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération de l'état : {str(e)}",
        )


@app.get("/consultation/{thread_id}/report")
async def get_consultation_report(thread_id: str):
    """
    Retourne le rapport final de la consultation.
    Retourne 404 si le rapport n'est pas encore généré.
    """
    config = {"configurable": {"thread_id": thread_id}}

    try:
        current_state = API_SESSION_STATES.get(thread_id)
        if not current_state:
            state = medical_graph.get_state(config)
            current_state = state.values if state else None

        if not current_state:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune consultation trouvée pour le thread_id : {thread_id}",
            )

        final_report = current_state.get("final_report", "")

        if not final_report:
            raise HTTPException(
                status_code=404,
                detail="Le rapport final n'est pas encore généré pour cette consultation.",
            )

        return {
            "thread_id": thread_id,
            "status": "completed",
            "final_report": final_report,
            "final_report_json": current_state.get("final_report_json", {}),
            "disclaimer": "⚠️ Ce système ne remplace pas une consultation médicale.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération du rapport : {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("FASTAPI_HOST", "0.0.0.0")
    port = int(os.getenv("FASTAPI_PORT", "8000"))
    uvicorn.run("backend.app.api:app", host=host, port=port, reload=True)
