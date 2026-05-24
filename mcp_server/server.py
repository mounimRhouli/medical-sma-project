"""
MCP Care Guidelines Server — Standalone FastAPI-based server
providing clinical care guidelines for the multi-agent system.
"""

import os
import json
from typing import List, Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(
    title="MCP Care Guidelines Server",
    description="Serveur de lignes directrices de soins pour le système multi-agents médical.",
    version="1.0.0",
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
GUIDELINES_FILE = os.path.join(DATA_DIR, "care_guidelines.json")


def _load_guidelines() -> list:
    """Charge les lignes directrices depuis le fichier JSON."""
    try:
        with open(GUIDELINES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Erreur lors du chargement des lignes directrices : {e}")
        return []


def _tokenize(text: str) -> set:
    """Tokenise un texte en mots clés normalisés."""
    import re
    text = text.lower()
    text = re.sub(r"[^\w\sàâäéèêëïîôùûüÿçœæ]", " ", text)
    tokens = set(text.split())
    stop_words = {
        "le", "la", "les", "de", "du", "des", "un", "une", "et", "ou",
        "en", "à", "au", "aux", "ce", "ces", "mon", "ma", "mes",
        "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
        "est", "sont", "a", "ai", "ont", "être", "avoir",
        "que", "qui", "quoi", "dont", "où", "par", "pour", "avec",
        "sur", "dans", "ne", "pas", "plus", "très", "bien",
    }
    return tokens - stop_words


def _match_guidelines(symptoms: str, guidelines: list) -> list:
    """
    Fait correspondre les symptômes aux lignes directrices par
    chevauchement de mots clés. Retourne les résultats triés
    par score de correspondance décroissant.
    """
    symptom_tokens = _tokenize(symptoms)
    scored_guidelines = []

    for guideline in guidelines:
        keywords = set(k.lower() for k in guideline.get("keywords", []))
        condition_tokens = _tokenize(guideline.get("condition", ""))
        all_keywords = keywords | condition_tokens

        overlap = symptom_tokens & all_keywords
        score = len(overlap)

        partial_score = 0
        for symptom_token in symptom_tokens:
            for keyword in all_keywords:
                if symptom_token in keyword or keyword in symptom_token:
                    if symptom_token not in overlap and keyword not in overlap:
                        partial_score += 0.5

        total_score = score + partial_score

        if total_score > 0:
            scored_guidelines.append({
                **guideline,
                "match_score": total_score,
                "matched_keywords": list(overlap),
            })

    scored_guidelines.sort(key=lambda x: x["match_score"], reverse=True)
    return scored_guidelines


class SymptomsRequest(BaseModel):
    """Requête pour la correspondance de symptômes."""
    symptoms: str


@app.get("/health")
async def health_check():
    """Vérifie l'état de santé du serveur MCP."""
    return {"status": "ok", "server": "MCP Care Guidelines"}


@app.get("/guidelines")
async def get_guidelines(symptoms: str = Query(..., description="Symptômes du patient")):
    """
    Retourne les lignes directrices correspondant aux symptômes fournis.
    Effectue une recherche par correspondance de mots clés.
    """
    guidelines = _load_guidelines()
    matched = _match_guidelines(symptoms, guidelines)

    return {
        "status": "success",
        "symptoms_query": symptoms,
        "total_matches": len(matched),
        "guidelines": matched,
    }


@app.get("/guidelines/all")
async def get_all_guidelines():
    """Retourne toutes les lignes directrices disponibles."""
    guidelines = _load_guidelines()
    return {
        "status": "success",
        "total_guidelines": len(guidelines),
        "guidelines": guidelines,
    }


@app.post("/guidelines/match")
async def match_guidelines(request: SymptomsRequest):
    """
    Retourne les 3 meilleures correspondances de lignes directrices
    pour les symptômes fournis.
    """
    guidelines = _load_guidelines()
    matched = _match_guidelines(request.symptoms, guidelines)
    top_matches = matched[:3]

    return {
        "status": "success",
        "symptoms_query": request.symptoms,
        "top_matches": len(top_matches),
        "guidelines": top_matches,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MCP_SERVER_PORT", "8001"))
    uvicorn.run("mcp_server.server:app", host="0.0.0.0", port=port, reload=True)
