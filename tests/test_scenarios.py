"""
Integration test scenarios for the Medical Clinical Orientation Workflow.
Tests 3 complete clinical scenarios through the FastAPI API.
Note: These tests require GROQ_API_KEY to be set for LLM calls.
Tests that require API calls are marked with pytest.mark.integration.
"""

from fastapi.testclient import TestClient
from backend.app.api import app
from backend.app.nodes.supervisor import supervisor_node
from backend.app.nodes.diagnostic_agent import MANDATORY_QUESTIONS
from backend.app.tools.patient_tools import ask_patient, record_patient_answer
from mcp_server.server import _match_guidelines, _load_guidelines, _tokenize


client = TestClient(app)


class TestMCPMatching:
    """Tests de la correspondance MCP pour les 3 scénarios."""

    def test_respiratory_matching(self):
        """Scénario 1 : Les symptômes respiratoires doivent correspondre aux lignes directrices."""
        guidelines = _load_guidelines()
        results = _match_guidelines("toux sèche persistante fièvre", guidelines)
        assert len(results) > 0
        conditions = [r["condition"] for r in results]
        assert any("respiratoire" in c.lower() for c in conditions)

    def test_cardiac_red_flag_matching(self):
        """Scénario 2 : La douleur thoracique doit déclencher un red flag cardiovasculaire."""
        guidelines = _load_guidelines()
        results = _match_guidelines("douleur thoracique intense palpitations", guidelines)
        assert len(results) > 0
        high_urgency = [r for r in results if r.get("urgency") == "high"]
        assert len(high_urgency) > 0, "Les symptômes cardiovasculaires doivent avoir une urgence 'high'"

    def test_benign_matching(self):
        """Scénario 3 : La fatigue légère doit avoir une urgence basse."""
        guidelines = _load_guidelines()
        results = _match_guidelines("légère fatigue stress insomnie", guidelines)
        assert len(results) > 0
        low_urgency = [r for r in results if r.get("urgency") == "low"]
        assert len(low_urgency) > 0, "Les symptômes bénins doivent avoir une urgence 'low'"


class TestTokenization:
    """Tests de la tokenisation des symptômes."""

    def test_tokenize_basic(self):
        """La tokenisation doit séparer les mots et supprimer les stop words."""
        tokens = _tokenize("toux sèche et fièvre")
        assert "toux" in tokens
        assert "fièvre" in tokens
        assert "et" not in tokens

    def test_tokenize_accented(self):
        """La tokenisation doit gérer les caractères accentués."""
        tokens = _tokenize("céphalée sévère")
        assert "céphalée" in tokens
        assert "sévère" in tokens


class TestPatientTools:
    """Tests des outils patient."""

    def test_ask_patient_format(self):
        """ask_patient doit formater correctement la question."""
        result = ask_patient.invoke({
            "question": "Quel est votre symptôme principal ?",
            "question_number": 1,
        })
        assert "[Question 1/5]" in result
        assert "symptôme principal" in result

    def test_record_patient_answer_structure(self):
        """record_patient_answer doit retourner un dict structuré."""
        result = record_patient_answer.invoke({
            "question": "Question test",
            "answer": "Réponse test",
            "question_number": 1,
        })
        assert result["question"] == "Question test"
        assert result["answer"] == "Réponse test"
        assert result["number"] == 1


class TestMandatoryQuestions:
    """Tests des 5 questions obligatoires."""

    def test_exactly_five_questions(self):
        """Il doit y avoir exactement 5 questions obligatoires."""
        assert len(MANDATORY_QUESTIONS) == 5

    def test_questions_are_in_french(self):
        """Les questions doivent être en français."""
        french_indicators = ["vous", "votre", "vos", "avez", "êtes"]
        for question in MANDATORY_QUESTIONS:
            has_french = any(indicator in question.lower() for indicator in french_indicators)
            assert has_french, f"La question ne semble pas être en français : {question}"

    def test_question_order_symptome_principal(self):
        """Q1 doit porter sur le symptôme principal."""
        assert "symptôme principal" in MANDATORY_QUESTIONS[0].lower() or "motif" in MANDATORY_QUESTIONS[0].lower()

    def test_question_order_duree(self):
        """Q2 doit porter sur la durée des symptômes."""
        assert "combien de temps" in MANDATORY_QUESTIONS[1].lower() or "depuis" in MANDATORY_QUESTIONS[1].lower()

    def test_question_order_intensite(self):
        """Q3 doit porter sur l'intensité de la douleur."""
        assert "échelle" in MANDATORY_QUESTIONS[2].lower() or "intensité" in MANDATORY_QUESTIONS[2].lower()

    def test_question_order_antecedents(self):
        """Q4 doit porter sur les antécédents."""
        assert "antécédents" in MANDATORY_QUESTIONS[3].lower() or "allergies" in MANDATORY_QUESTIONS[3].lower()

    def test_question_order_medicaments(self):
        """Q5 doit porter sur les médicaments actuels."""
        assert "médicaments" in MANDATORY_QUESTIONS[4].lower()


