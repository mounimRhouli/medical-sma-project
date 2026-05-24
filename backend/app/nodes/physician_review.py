"""
Physician Review Node — Human-in-the-Loop (HITL) interruption point.
The graph pauses before this node (interrupt_before=["physician_review"]).
The physician's input is injected via the API resume endpoint.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from backend.app.state import MedicalState


def physician_review_node(state: MedicalState) -> dict:
    """
    Nœud de revue médecin (Human-in-the-Loop).

    Ce nœud est le point d'interruption HITL du workflow.
    Le graphe est compilé avec interrupt_before=["physician_review"],
    ce qui signifie qu'il se met en PAUSE automatiquement avant l'exécution
    de ce nœud.

    L'entrée du médecin est injectée dans state["physician_treatment"]
    par l'appel API POST /consultation/resume avec role="physician".

    Ce nœud :
      1. Lit le traitement/conduite à tenir du médecin
      2. Formate et ajoute la revue médicale aux messages
      3. Met à jour le statut de la consultation
    """
    patient_info = state.get("patient_info", {})
    diagnostic_summary = state.get("diagnostic_summary", "")
    interim_care = state.get("interim_care", "")
    physician_treatment = state.get("physician_treatment", "")

    patient_name = patient_info.get("name", "Inconnu")
    patient_age = patient_info.get("age", 0)
    initial_case = patient_info.get("initial_case", "Non spécifié")

    review_display = (
        "\n══════════════════════════════════════\n"
        "REVUE MÉDECIN — Action requise\n"
        "══════════════════════════════════════\n"
        f"Patient: {patient_name}, {patient_age} ans\n"
        f"Cas initial: {initial_case}\n\n"
        "SYNTHÈSE CLINIQUE PRÉLIMINAIRE:\n"
        f"{diagnostic_summary}\n\n"
        "RECOMMANDATION INTERMÉDIAIRE:\n"
        f"{interim_care}\n\n"
        "→ Le médecin doit saisir son traitement ou conduite à tenir.\n"
        "══════════════════════════════════════\n"
    )

    if physician_treatment:
        physician_message = HumanMessage(
            content=(
                f"[Revue Médecin] Avis du médecin traitant :\n"
                f"{physician_treatment}"
            )
        )
        status_message = SystemMessage(
            content=(
                "[Système] Avis du médecin enregistré. "
                "Passage à la génération du rapport final."
            )
        )
        return {
            "consultation_status": "report_generated",
            "messages": [physician_message, status_message],
        }

    display_message = SystemMessage(content=review_display)
    return {
        "consultation_status": "awaiting_physician",
        "messages": [display_message],
    }
