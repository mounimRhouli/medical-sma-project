# Rapport Technique - Systeme Multi-Agents d'Orientation Clinique Preliminaire

## 1. Contexte et objectif

Ce projet est une simulation academique d'un systeme multi-agents (SMA) pour l'orientation clinique preliminaire. Il combine LangGraph, LangChain, FastAPI, un serveur MCP, Streamlit et Groq afin de simuler un flux de consultation encadre par une revue humaine.

Le systeme ne remplace pas une consultation medicale, ne constitue pas un dispositif medical et ne doit pas etre utilise pour prendre des decisions medicales reelles.

## 2. Architecture generale

```text
START -> SUPERVISOR -> DIAGNOSTIC_AGENT
              |
              +-> PHYSICIAN_REVIEW
              |
              +-> REPORT_AGENT
              |
              +-> FINISH

FastAPI API  <->  Streamlit UI
    |
    +-> MCP Server
    |
    +-> Groq LLM via LangChain
```

Services par defaut:

| Service | Role | Port |
| --- | --- | --- |
| FastAPI | API REST de consultation | 8000 |
| MCP Server | Lignes directrices de soins | 8001 |
| Streamlit | Interface utilisateur | 8501 |

Le frontend lit `API_BASE_URL` depuis `.env`. Si le port FastAPI par defaut est indisponible, le backend peut etre lance sur un autre port, par exemple `8010`, puis `API_BASE_URL` doit etre mis a jour.

