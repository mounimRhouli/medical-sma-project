# Rapport Technique — Système Multi-Agents d'Orientation Clinique Préliminaire

## 1. Introduction et Contexte Académique

Ce projet est réalisé dans un cadre strictement académique. Il présente un **système multi-agents (SMA)** d'orientation clinique préliminaire, conçu pour simuler un processus de consultation médicale assistée par intelligence artificielle.

**⚠️ Ce système ne remplace pas une consultation médicale. Il ne constitue pas un dispositif médical et ne doit en aucun cas être utilisé pour établir un diagnostic réel.**

L'objectif pédagogique est d'explorer :
- L'orchestration d'agents intelligents via LangGraph
- L'intégration de modèles de langage (LLM) via Groq API
- La mise en œuvre du pattern Human-in-the-Loop (HITL)
- L'architecture microservices avec FastAPI et MCP
- Le prototypage rapide d'interfaces avec Streamlit

---

## 2. Architecture Générale du Système

### Diagramme ASCII du Workflow LangGraph

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKFLOW MÉDICAL SMA                         │
│                                                                 │
│  ┌─────────┐     ┌──────────────┐     ┌───────────────────┐   │
│  │  START   │────▶│  SUPERVISOR  │────▶│ DIAGNOSTIC_AGENT  │   │
│  └─────────┘     │  (Routage)   │     │  (5 Questions)    │   │
│                  └──────┬───────┘     └────────┬──────────┘   │
│                         │                      │               │
│                         │◀─────────────────────┘               │
│                         │                                      │
│                         │     ┌───────────────────────┐        │
│                         ├────▶│  PHYSICIAN_REVIEW     │        │
│                         │     │  (HITL — Interruption) │        │
│                         │     └────────┬──────────────┘        │
│                         │              │                       │
│                         │◀─────────────┘                       │
│                         │                                      │
│                         │     ┌───────────────────┐            │
│                         ├────▶│  REPORT_AGENT     │            │
│                         │     │  (Rapport Final)  │            │
│                         │     └────────┬──────────┘            │
│                         │              │                       │
│                         │◀─────────────┘                       │
│                         │                                      │
│                  ┌──────▼───────┐                              │
│                  │    FINISH    │                               │
│                  └──────────────┘                              │
└─────────────────────────────────────────────────────────────────┘

Services externes:
┌──────────────┐  HTTP   ┌──────────────┐
│ FastAPI API  │◀───────▶│  Streamlit   │
│ (Port 8000)  │         │  (Frontend)  │
└──────┬───────┘         └──────────────┘
       │
       │  LangGraph
       ▼