class TestScenario1Respiratory:
    """
    Scénario 1 — Syndrome respiratoire simple.
    Patient: Toux sèche persistante, 3 jours, 4/10, aucun antécédent, aucun médicament.
    """

    ANSWERS = [
        "Toux sèche persistante",
        "Depuis 3 jours",
        "4/10",
        "Aucun antécédent",
        "Aucun médicament",
    ]

    def test_supervisor_routes_correctly_through_workflow(self):
        """Le superviseur doit router correctement à travers le workflow respiratoire."""
        state = {
            "question_count": 0,
            "diagnostic_summary": "",
            "physician_treatment": "",
            "final_report": "",
        }
        result = supervisor_node(state)
        assert result["next"] == "diagnostic_agent"

        state["question_count"] = 5
        state["diagnostic_summary"] = "Orientation clinique préliminaire : syndrome respiratoire"
        result = supervisor_node(state)
        assert result["next"] == "physician_review"

    def test_mcp_respiratory_guidelines(self):
        """Le MCP doit retourner des recommandations pour les symptômes respiratoires."""
        guidelines = _load_guidelines()
        results = _match_guidelines("toux sèche persistante", guidelines)
        assert len(results) > 0
        first_match = results[0]
        assert "repos" in first_match.get("guidelines", "").lower() or \
               "hydratation" in first_match.get("guidelines", "").lower()

    def test_full_qa_collection(self):
        """Les 5 paires Q&A doivent être collectées correctement."""
        qa_pairs = []
        for i, (q, a) in enumerate(zip(MANDATORY_QUESTIONS, self.ANSWERS)):
            result = record_patient_answer.invoke({
                "question": q,
                "answer": a,
                "question_number": i + 1,
            })
            qa_pairs.append(result)
        assert len(qa_pairs) == 5
        assert qa_pairs[0]["answer"] == "Toux sèche persistante"


class TestScenario2RedFlags:
    """
    Scénario 2 — Cas avec red flags cardiovasculaires.
    Patient: Douleur thoracique intense, 2 heures, 9/10, hypertendu, Amlodipine 5mg.
    """

    ANSWERS = [
        "Douleur thoracique intense",
        "Depuis 2 heures",
        "9/10",
        "Hypertendu, antécédent familial cardiaque",
        "Amlodipine 5mg",
    ]

    def test_mcp_flags_high_urgency(self):
        """Le MCP doit signaler une urgence élevée pour la douleur thoracique."""
        guidelines = _load_guidelines()
        results = _match_guidelines("douleur thoracique intense palpitations", guidelines)
        high_urgency_found = any(r.get("urgency") == "high" for r in results)
        assert high_urgency_found, "La douleur thoracique doit déclencher une urgence 'high'"

    def test_cardiac_guidelines_mention_urgence(self):
        """Les recommandations cardiovasculaires doivent mentionner l'urgence."""
        guidelines = _load_guidelines()
        results = _match_guidelines("douleur thoracique", guidelines)
        cardiac_results = [r for r in results if r.get("urgency") == "high"]
        assert len(cardiac_results) > 0
        first = cardiac_results[0]
        guidelines_text = first.get("guidelines", "").lower()
        assert "urgence" in guidelines_text or "samu" in guidelines_text or "immédiat" in guidelines_text

    def test_all_five_questions_asked(self):
        """Les 5 questions doivent être posées même pour un cas urgent."""
        qa_pairs = []
        for i, (q, a) in enumerate(zip(MANDATORY_QUESTIONS, self.ANSWERS)):
            formatted = ask_patient.invoke({"question": q, "question_number": i + 1})
            assert f"[Question {i+1}/5]" in formatted
            result = record_patient_answer.invoke({
                "question": q, "answer": a, "question_number": i + 1,
            })
            qa_pairs.append(result)
        assert len(qa_pairs) == 5


class TestScenario3Benign:
    """
    Scénario 3 — Cas bénin.
    Patient: Légère fatigue, 1 semaine, 2/10, aucun, vitamines.
    """

    ANSWERS = [
        "Légère fatigue",
        "Depuis 1 semaine",
        "2/10",
        "Aucun",
        "Vitamines",
    ]

    def test_mcp_low_urgency(self):
        """Le MCP doit retourner une urgence basse pour la fatigue légère."""
        guidelines = _load_guidelines()
        results = _match_guidelines("légère fatigue stress insomnie", guidelines)
        low_urgency = [r for r in results if r.get("urgency") == "low"]
        assert len(low_urgency) > 0

    def test_benign_guidelines_mention_repos(self):
        """Les recommandations bénignes doivent mentionner repos ou surveillance."""
        guidelines = _load_guidelines()
        results = _match_guidelines("fatigue", guidelines)
        assert len(results) > 0
        all_text = " ".join(r.get("guidelines", "") for r in results).lower()
        assert "repos" in all_text or "surveillance" in all_text

    def test_complete_workflow_state_transitions(self):
        """Le workflow complet doit passer par toutes les transitions d'état."""
        state = {"question_count": 0, "diagnostic_summary": "", "physician_treatment": "", "final_report": ""}
        result = supervisor_node(state)
        assert result["next"] == "diagnostic_agent"

        state["question_count"] = 5
        state["diagnostic_summary"] = "Orientation clinique préliminaire : fatigue générale"
        result = supervisor_node(state)
        assert result["next"] == "physician_review"

        state["physician_treatment"] = "Repos, alimentation équilibrée, activité physique douce"
        result = supervisor_node(state)
        assert result["next"] == "report_agent"

        state["final_report"] = "Rapport final complet"
        result = supervisor_node(state)
        assert result["next"] == "FINISH"
        assert result["consultation_status"] == "completed"
