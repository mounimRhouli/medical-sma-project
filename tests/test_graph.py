"""
Tests for the LangGraph medical workflow graph.
Tests graph compilation, supervisor routing, and state transitions.
"""

import pytest
from backend.app.state import MedicalState
from backend.app.nodes.supervisor import supervisor_node
from backend.app.graph import build_graph, medical_graph, checkpointer


class TestGraphCompilation:
    """Tests de compilation du graphe LangGraph."""

    def test_graph_builds_without_error(self):
        """Le graphe doit se construire sans erreur."""
        graph = build_graph()
        assert graph is not None

    def test_graph_compiles_without_error(self):
        """Le graphe compilé doit exister au niveau du module."""
        assert medical_graph is not None

    def test_checkpointer_exists(self):
        """Le checkpointer MemorySaver doit exister."""
        assert checkpointer is not None

    def test_graph_has_correct_nodes(self):
        """Le graphe doit contenir les 4 nœuds attendus."""
        graph = build_graph()
        node_names = set(graph.nodes.keys())
        expected_nodes = {"supervisor", "diagnostic_agent", "physician_review", "report_agent"}
        assert expected_nodes.issubset(node_names), (
            f"Nœuds manquants : {expected_nodes - node_names}"
        )


class TestSupervisorRouting:
    """Tests de la logique de routage du superviseur."""

    def test_routes_to_diagnostic_agent_initially(self):
        """Le superviseur doit router vers diagnostic_agent au début."""
        state: MedicalState = {
            "question_count": 0,
            "diagnostic_summary": "",
            "physician_treatment": "",
            "final_report": "",
        }
        result = supervisor_node(state)
        assert result["next"] == "diagnostic_agent"

    def test_routes_to_diagnostic_agent_mid_questioning(self):
        """Le superviseur doit continuer vers diagnostic_agent pendant le questionnaire."""
        state: MedicalState = {
            "question_count": 3,
            "questions_and_answers": [
                {"question": "Q1", "answer": "R1"},
                {"question": "Q2", "answer": "R2"},
                {"question": "Q3", "answer": "R3"},
            ],
            "diagnostic_summary": "",
            "physician_treatment": "",
            "final_report": "",
        }
        result = supervisor_node(state)
        assert result["next"] == "diagnostic_agent"

    def test_routes_to_finish_after_question_is_asked(self):
        """Le superviseur doit s'arrÃªter aprÃ¨s avoir posÃ© une question."""
        state: MedicalState = {
            "question_count": 3,
            "questions_and_answers": [
                {"question": "Q1", "answer": "R1"},
                {"question": "Q2", "answer": "R2"},
            ],
            "diagnostic_summary": "",
            "physician_treatment": "",
            "final_report": "",
        }
        result = supervisor_node(state)
        assert result["next"] == "FINISH"
        assert result["consultation_status"] == "questioning"

    def test_routes_to_physician_review_after_summary(self):
        """Le superviseur doit router vers physician_review après la synthèse."""
        state: MedicalState = {
            "question_count": 5,
            "diagnostic_summary": "Synthèse clinique préliminaire test",
            "physician_treatment": "",
            "final_report": "",
        }
        result = supervisor_node(state)
        assert result["next"] == "physician_review"

    def test_routes_to_report_agent_after_physician(self):
        """Le superviseur doit router vers report_agent après l'avis médecin."""
        state: MedicalState = {
            "question_count": 5,
            "diagnostic_summary": "Synthèse clinique préliminaire test",
            "physician_treatment": "Traitement prescrit par le médecin",
            "final_report": "",
        }
        result = supervisor_node(state)
        assert result["next"] == "report_agent"

    def test_routes_to_finish_after_report(self):
        """Le superviseur doit router vers FINISH après le rapport final."""
        state: MedicalState = {
            "question_count": 5,
            "diagnostic_summary": "Synthèse clinique préliminaire test",
            "physician_treatment": "Traitement prescrit",
            "final_report": "Rapport final complet",
        }
        result = supervisor_node(state)
        assert result["next"] == "FINISH"


class TestStateTransitions:
    """Tests des transitions d'état."""

    def test_consultation_status_started(self):
        """Le statut doit être 'started' au tout début."""
        state: MedicalState = {
            "question_count": 0,
            "diagnostic_summary": "",
            "physician_treatment": "",
            "final_report": "",
        }
        result = supervisor_node(state)
        assert result["consultation_status"] == "started"

    def test_consultation_status_questioning(self):
        """Le statut doit être 'questioning' pendant le questionnaire."""
        state: MedicalState = {
            "question_count": 2,
            "questions_and_answers": [
                {"question": "Q1", "answer": "R1"},
                {"question": "Q2", "answer": "R2"},
            ],
            "diagnostic_summary": "",
            "physician_treatment": "",
            "final_report": "",
        }
        result = supervisor_node(state)
        assert result["consultation_status"] == "questioning"

    def test_consultation_status_awaiting_physician(self):
        """Le statut doit être 'awaiting_physician' après la synthèse."""
        state: MedicalState = {
            "question_count": 5,
            "diagnostic_summary": "Synthèse clinique préliminaire test",
            "physician_treatment": "",
            "final_report": "",
        }
        result = supervisor_node(state)
        assert result["consultation_status"] == "awaiting_physician"

    def test_consultation_status_completed(self):
        """Le statut doit être 'completed' après le rapport final."""
        state: MedicalState = {
            "question_count": 5,
            "diagnostic_summary": "Synthèse clinique préliminaire",
            "physician_treatment": "Traitement",
            "final_report": "Rapport final",
        }
        result = supervisor_node(state)
        assert result["consultation_status"] == "completed"

    def test_supervisor_returns_messages(self):
        """Le superviseur doit toujours retourner des messages."""
        state: MedicalState = {
            "question_count": 0,
            "diagnostic_summary": "",
            "physician_treatment": "",
            "final_report": "",
        }
        result = supervisor_node(state)
        assert "messages" in result
        assert len(result["messages"]) > 0