┌──────────────┐  HTTP   ┌──────────────┐
│  MedicalGraph│◀───────▶│  MCP Server  │
│  (Workflow)  │         │  (Port 8001) │
└──────────────┘         └──────────────┘
```

### Description des Composants

| Composant | Rôle | Technologie |
|-----------|------|-------------|
| **Supervisor** | Routage déterministe entre les agents | Python (logique conditionnelle) |
| **DiagnosticAgent** | Collecte des réponses patient + synthèse LLM | LangChain + Groq |
| **PhysicianReview** | Point d'interruption HITL pour le médecin | LangGraph interrupt |
| **ReportAgent** | Génération du rapport final structuré | LangChain + Groq + Pydantic |
| **FastAPI** | API REST (6 endpoints) | FastAPI + Uvicorn |
| **MCP Server** | Base de données de lignes directrices | FastAPI (standalone) |
| **Streamlit** | Interface utilisateur (4 écrans) | Streamlit |

---

## 3. Choix Technologiques et Justifications

### Pourquoi LangGraph ?
- **Gestion d'état** : TypedDict partagé entre tous les nœuds (MedicalState)
- **HITL natif** : `interrupt_before` permet de pauser le workflow avant la revue médecin
- **LangGraph Studio** : Visualisation et débogage du graphe en temps réel
- **MemorySaver** : Persistance de l'état de la consultation par thread_id
- **Routage conditionnel** : `add_conditional_edges` pour le supervisor

### Pourquoi Groq API ?
- **Gratuit** : Pas de coûts pour l'utilisation académique
- **Rapide** : Inférence très rapide grâce au matériel LPU propriétaire
- **llama3-70b-8192** : Modèle performant pour la génération de texte médical en français
- **Compatibilité LangChain** : Package `langchain-groq` officiel

### Pourquoi FastAPI ?
- **Asynchrone** : Support natif async/await pour les appels LLM
- **Documentation automatique** : Swagger UI accessible à `/docs`
- **Validation** : Pydantic intégré pour la validation des requêtes
- **Performance** : Serveur ASGI via Uvicorn

### Pourquoi MCP (Model Context Protocol) ?
- **Extensibilité** : Les outils peuvent être ajoutés dynamiquement
- **Séparation des préoccupations** : Les lignes directrices sont indépendantes du workflow
- **Interopérabilité** : Protocole standardisé pour les outils LLM
- **Scalabilité** : Le serveur MCP peut être déployé indépendamment

### Pourquoi Streamlit ?
- **Rapidité de prototypage** : Interface fonctionnelle en un seul fichier
- **Session state** : Gestion native de l'état de navigation
- **Composants riches** : Barres de progression, expanders, boutons de téléchargement
- **Pas de JavaScript** : Tout en Python

---

## 4. Description des Agents

### 4.1 Supervisor (Nœud superviseur)

**Fichier** : `backend/app/nodes/supervisor.py`

Le superviseur est un nœud de routage **purement déterministe** (pas de LLM). Il analyse l'état actuel et détermine le prochain agent à exécuter :

| Condition | Prochain nœud | Statut |
|-----------|---------------|--------|
| `final_report` existe | FINISH | completed |
| `physician_treatment` fourni | report_agent | report_generated |
| `question_count >= 5` ET `diagnostic_summary` | physician_review | awaiting_physician |
| Sinon | diagnostic_agent | questioning/started |

### 4.2 DiagnosticAgent (Agent d'orientation clinique préliminaire)

**Fichier** : `backend/app/nodes/diagnostic_agent.py`

Cet agent fonctionne en deux phases :

**Phase 1 — Questionnaire** (question_count < 5) :
- Pose les 5 questions obligatoires dans l'ordre
- Chaque question est formatée via l'outil `ask_patient`
- Attend la réponse du patient via l'API

**Phase 2 — Synthèse** (question_count == 5) :
- Enregistre toutes les réponses via `record_patient_answer`
- Génère la synthèse clinique préliminaire via Groq LLM
- Appelle `recommend_interim_care` pour les recommandations intermédiaires

**Prompt LLM utilisé** :
> "Tu es un assistant médical académique. À partir des réponses suivantes d'un patient fictif, rédige une synthèse clinique préliminaire structurée en français. N'émets AUCUN diagnostic définitif. Utilise uniquement le terme 'orientation clinique préliminaire'."

### 4.3 PhysicianReview (Revue médecin — HITL)

**Fichier** : `backend/app/nodes/physician_review.py`

Ce nœud est le point d'interruption **Human-in-the-Loop** :
- Le graphe se met en **pause automatique** avant ce nœud (`interrupt_before`)
- Affiche un résumé complet au médecin (patient, synthèse, recommandations)
- Le médecin saisit son traitement via l'API `/consultation/resume`
- Le nœud reprend et enregistre l'avis médical

### 4.4 ReportAgent (Agent de rapport)

**Fichier** : `backend/app/nodes/report_agent.py`

Génère le rapport final structuré en 7 sections :
1. Informations patient
2. Anamnèse (Q&A)
3. Synthèse clinique préliminaire
4. Recommandation intermédiaire
5. Avis du médecin traitant
6. Conclusion générale (LLM)
7. Avertissement légal

Stocke le rapport en deux formats :
- `final_report` : Texte formaté
- `final_report_json` : Modèle Pydantic `FinalReportModel`

---

## 5. Gestion de l'État Partagé (MedicalState)

Le `MedicalState` est un `TypedDict` partagé par tous les nœuds :

```python
class MedicalState(TypedDict, total=False):
    messages: Annotated[list, add_messages]       # Historique des messages
    next: Literal[...]                             # Prochain nœud
    patient_info: dict                             # Info patient
    question_count: int                            # Compteur 0-5
    questions_and_answers: List[dict]              # Paires Q&A
    current_question: str                          # Question courante
    diagnostic_summary: str                        # Synthèse clinique
    interim_care: str                              # Recommandation intermédiaire
    physician_treatment: str                       # Avis médecin
    final_report: str                              # Rapport texte
    final_report_json: dict                        # Rapport structuré
    consultation_status: Literal[...]              # Statut consultation
    thread_id: str                                 # ID de session
    error: Optional[str]                           # Erreur éventuelle
