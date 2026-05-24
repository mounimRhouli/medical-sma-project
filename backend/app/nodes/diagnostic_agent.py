"""
Diagnostic Agent Node — Collects patient information through 5 mandatory questions,
then generates a preliminary clinical summary using Groq LLM.
"""

from langchain_core.messages import AIMessage, SystemMessage
from langchain_groq import ChatGroq

from backend.app.config import get_groq_api_key, get_llm_model
from backend.app.state import MedicalState
from backend.app.tools.patient_tools import ask_patient, record_patient_answer
from backend.app.tools.care_tools import recommend_interim_care

MANDATORY_QUESTIONS = [
    "Quel est votre symptôme principal ou motif de consultation ?",
    "Depuis combien de temps ressentez-vous ces symptômes ?",
    "Sur une échelle de 1 à 10, comment évaluez-vous l'intensité de votre douleur ou gêne ?",
    "Avez-vous des antécédents médicaux importants ou des allergies connues ?",
    "Prenez-vous actuellement des médicaments ? Si oui, lesquels ?",
]


def _get_llm() -> ChatGroq:
    """Initialise le modèle Groq LLM."""
    return ChatGroq(
        model=get_llm_model(),
        api_key=get_groq_api_key(),
        temperature=0.3,
    )


def _generate_diagnostic_summary(qa_pairs: list) -> str:
    """
    Génère une synthèse clinique préliminaire à partir des réponses patient.
    N'émet AUCUN diagnostic définitif.
    """
    qa_text = "\n".join(
        [f"Q{i+1}: {qa['question']}\nR{i+1}: {qa['answer']}" for i, qa in enumerate(qa_pairs)]
    )

    prompt = (
        "Tu es un assistant médical académique. "
        "À partir des réponses suivantes d'un patient fictif, rédige une "
        "synthèse clinique préliminaire structurée en français. "
        "N'émets AUCUN diagnostic définitif. "
        "Utilise uniquement le terme 'orientation clinique préliminaire'.\n\n"
        f"Réponses patient:\n{qa_text}\n\n"
        "Synthèse clinique préliminaire:"
    )

    try:
        llm = _get_llm()
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return (
            f"[Erreur lors de la génération de la synthèse clinique préliminaire : {str(e)}] "
            "Une synthèse clinique préliminaire n'a pas pu être générée automatiquement. "
            "Veuillez consulter les réponses du patient directement."
        )


def diagnostic_agent_node(state: MedicalState) -> dict:
    """
    Nœud de l'agent d'orientation clinique préliminaire.

    Phase 1 (question_count < 5) :
      - Pose la prochaine question au patient
      - Incrémente le compteur de questions
      - Retourne l'état mis à jour (attend la réponse via API)

    Phase 2 (question_count == 5, toutes les réponses collectées) :
      - Génère la synthèse clinique préliminaire via LLM
      - Appelle recommend_interim_care pour les recommandations intermédiaires
      - Met à jour le statut vers "awaiting_physician"
    """
    question_count = state.get("question_count", 0)
    questions_and_answers = state.get("questions_and_answers", [])

    if question_count < 5:
        current_question = MANDATORY_QUESTIONS[question_count]
        formatted_question = ask_patient.invoke(
            {"question": current_question, "question_number": question_count + 1}
        )

        question_message = AIMessage(
            content=f"🩺 {formatted_question}"
        )

        return {
            "current_question": current_question,
            "question_count": question_count + 1,
            "consultation_status": "questioning",
            "messages": [question_message],
        }

    if question_count >= 5 and len(questions_and_answers) >= 5:
        for i, qa in enumerate(questions_and_answers):
            record_patient_answer.invoke({
                "question": qa["question"],
                "answer": qa["answer"],
                "question_number": i + 1,
            })

        diagnostic_summary = _generate_diagnostic_summary(questions_and_answers)

        try:
            interim_care = recommend_interim_care.invoke(
                {"diagnostic_summary": diagnostic_summary}
            )
        except Exception as e:
            interim_care = (
                f"[Erreur lors de la génération des recommandations : {str(e)}] "
                "Recommandations générales : repos, hydratation, surveillance des symptômes. "
                "Consultez un professionnel de santé en cas d'aggravation."
            )

        summary_message = SystemMessage(
            content=(
                f"[Agent d'orientation clinique préliminaire] "
                f"Synthèse clinique préliminaire générée. "
                f"Recommandation intermédiaire produite. "
                f"En attente de la revue du médecin traitant."
            )
        )

        return {
            "diagnostic_summary": diagnostic_summary,
            "interim_care": interim_care,
            "consultation_status": "awaiting_physician",
            "messages": [summary_message],
        }

    waiting_message = AIMessage(
        content="En attente des réponses du patient pour compléter le questionnaire."
    )
    return {
        "messages": [waiting_message],
    }
