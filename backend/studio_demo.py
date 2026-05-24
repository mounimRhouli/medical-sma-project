"""
LangGraph Studio — Démonstration des 3 scénarios cliniques.

Ce script exécute le workflow complet pour chaque scénario et affiche
les transitions de nœuds, les états intermédiaires, et les interruptions
HITL (Human-in-the-Loop) telles qu'elles apparaissent dans LangGraph Studio.

Usage:
    cd medical-sma-project
    python -m backend.studio_demo

Prérequis:
    - GROQ_API_KEY définie dans .env
    - Le serveur MCP tourne sur le port 8001 (optionnel, fallback si absent)
"""

import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage
from backend.app.nodes.diagnostic_agent import MANDATORY_QUESTIONS
from backend.studio_graph import medical_graph_debug as graph


SEPARATOR = "=" * 70

SCENARIOS = [
    {
        "name": "Scénario 1 — Syndrome respiratoire simple",
        "patient": {"name": "Patient Alpha", "age": 45, "initial_case": "Toux sèche persistante depuis 3 jours"},
        "answers": [
            "Toux sèche persistante",
            "Depuis 3 jours",
            "4/10",
            "Aucun antécédent",
            "Aucun médicament",
        ],
        "physician": "Repos, hydratation abondante, surveillance symptomatique pendant 5 jours. Reconsulter si aggravation.",
    },
    {
        "name": "Scénario 2 — Red flags cardiovasculaires",
        "patient": {"name": "Patient Beta", "age": 62, "initial_case": "Douleur thoracique intense depuis 2 heures"},
        "answers": [
            "Douleur thoracique intense",
            "Depuis 2 heures",
            "9/10",
            "Hypertendu, antécédent familial cardiaque",
            "Amlodipine 5mg",
        ],
        "physician": "Urgence — orienter immédiatement aux urgences cardiologiques. ECG et troponine en priorité.",
    },
    {
        "name": "Scénario 3 — Cas bénin",
        "patient": {"name": "Patient Gamma", "age": 28, "initial_case": "Légère fatigue depuis 1 semaine"},
        "answers": [
            "Légère fatigue",
            "Depuis 1 semaine",
            "2/10",
            "Aucun",
            "Vitamines",
        ],
        "physician": "Repos suffisant, alimentation équilibrée, activité physique douce. Pas d'investigation complémentaire nécessaire.",
    },
]


def print_state(label: str, state: dict) -> None:
    """Affiche un résumé lisible de l'état courant."""
    print(f"\n  [{label}]")
    print(f"    consultation_status : {state.get('consultation_status', '—')}")
    print(f"    question_count      : {state.get('question_count', 0)}")
    print(f"    questions_and_answers: {len(state.get('questions_and_answers', []))} réponses")
    if state.get("current_question"):
        print(f"    current_question    : {state['current_question'][:80]}...")
    if state.get("diagnostic_summary"):
        print(f"    diagnostic_summary  : {state['diagnostic_summary'][:100]}...")
    if state.get("interim_care"):
        print(f"    interim_care        : {state['interim_care'][:100]}...")
    if state.get("physician_treatment"):
        print(f"    physician_treatment : {state['physician_treatment'][:100]}...")
    if state.get("final_report"):
        print(f"    final_report        : {state['final_report'][:100]}...")


