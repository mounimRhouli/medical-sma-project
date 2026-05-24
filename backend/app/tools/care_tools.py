"""
Care Tools — Tools for generating intermediate care recommendations.
Uses MCP server to fetch relevant care guidelines, then Groq LLM to produce advice.
"""

from langchain_core.tools import tool
from langchain_groq import ChatGroq

from backend.app.config import get_groq_api_key, get_llm_model
from backend.app.tools.mcp_client import get_care_guidelines_sync

def _get_llm() -> ChatGroq:
    """Initialise le modèle Groq LLM."""
    return ChatGroq(
        model=get_llm_model(),
        api_key=get_groq_api_key(),
        temperature=0.3,
    )


@tool
def recommend_interim_care(diagnostic_summary: str) -> str:
    """
    Génère une recommandation intermédiaire de soins prudente.
    Appelle le serveur MCP pour récupérer les lignes directrices pertinentes.
    N'émet JAMAIS de diagnostic définitif.

    Args:
        diagnostic_summary: La synthèse clinique préliminaire

    Returns:
        Chaîne contenant la recommandation intermédiaire de soins
    """
    mcp_response = get_care_guidelines_sync(diagnostic_summary)

    guidelines_text = ""
    if mcp_response.get("guidelines"):
        for guideline in mcp_response["guidelines"]:
            guidelines_text += (
                f"- Condition: {guideline.get('condition', 'N/A')}\n"
                f"  Recommandations: {guideline.get('guidelines', 'N/A')}\n"
                f"  Urgence: {guideline.get('urgency', 'N/A')}\n"
                f"  Actions: {', '.join(guideline.get('recommended_actions', []))}\n\n"
            )
    else:
        guidelines_text = "Aucune ligne directrice spécifique trouvée dans la base MCP."

    prompt = (
        "Tu es un assistant médical académique. "
        "À partir de la synthèse clinique préliminaire suivante et des "
        "lignes directrices de soins, génère une recommandation intermédiaire "
        "prudente en français. "
        "N'émets AUCUN diagnostic définitif. "
        "Utilise uniquement le terme 'recommandation intermédiaire'. "
        "Les recommandations doivent être générales et prudentes : "
        "repos, hydratation, surveillance, consultation rapide en cas d'aggravation.\n\n"
        f"Synthèse clinique préliminaire:\n{diagnostic_summary}\n\n"
        f"Lignes directrices de soins (base MCP):\n{guidelines_text}\n\n"
        "Recommandation intermédiaire:"
    )

    try:
        llm = _get_llm()
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return (
            f"[Erreur LLM : {str(e)}] "
            "Recommandation intermédiaire par défaut : "
            "Repos, hydratation adéquate, surveillance des symptômes. "
            "En cas d'aggravation ou de persistance des symptômes, "
            "une consultation médicale rapide est recommandée. "
            "⚠️ Ce système ne remplace pas une consultation médicale."
        )
