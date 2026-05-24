"""
Supervisor Node — Deterministic routing logic for the medical workflow.
Routes to the next agent based on current state, no LLM needed.
"""

from langchain_core.messages import SystemMessage
from backend.app.state import MedicalState


def supervisor_node(state: MedicalState) -> dict:
    """
    Nœud superviseur : détermine le prochain agent à exécuter
    en fonction de l'état actuel de la consultation.

    Logique de routage :
      1. Si le rapport final existe → FINISH
      2. Si le médecin a fourni son avis → report_agent
      3. Si les 5 questions sont posées et la synthèse est faite → physician_review
      4. Si une question vient d'être posée → FINISH temporaire
      5. Sinon → diagnostic_agent
    """
    final_report = state.get("final_report", "")
    physician_treatment = state.get("physician_treatment", "")
    question_count = state.get("question_count", 0)
    questions_and_answers = state.get("questions_and_answers", [])
    diagnostic_summary = state.get("diagnostic_summary", "")

    if final_report:
        next_node = "FINISH"
        consultation_status = "completed"
        routing_reason = "Rapport final généré. Consultation terminée."
    elif physician_treatment:
        next_node = "report_agent"
        consultation_status = "report_generated"
        routing_reason = "Avis médecin reçu. Génération du rapport final."
    elif question_count >= 5 and diagnostic_summary:
        next_node = "physician_review"
        consultation_status = "awaiting_physician"
        routing_reason = "Synthèse clinique préliminaire complétée. En attente de la revue médecin."
    elif question_count > len(questions_and_answers):
        next_node = "FINISH"
        consultation_status = "questioning"
        routing_reason = "Question posée. En attente de la réponse patient."
    else:
        next_node = "diagnostic_agent"
        consultation_status = "questioning" if question_count > 0 else "started"
        routing_reason = f"Poursuite du questionnaire patient (question {question_count + 1}/5)."

    supervisor_message = SystemMessage(
        content=f"[Superviseur] Routage → {next_node} | Raison : {routing_reason}"
    )

    return {
        "next": next_node,
        "consultation_status": consultation_status,
        "messages": [supervisor_message],
    }