def run_scenario(scenario: dict) -> None:
    """Exécute un scénario complet à travers le graphe."""
    print(f"\n{SEPARATOR}")
    print(f"  {scenario['name']}")
    print(SEPARATOR)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    patient = scenario["patient"]

    # --- Étape 1 : Démarrage de la consultation ---
    print("\n>>> Étape 1 : Démarrage de la consultation")
    initial_state = {
        "messages": [
            HumanMessage(
                content=(
                    f"Nouvelle consultation pour {patient['name']}, "
                    f"{patient['age']} ans. "
                    f"Motif : {patient['initial_case']}"
                )
            )
        ],
        "patient_info": {
            "name": patient["name"],
            "age": patient["age"],
            "initial_case": patient["initial_case"],
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
        "thread_id": thread_id,
        "error": None,
    }

    for event in graph.stream(initial_state, config=config):
        for node_name in event:
            print(f"  -> Nœud exécuté : {node_name}")

    state = graph.get_state(config)
    print_state("Après démarrage", state.values)

    # --- Étapes 2-5 : Réponses patient (Q1 à Q4) ---
    for i, answer in enumerate(scenario["answers"][:4]):
        q_num = i + 1
        print(f"\n>>> Étape {q_num + 1} : Réponse patient Q{q_num} → \"{answer}\"")

        qa_list = list(state.values.get("questions_and_answers", []))
        qa_list.append({
            "question": state.values.get("current_question", MANDATORY_QUESTIONS[i]),
            "answer": answer,
        })

        graph.update_state(
            config,
            {
                "messages": [HumanMessage(content=f"[Réponse patient Q{q_num}] {answer}")],
                "questions_and_answers": qa_list,
                "question_count": q_num + 1,
                "current_question": MANDATORY_QUESTIONS[q_num] if q_num < 5 else "",
                "consultation_status": "questioning",
            },
            as_node="diagnostic_agent",
        )

        state = graph.get_state(config)
        print_state(f"Après Q{q_num}", state.values)

    # --- Étape 6 : Dernière réponse (Q5) + génération de la synthèse ---
    print(f"\n>>> Étape 6 : Réponse patient Q5 → \"{scenario['answers'][4]}\" + génération synthèse")

    qa_list = list(state.values.get("questions_and_answers", []))
    qa_list.append({
        "question": state.values.get("current_question", MANDATORY_QUESTIONS[4]),
        "answer": scenario["answers"][4],
    })

    graph.update_state(
        config,
        {
            "messages": [HumanMessage(content=f"[Réponse patient Q5] {scenario['answers'][4]}")],
            "questions_and_answers": qa_list,
            "question_count": 5,
        },
        as_node="supervisor",
    )

    for event in graph.stream(None, config=config):
        for node_name in event:
            print(f"  -> Nœud exécuté : {node_name}")

    state = graph.get_state(config)
    print_state("Après synthèse (HITL interrupt)", state.values)

    # --- Étape 7 : Interruption HITL — le graphe est en pause ---
    print(f"\n>>> Étape 7 : INTERRUPTION HITL — En attente du médecin")
    print(f"    État du graphe : interrompu avant 'physician_review'")
    print(f"    next={state.next}")

    # --- Étape 8 : Avis du médecin ---
    print(f"\n>>> Étape 8 : Avis médecin → \"{scenario['physician'][:60]}...\"")

    graph.update_state(
        config,
        {
            "messages": [HumanMessage(content=f"[Avis médecin] {scenario['physician']}")],
            "physician_treatment": scenario["physician"],
        },
        as_node="physician_review",
    )

    for event in graph.stream(None, config=config):
        for node_name in event:
            print(f"  -> Nœud exécuté : {node_name}")

    state = graph.get_state(config)
    print_state("État final", state.values)

    # --- Résumé ---
    print(f"\n{'─' * 50}")
    print(f"  RÉSULTAT : {'SUCCÈS' if state.values.get('final_report') else 'ÉCHEC'}")
    print(f"  Statut final : {state.values.get('consultation_status', '—')}")
    print(f"{'─' * 50}")


def main() -> None:
    """Point d'entrée principal."""
    print(SEPARATOR)
    print("  LangGraph Studio — Démonstration des 3 scénarios cliniques")
    print("  Workflow : START → Supervisor → DiagnosticAgent → PhysicianReview (HITL) → ReportAgent → END")
    print(SEPARATOR)

    for scenario in SCENARIOS:
        try:
            run_scenario(scenario)
        except Exception as e:
            print(f"\n  ERREUR dans {scenario['name']} : {e}")

    print(f"\n{SEPARATOR}")
    print("  Démonstration terminée — 3 scénarios exécutés.")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
