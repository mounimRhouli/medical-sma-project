"""
Report Agent Node — Generates the final structured clinical report
using Groq LLM, with Pydantic structured output.
"""

import json
import os
from datetime import datetime
from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq

from backend.app.config import get_groq_api_key, get_llm_model
from backend.app.state import MedicalState, FinalReportModel
from backend.app.database import save_consultation

import logging

logger = logging.getLogger(__name__)

def _get_llm() -> ChatGroq:
    """Initialise le modèle Groq LLM."""
    return ChatGroq(
        model=get_llm_model(),
        api_key=get_groq_api_key(),
        temperature=0.3,
    )


def _generate_conclusion(
    diagnostic_summary: str,
    interim_care: str,
    physician_treatment: str,
) -> str:
    """
    Génère une conclusion générale via LLM.
    N'émet AUCUN diagnostic définitif.
    """
    prompt = (
        "Tu es un assistant médical académique. "
        "À partir des éléments suivants, rédige une conclusion générale "
        "en français pour un rapport clinique académique. "
        "N'émets AUCUN diagnostic définitif. "
        "Utilise les termes 'orientation clinique préliminaire' et "
        "'recommandation intermédiaire'. "
        "La conclusion doit être prudente et rappeler la nécessité "
        "d'une consultation médicale professionnelle.\n\n"
        f"Synthèse clinique préliminaire:\n{diagnostic_summary}\n\n"
        f"Recommandation intermédiaire:\n{interim_care}\n\n"
        f"Avis du médecin traitant:\n{physician_treatment}\n\n"
        "Conclusion générale:"
    )

    try:
        llm = _get_llm()
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return (
            f"[Erreur lors de la génération de la conclusion : {str(e)}] "
            "Conclusion générale : Sur la base de l'orientation clinique préliminaire "
            "et de la recommandation intermédiaire, une consultation médicale "
            "professionnelle est vivement recommandée pour un suivi adapté."
        )


def _format_report(
    patient_info: dict,
    questions_and_answers: list,
    diagnostic_summary: str,
    interim_care: str,
    physician_treatment: str,
    conclusion: str,
) -> str:
    """Formate le rapport clinique final en texte structuré."""
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")

    qa_section = ""
    for i, qa in enumerate(questions_and_answers):
        qa_section += f"     Q{i+1}: {qa.get('question', '')} → R: {qa.get('answer', '')}\n"

    report = (
        "══════════════════════════════════════════════════\n"
        "RAPPORT CLINIQUE FINAL — SYSTÈME MULTI-AGENTS SMA\n"
        "══════════════════════════════════════════════════\n\n"
        "  1. INFORMATIONS PATIENT\n"
        f"     Nom: {patient_info.get('name', 'Inconnu')}  |  "
        f"Âge: {patient_info.get('age', 0)}  |  Date: {date_str}\n"
        f"     Motif initial: {patient_info.get('initial_case', 'Non spécifié')}\n\n"
        "  2. ANAMNÈSE — QUESTIONS & RÉPONSES\n"
        f"{qa_section}\n"
        "  3. SYNTHÈSE CLINIQUE PRÉLIMINAIRE\n"
        f"     {diagnostic_summary}\n\n"
        "  4. RECOMMANDATION INTERMÉDIAIRE\n"
        f"     {interim_care}\n\n"
        "  5. AVIS DU MÉDECIN TRAITANT\n"
        f"     {physician_treatment}\n\n"
        "  6. CONCLUSION GÉNÉRALE\n"
        f"     {conclusion}\n\n"
        "  7. AVERTISSEMENT LÉGAL\n"
        "     ⚠️ Ce système ne remplace pas une consultation médicale.\n"
        "     Ce rapport est produit dans le cadre d'un exercice académique.\n"
        "     Il ne constitue pas un avis médical professionnel.\n"
        "══════════════════════════════════════════════════\n"
    )
    return report


def _save_consultation_history(report_json: dict, thread_id: str) -> None:
    """Sauvegarde l'historique de la consultation dans la base SQLite."""
    try:
        save_consultation(thread_id, report_json)
        logger.info("Consultation %s sauvegardée en base de données.", thread_id)
    except Exception as e:
        logger.error("Erreur lors de la sauvegarde en base : %s", e)


def report_agent_node(state: MedicalState) -> dict:
    """
    Nœud de génération du rapport clinique final.

    Utilise le LLM Groq pour générer une conclusion générale,
    puis formate le rapport complet avec les 7 sections obligatoires.
    Stocke le rapport en format texte et en format structuré Pydantic.
    Sauvegarde l'historique de consultation.
    """
    patient_info = state.get("patient_info", {})
    questions_and_answers = state.get("questions_and_answers", [])
    diagnostic_summary = state.get("diagnostic_summary", "")
    interim_care = state.get("interim_care", "")
    physician_treatment = state.get("physician_treatment", "")
    thread_id = state.get("thread_id", "unknown")

    conclusion = _generate_conclusion(
        diagnostic_summary, interim_care, physician_treatment
    )

    final_report = _format_report(
        patient_info=patient_info,
        questions_and_answers=questions_and_answers,
        diagnostic_summary=diagnostic_summary,
        interim_care=interim_care,
        physician_treatment=physician_treatment,
        conclusion=conclusion,
    )

    final_report_model = FinalReportModel(
        patient_info=patient_info,
        questions_and_answers=questions_and_answers,
        diagnostic_summary=diagnostic_summary,
        interim_care=interim_care,
        physician_treatment=physician_treatment,
        conclusion=conclusion,
        disclaimer="⚠️ Ce système ne remplace pas une consultation médicale.",
    )

    final_report_json = final_report_model.model_dump()

    _save_consultation_history(final_report_json, thread_id)

    report_message = SystemMessage(
        content=(
            "[Agent de rapport] Rapport clinique final généré avec succès. "
            "Consultation terminée."
        )
    )

    return {
        "final_report": final_report,
        "final_report_json": final_report_json,
        "consultation_status": "completed",
        "messages": [report_message],
    }
