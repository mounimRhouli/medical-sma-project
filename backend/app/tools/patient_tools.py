"""
Patient Tools — Tools used by the DiagnosticAgent to collect patient information.
"""

from langchain_core.tools import tool


@tool
def ask_patient(question: str, question_number: int) -> str:
    """
    Formate et retourne une question clinique à poser au patient.
    Utilisé par l'agent d'orientation clinique préliminaire pour
    collecter les informations du patient.

    Args:
        question: Le texte de la question clinique
        question_number: L'index de la question (1-5)

    Returns:
        Chaîne de caractères formatée pour l'affichage
    """
    return f"[Question {question_number}/5] {question}"


@tool
def record_patient_answer(question: str, answer: str, question_number: int) -> dict:
    """
    Enregistre la réponse d'un patient et retourne une paire QA structurée.

    Args:
        question: La question posée au patient
        answer: La réponse du patient
        question_number: Le numéro de la question (1-5)

    Returns:
        Dictionnaire contenant la question, la réponse et le numéro
    """
    return {
        "question": question,
        "answer": answer,
        "number": question_number,
    }