Exemple de fallback local:

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.app.api:app --host 0.0.0.0 --port 8010 --reload
```

Configuration associee dans `.env`:

```env
API_BASE_URL=http://localhost:8010
```

## 3. Configuration

La configuration applicative est centralisee dans `backend/app/config.py`.

Variables principales:

```env
GROQ_API_KEY=your_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8001
API_BASE_URL=http://localhost:8000
```

Les agents LLM ne contiennent plus de nom de modele en dur. Ils appellent:

- `get_llm_model()`
- `get_groq_api_key()`

Cela garantit que le modele Groq est pilote par `.env`.

## 4. Choix technologiques

| Technologie | Utilisation | Justification |
| --- | --- | --- |
| LangGraph | Graphe de workflow et routage | Orchestration d'agents, transitions explicites |
| LangChain | Appels LLM et outils | Integration avec Groq et outils applicatifs |
| Groq | Generation LLM | Inference rapide et acces simple via API |
| FastAPI | API REST | Validation Pydantic, Swagger, integration simple |
| MCP/FastAPI | Service de lignes directrices | Separation entre workflow et base de recommandations |
| Streamlit | Interface utilisateur | Prototypage rapide, gestion de session |
| ReportLab | Export PDF | Rapport final professionnel telechargeable |
| Pytest | Validation | Tests unitaires et d'integration |

## 5. Agents et responsabilites

### Supervisor

Fichier: `backend/app/nodes/supervisor.py`

Le superviseur realise un routage deterministe:

| Condition | Prochaine etape |
| --- | --- |
| Rapport final present | FINISH |
| Avis medecin present | report_agent |
| Synthese preliminaire produite | physician_review |
| Question posee mais non repondue | FINISH temporaire |
| Sinon | diagnostic_agent |

La condition "question posee mais non repondue" evite que le graphe boucle sur les cinq questions sans attendre le patient.

### DiagnosticAgent

Fichier: `backend/app/nodes/diagnostic_agent.py`

Responsabilites:

- Poser exactement cinq questions obligatoires.
- Collecter les reponses patient.
- Generer une synthese clinique preliminaire via Groq.
- Appeler `recommend_interim_care` pour produire une recommandation intermediaire prudente.

Le prompt interdit tout diagnostic definitif et impose le vocabulaire "orientation clinique preliminaire".

### PhysicianReview

Fichier: `backend/app/nodes/physician_review.py`

Ce noeud represente le point Human-in-the-Loop. Le medecin consulte les informations patient, la synthese preliminaire et la recommandation intermediaire, puis saisit son avis ou sa conduite a tenir.

### ReportAgent

Fichier: `backend/app/nodes/report_agent.py`

Responsabilites:

- Generer une conclusion generale via Groq.
- Construire le rapport final texte.
- Construire `final_report_json` via `FinalReportModel`.
- Sauvegarder un historique local dans `backend/consultations_history.json`.

Le PDF professionnel est genere cote frontend a partir de `final_report_json`.

## 6. Gestion de l'etat

Le projet utilise deux niveaux d'etat:

1. `MedicalState`, defini dans `backend/app/state.py`, pour le graphe et les agents.
2. `API_SESSION_STATES`, dictionnaire en memoire dans `backend/app/api.py`, pour garantir la progression interactive de l'API REST entre les reponses patient.

Ce store API en memoire evite les problemes de reprise apres un `END` checkpoint LangGraph dans le flux question par question. Il convient pour une demonstration academique locale. Pour une version de production, il faudrait le remplacer par Redis, PostgreSQL ou un checkpointer persistant adapte au mode interactif.

Champs principaux de `MedicalState`:

| Champ | Description |
| --- | --- |
| `patient_info` | Nom, age, motif initial |
| `question_count` | Numero de question courant |
| `questions_and_answers` | Historique Q/R |
| `diagnostic_summary` | Synthese clinique preliminaire |
| `interim_care` | Recommandation intermediaire |
| `physician_treatment` | Avis du medecin |
| `final_report` | Rapport final texte |
| `final_report_json` | Rapport final structure |
| `consultation_status` | Statut courant |
| `thread_id` | ID de session |

## 7. API FastAPI

Endpoints disponibles:

| Methode | Route | Description |
| --- | --- | --- |
| GET | `/health` | Verification de l'API |
| POST | `/sessions/start` | Creation d'une session |
| POST | `/consultation/start` | Demarrage de consultation |
| POST | `/consultation/resume` | Reponse patient ou avis medecin |
| GET | `/consultation/{thread_id}` | Etat courant |
| GET | `/consultation/{thread_id}/report` | Rapport final |

Validation:

- `patient_age` entre 1 et 120.
- `initial_case` obligatoire.
- `role` limite a `patient` ou `physician`.
- Reponse non vide.

Gestion d'erreur:

- 422 pour les erreurs de validation.
- 404 pour une session ou un rapport introuvable.
- 500 pour les erreurs internes.
- Les erreurs LLM sont capturees et remplacent la sortie par un message de fallback prudent.

## 8. Serveur MCP

Fichier: `mcp_server/server.py`

Le serveur MCP expose des lignes directrices locales contenues dans `mcp_server/data/care_guidelines.json`.

Endpoints:

| Methode | Route | Description |
| --- | --- | --- |
| GET | `/health` | Etat du serveur |
| GET | `/guidelines` | Recherche par symptomes |
| GET | `/guidelines/all` | Liste complete |
| POST | `/guidelines/match` | Meilleures correspondances |

La recherche repose sur une tokenisation simple, une suppression de stop words et un score de recouvrement de mots cles.

## 9. Frontend Streamlit

Fichier: `frontend/app.py`

Ecrans:

1. Saisie patient.
2. Questionnaire clinique en cinq questions.
3. Revue medecin HITL.
4. Rapport final.

Fonctions recentes:

- Le backend cible est lu depuis `API_BASE_URL`.
- Le rapport final peut etre telecharge en PDF.
- Le PDF contient une reference courte, l'ID de session complet, les informations patient, les questions/reponses, la synthese, la recommandation, l'avis medecin, la conclusion et l'avertissement legal.

## 10. Rapport PDF

Le PDF est genere avec ReportLab dans `build_report_pdf()`.

Caracteristiques:

- Mise en page professionnelle.
- Tableau de metadonnees.
- Reference du rapport et ID de session complet.
- Table Q/R.
- Sections structurees.
- Avertissement legal encadre.
- Pied de page avec numerotation.

L'ancien telechargement `.txt` a ete remplace par:

```text
Telecharger le rapport (.pdf)
```

## 11. Tests

La suite de tests contient:

- `tests/test_graph.py`: compilation et routage LangGraph.
- `tests/test_api.py`: endpoints FastAPI et progression Q1 -> Q2.
- `tests/test_scenarios.py`: scenarios cliniques et matching MCP.

Commande:

```powershell
.\venv\Scripts\python.exe -m pytest tests\ -v
```

Etat courant apres mise a jour:

```text
53 tests passent
```

## 12. Scenarios cliniques academiques

| Scenario | Entree | Attendu |
| --- | --- | --- |
| Syndrome respiratoire simple | Toux seche, 3 jours | Urgence medium |
| Red flags cardiovasculaires | Douleur thoracique intense | Urgence high |
| Cas benin | Fatigue legere | Urgence low |

## 13. Limites connues

- `API_SESSION_STATES` est en memoire: les sessions disparaissent au redemarrage du backend.
- Le systeme n'est pas securise par authentification.
- Les recommandations MCP sont simplifiees et academiques.
- Les sorties LLM dependent de la disponibilite de Groq et du modele configure dans `.env`.
- Le systeme ne doit pas etre utilise comme avis medical.

## 14. Perspectives

- Remplacer le store en memoire par Redis ou PostgreSQL.
- Ajouter une authentification pour le role medecin.
- Ajouter un historique consultable des rapports.
- Enrichir les lignes directrices MCP.
- Ajouter un export PDF multilingue.
- Containeriser l'application.

## 15. Conclusion

Le projet illustre un workflow multi-agents medical academique avec un questionnaire structure, une synthese LLM, une recommandation outillee par MCP, une revue humaine et un rapport final professionnel. Les dernieres modifications alignent le code avec une configuration `.env` centralisee, un modele Groq actuel, un export PDF professionnel et une API interactive plus robuste.

**Ce systeme ne remplace pas une consultation medicale.**