```

L'annotation `Annotated[list, add_messages]` permet à LangGraph d'**accumuler** les messages au lieu de les remplacer.

---

## 6. Human-in-the-Loop — Implémentation et Flux

### Principe

Le HITL est un pattern essentiel pour les systèmes médicaux. Il garantit qu'un professionnel de santé valide les résultats avant la génération du rapport final.

### Flux HITL

```
DiagnosticAgent (5 questions)
        │
        ▼
Supervisor → physician_review
        │
        ▼ (PAUSE — interrupt_before)
        │
[Attente de l'intervention du médecin]
        │
API: POST /consultation/resume (role=physician)
        │
        ▼
PhysicianReview (traite l'avis médecin)
        │
        ▼
Supervisor → report_agent
        │
        ▼
ReportAgent (génère le rapport final)
```

### Implémentation technique

```python
medical_graph = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["physician_review"],
)
```

Le `MemorySaver` permet de persister l'état pendant la pause, et l'API utilise `graph.update_state()` pour injecter l'avis du médecin avant de reprendre le graphe.

---

## 7. Intégration MCP

### Architecture

Le serveur MCP est un service FastAPI standalone (port 8001) qui fournit :
- **GET /health** : Vérification de l'état du serveur
- **GET /guidelines** : Recherche par symptômes (query param)
- **GET /guidelines/all** : Toutes les lignes directrices
- **POST /guidelines/match** : Top 3 correspondances

### Base de données

10 conditions médicales couvertes :
1. Syndrome respiratoire
2. Troubles digestifs
3. Urgence cardiovasculaire (RED FLAG)
4. Troubles musculosquelettiques
5. Urgence neurologique (RED FLAG)
6. Troubles dermatologiques
7. Troubles ORL
8. Troubles urologiques
9. Troubles ophtalmologiques
10. Symptômes généraux bénins

### Algorithme de correspondance

- Tokenisation du texte des symptômes
- Suppression des stop words français
- Correspondance par chevauchement de mots clés
- Score basé sur la fréquence de correspondance
- Support des correspondances partielles (sous-chaînes)

---

## 8. API FastAPI — Routes et Contrats

### Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/health` | Vérification de l'état de l'API |
| POST | `/sessions/start` | Création d'une session |
| POST | `/consultation/start` | Démarrage de la consultation |
| POST | `/consultation/resume` | Reprise (patient ou médecin) |
| GET | `/consultation/{thread_id}` | État de la consultation |
| GET | `/consultation/{thread_id}/report` | Rapport final |

### Validation Pydantic

Tous les endpoints utilisent des modèles Pydantic pour la validation :
- `ConsultationStartRequest` : thread_id, patient_name, patient_age (1-120), initial_case (min 10 chars)
- `ConsultationResumeRequest` : thread_id, answer, role (patient|physician)

### Gestion d'erreurs

- **422** : Validation Pydantic échouée
- **404** : Consultation ou rapport non trouvé
- **500** : Erreur interne (LLM, graphe)
- Tous les appels LLM sont protégés par `try/except` avec messages de fallback

---

## 9. Frontend Streamlit — Écrans et Navigation

### Écran 1 : Saisie du Cas Initial Patient
- Champs : Nom, Âge (1-120), Description du cas (min 20 chars)
- Validation côté client et serveur
- Bouton "Démarrer la consultation"

### Écran 2 : Questionnaire Patient
- Barre de progression (question N/5)
- Affichage de la question courante
- Zone de réponse
- Historique des réponses précédentes (expander)

### Écran 3 : Revue Médecin (HITL)
- Affichage du résumé patient
- Synthèse clinique préliminaire
- Recommandation intermédiaire
- Zone de saisie pour l'avis médecin

### Écran 4 : Rapport Final
- Affichage du rapport complet (text_area)
- Sections détaillées (expanders)
- Avertissement légal
- Boutons : Nouvelle consultation, Télécharger (.txt)

### Navigation
- `st.session_state["screen"]` contrôle l'écran affiché
- Barre latérale persistante avec statut, progression, informations patient

---

## 10. Tests et Scénarios de Validation

### Structure des tests

- `test_graph.py` : Tests de compilation et routage du graphe
- `test_api.py` : Tests des endpoints FastAPI
- `test_scenarios.py` : 3 scénarios cliniques complets

### Scénario 1 — Syndrome respiratoire simple
- **Patient** : Toux sèche, 3 jours, 4/10, aucun antécédent
- **Attendu** : Urgence medium, repos et hydratation recommandés

### Scénario 2 — Cas avec red flags cardiovasculaires
- **Patient** : Douleur thoracique intense, 2h, 9/10, hypertendu
- **Attendu** : Urgence high, consultation urgente recommandée

### Scénario 3 — Cas bénin
- **Patient** : Légère fatigue, 1 semaine, 2/10
- **Attendu** : Urgence low, repos et surveillance

### Couverture

- Tests unitaires : Supervisor, outils, tokenisation
- Tests d'intégration : API endpoints, MCP matching
- Tests de validation : Pydantic, entrées invalides

---

## 11. Cadre Éthique Respecté

### Règles strictement appliquées

1. **Pas de diagnostic définitif** : Le terme "diagnostic" n'est jamais utilisé seul. Uniquement "orientation clinique préliminaire" et "synthèse clinique préliminaire".

2. **Recommandations prudentes** : Les recommandations intermédiaires sont toujours générales (repos, hydratation, surveillance, consultation en cas d'aggravation).

3. **Avertissement systématique** : Chaque rapport final se termine par :
   > "⚠️ Ce système ne remplace pas une consultation médicale."

4. **HITL obligatoire** : Un professionnel de santé doit valider avant la génération du rapport.

5. **Cadre académique** : Le système est clairement présenté comme une simulation académique.

---

## 12. Conclusion et Perspectives

### Réalisations

Ce projet démontre la faisabilité d'un système multi-agents médical orchestré par LangGraph, intégrant :
- Un workflow structuré avec routage conditionnel
- Une interruption Human-in-the-Loop pour la validation médicale
- Des outils externes via le protocole MCP
- Une API REST complète avec FastAPI
- Une interface utilisateur fonctionnelle avec Streamlit

### Perspectives d'amélioration

1. **Persistance** : Remplacer MemorySaver par une base de données (PostgreSQL, Redis)
2. **Authentification** : Ajouter JWT pour sécuriser l'accès médecin
3. **Multilingue** : Support de plusieurs langues (actuellement français uniquement)
4. **Base de connaissances** : Enrichir les lignes directrices MCP avec des sources médicales validées
5. **Monitoring** : Ajouter LangSmith pour le traçage des appels LLM
6. **Déploiement** : Containerisation Docker et déploiement cloud

---

**⚠️ Ce système ne remplace pas une consultation médicale. Il est produit dans le cadre d'un exercice académique.**
