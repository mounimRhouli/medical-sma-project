"""
FastAPI API — Medical Clinical Orientation Workflow REST API.
Provides 6 endpoints for managing medical consultations with the multi-agent system.
"""

import logging
import uuid
import os
import time
import functools
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv(override=True)

from backend.app.logging_config import setup_logging  # noqa: E402
setup_logging()

from backend.app.graph import medical_graph  # noqa: E402
from backend.app.state import MedicalState  # noqa: E402
from backend.app.nodes.diagnostic_agent import MANDATORY_QUESTIONS  # noqa: E402
from backend.app.database import init_db, get_consultation as db_get_consultation, get_all_consultations  # noqa: E402
from backend.app.exceptions import (  # noqa: E402
    SMABaseError,
    ConsultationNotFoundError,
    ReportNotReadyError,
    GraphExecutionError,
)

logger = logging.getLogger(__name__)

init_db()

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


@app.exception_handler(SMABaseError)
async def sma_exception_handler(request: Request, exc: SMABaseError):
    """Global handler for all custom SMA exceptions."""
    status_map = {
        "CONSULTATION_NOT_FOUND": 404,
        "REPORT_NOT_READY": 404,
        "CONSULTATION_EXISTS": 409,
        "VALIDATION_ERROR": 422,
        "LLM_ERROR": 502,
        "MCP_UNAVAILABLE": 503,
        "GRAPH_EXECUTION_ERROR": 500,
        "DATABASE_ERROR": 500,
    }
    status_code = status_map.get(exc.error_code, 500)
    logger.error("SMA Error [%s]: %s", exc.error_code, exc.message)
    return JSONResponse(status_code=status_code, content=exc.to_dict())


def retry_on_failure(max_retries: int = 2, delay: float = 1.0):
    """Decorator that retries a function on transient failures."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError, OSError) as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(
                            "Tentative %d/%d échouée pour %s : %s",
                            attempt + 1, max_retries + 1, func.__name__, e,
                        )
                        time.sleep(delay * (attempt + 1))
            raise last_error
        return wrapper
    return decorator

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
        for event in medical_graph.stream(initial_state, config=config):
            pass

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
        logger.error("Erreur démarrage consultation %s: %s", request.thread_id, e)
        raise GraphExecutionError("démarrage de la consultation", str(e))


@app.post("/consultation/resume")
async def resume_consultation(request: ConsultationResumeRequest):
    """
    Reprend une consultation en cours.
    Gère les réponses du patient (via mise à jour du graphe + re-streaming)
    et les avis du médecin (via reprise HITL du graphe interrompu).
    """
    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        current_state = API_SESSION_STATES.get(request.thread_id)
        if not current_state:
            state = medical_graph.get_state(config)
            current_state = state.values if state else None

        if not current_state:
            raise ConsultationNotFoundError(request.thread_id)

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
                state_update = {
                    "messages": [answer_message],
                    "questions_and_answers": questions_and_answers,
                    "question_count": next_question_count,
                    "current_question": next_question,
                    "consultation_status": "questioning",
                }
                medical_graph.update_state(config, state_update, as_node="diagnostic_agent")
                new_state = dict(current_state)
                new_state.update(state_update)
                API_SESSION_STATES[request.thread_id] = new_state
            else:
                state_update = {
                    "messages": [answer_message],
                    "questions_and_answers": questions_and_answers,
                    "question_count": 5,
                }
                medical_graph.update_state(config, state_update, as_node="supervisor")

                for event in medical_graph.stream(None, config=config):
                    pass

                graph_state = medical_graph.get_state(config)
                new_state = dict(graph_state.values)
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

            medical_graph.update_state(
                config,
                {
                    "messages": [physician_message],
                    "physician_treatment": request.answer,
                },
                as_node="physician_review",
            )

            for event in medical_graph.stream(None, config=config):
                pass

            graph_state = medical_graph.get_state(config)
            new_state = dict(graph_state.values)
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

    except (SMABaseError, HTTPException):
        raise
    except Exception as e:
        logger.error("Erreur reprise consultation %s: %s", request.thread_id, e)
        raise GraphExecutionError("reprise de la consultation", str(e))


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
            raise ConsultationNotFoundError(thread_id)

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
    except SMABaseError:
        raise
    except Exception as e:
        logger.error("Erreur récupération état %s: %s", thread_id, e)
        raise GraphExecutionError("récupération de l'état", str(e))


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
            raise ConsultationNotFoundError(thread_id)

        final_report = current_state.get("final_report", "")

        if not final_report:
            raise ReportNotReadyError(thread_id)

        return {
            "thread_id": thread_id,
            "status": "completed",
            "final_report": final_report,
            "final_report_json": current_state.get("final_report_json", {}),
            "disclaimer": "⚠️ Ce système ne remplace pas une consultation médicale.",
        }
    except SMABaseError:
        raise
    except Exception as e:
        logger.error("Erreur récupération rapport %s: %s", thread_id, e)
        raise GraphExecutionError("récupération du rapport", str(e))


@app.get("/consultations/history")
async def get_consultations_history():
    """
    Retourne l'historique de toutes les consultations (base SQLite).
    """
    try:
        consultations = get_all_consultations()
        return {
            "status": "success",
            "total": len(consultations),
            "consultations": consultations,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la r\u00e9cup\u00e9ration de l'historique : {str(e)}",
        )


@app.get("/consultations/history/{thread_id}")
async def get_consultation_history(thread_id: str):
    """
    Retourne les d\u00e9tails d'une consultation archiv\u00e9e en base SQLite.
    """
    try:
        consultation = db_get_consultation(thread_id)
        if not consultation:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune consultation archiv\u00e9e pour le thread_id : {thread_id}",
            )
        return {"status": "success", "consultation": consultation}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la r\u00e9cup\u00e9ration de la consultation : {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("FASTAPI_HOST", "0.0.0.0")
    port = int(os.getenv("FASTAPI_PORT", "8000"))
    uvicorn.run("backend.app.api:app", host=host, port=port, reload=True)
