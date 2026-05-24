"""
Tests for the FastAPI API endpoints.
Tests all 6 routes with TestClient, error handling, and HITL resume flow.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.api import app


client = TestClient(app)


class TestHealthEndpoint:
    """Tests du endpoint de santé."""

    def test_health_returns_ok(self):
        """Le endpoint /health doit retourner un statut ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "Medical Multi-Agent API"


class TestSessionsStart:
    """Tests du endpoint /sessions/start."""

    def test_create_session(self):
        """POST /sessions/start doit créer une session avec un thread_id."""
        response = client.post("/sessions/start")
        assert response.status_code == 200
        data = response.json()
        assert "thread_id" in data
        assert data["status"] == "created"
        assert len(data["thread_id"]) > 0

    def test_create_multiple_sessions(self):
        """Chaque appel doit créer un thread_id unique."""
        response1 = client.post("/sessions/start")
        response2 = client.post("/sessions/start")
        assert response1.json()["thread_id"] != response2.json()["thread_id"]


class TestConsultationStart:
    """Tests du endpoint /consultation/start."""

    def test_start_consultation_missing_fields(self):
        """POST /consultation/start sans champs requis doit retourner 422."""
        response = client.post("/consultation/start", json={})
        assert response.status_code == 422

    def test_start_consultation_invalid_age(self):
        """POST /consultation/start avec un âge invalide doit retourner 422."""
        response = client.post("/consultation/start", json={
            "thread_id": "test-thread",
            "patient_name": "Test Patient",
            "patient_age": 0,
            "initial_case": "Description du cas de test suffisamment longue",
        })
        assert response.status_code == 422

    def test_start_consultation_short_case(self):
        """POST /consultation/start avec une description trop courte doit retourner 422."""
        response = client.post("/consultation/start", json={
            "thread_id": "test-thread",
            "patient_name": "Test Patient",
            "patient_age": 30,
            "initial_case": "Court",
        })
        assert response.status_code == 422


class TestConsultationResume:
    """Tests du endpoint /consultation/resume."""

    def test_resume_missing_thread(self):
        """POST /consultation/resume sans thread_id doit retourner 422."""
        response = client.post("/consultation/resume", json={
            "answer": "Test answer",
            "role": "patient",
        })
        assert response.status_code == 422

    def test_resume_invalid_role(self):
        """POST /consultation/resume avec un rôle invalide doit retourner 422."""
        response = client.post("/consultation/resume", json={
            "thread_id": "test-thread",
            "answer": "Test answer",
            "role": "invalid_role",
        })
        assert response.status_code == 422

    def test_resume_nonexistent_thread(self):
        """POST /consultation/resume avec un thread inexistant doit retourner 404."""
        response = client.post("/consultation/resume", json={
            "thread_id": "nonexistent-thread-id",
            "answer": "Test answer",
            "role": "patient",
        })
        assert response.status_code == 404

    @pytest.mark.integration
    def test_resume_patient_answer_advances_to_next_question(self):
        """Après une réponse patient, l'API doit retourner la question suivante."""
        session_response = client.post("/sessions/start")
        thread_id = session_response.json()["thread_id"]

        start_response = client.post("/consultation/start", json={
            "thread_id": thread_id,
            "patient_name": "Test Patient",
            "patient_age": 30,
            "initial_case": "Toux sÃ¨che depuis trois jours avec fatigue lÃ©gÃ¨re.",
        })
        assert start_response.status_code == 200
        assert start_response.json()["question_number"] == 1

        resume_response = client.post("/consultation/resume", json={
            "thread_id": thread_id,
            "answer": "Toux sÃ¨che avec fatigue.",
            "role": "patient",
        })
        assert resume_response.status_code == 200

        data = resume_response.json()
        assert data["status"] == "questioning"
        assert data["question_number"] == 2
        assert "Depuis combien de temps" in data["question"]


class TestConsultationStatus:
    """Tests du endpoint /consultation/{thread_id}."""

    def test_get_nonexistent_consultation(self):
        """GET /consultation/{thread_id} inexistant doit retourner 404."""
        response = client.get("/consultation/nonexistent-thread-id")
        assert response.status_code == 404


class TestConsultationReport:
    """Tests du endpoint /consultation/{thread_id}/report."""

    def test_get_report_nonexistent(self):
        """GET /consultation/{thread_id}/report inexistant doit retourner 404."""
        response = client.get("/consultation/nonexistent-thread-id/report")
        assert response.status_code == 404


class TestInputValidation:
    """Tests de validation des entrées Pydantic."""

    def test_empty_patient_name(self):
        """Le nom du patient ne doit pas être vide."""
        response = client.post("/consultation/start", json={
            "thread_id": "test-thread",
            "patient_name": "",
            "patient_age": 30,
            "initial_case": "Description suffisamment longue pour le test",
        })
        assert response.status_code == 422

    def test_age_too_high(self):
        """L'âge du patient ne doit pas dépasser 120."""
        response = client.post("/consultation/start", json={
            "thread_id": "test-thread",
            "patient_name": "Test",
            "patient_age": 200,
            "initial_case": "Description suffisamment longue pour le test",
        })
        assert response.status_code == 422

    def test_empty_answer(self):
        """La réponse ne doit pas être vide."""
        response = client.post("/consultation/resume", json={
            "thread_id": "test-thread",
            "answer": "",
            "role": "patient",
        })
        assert response.status_code == 422
