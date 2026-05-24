# 🏥 Medical Clinical Orientation Workflow — Multi-Agent SMA

## 🇫🇷 Français

### Présentation

Système multi-agents (SMA) d'**orientation clinique préliminaire** construit avec LangGraph, LangChain, FastAPI, MCP et Streamlit. Ce projet est un **exercice strictement académique** — il ne constitue pas un dispositif médical.

**⚠️ Ce système ne remplace pas une consultation médicale.**

### Architecture

```
┌───────────────────────────────────────────────────────┐
│                 WORKFLOW LANGGRAPH                     │
│                                                       │
│  START → SUPERVISOR → DIAGNOSTIC_AGENT (5 questions)  │
│              │                                        │
│              ├──→ PHYSICIAN_REVIEW (HITL — pause)     │
│              │                                        │
│              ├──→ REPORT_AGENT (rapport final)        │
│              │                                        │
│              └──→ FINISH                              │
└───────────────────────────────────────────────────────┘
        │                           │
   FastAPI API                 MCP Server
   (Port 8000)                (Port 8001)
        │
   Streamlit UI
   (Port 8501)
```

### Prérequis

- **Python 3.11+**
- **Clé API Groq** (gratuite) : https://console.groq.com
- **pip** (gestionnaire de paquets Python)

### Installation

```bash
# 1. Cloner ou dézipper le projet
cd project

# 2. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. Installer les dépendances
pip install -r backend/requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Éditez .env et ajoutez votre GROQ_API_KEY
```

### Lancement

**Étape 1 — Démarrer le serveur MCP** (terminal 1) :
```bash
cd project
python -m uvicorn mcp_server.server:app --port 8001
```

**Étape 2 — Démarrer le backend FastAPI** (terminal 2) :
```bash
cd project
python -m uvicorn backend.app.api:app --host 0.0.0.0 --port 8000 --reload
```

**Étape 3 — Démarrer le frontend Streamlit** (terminal 3) :
```bash
cd project
streamlit run frontend/app.py
```

**Étape 4 (optionnel) — Ouvrir LangGraph Studio** :
```bash
cd project/backend
langgraph dev
```

### Documentation API

Accédez à la documentation Swagger automatique : http://localhost:8000/docs

### Comment obtenir une clé API Groq gratuite

1. Rendez-vous sur https://console.groq.com
2. Créez un compte (gratuit)
3. Générez une clé API dans le tableau de bord
4. Copiez la clé dans votre fichier `.env`

### Scénarios de test

Le projet inclut 3 scénarios de test :

1. **Syndrome respiratoire simple** : Toux sèche, 3 jours → urgence medium
2. **Red flags cardiovasculaires** : Douleur thoracique intense → urgence high
3. **Cas bénin** : Fatigue légère → urgence low

Exécuter les tests :
```bash
cd project
python -m pytest tests/ -v
```

### Avertissement éthique

⚠️ **Ce système est une simulation académique.** Il ne constitue pas un avis médical professionnel. Ne l'utilisez jamais pour des décisions médicales réelles. Consultez toujours un professionnel de santé qualifié.

---

## 🇬🇧 English

### Overview

Multi-agent system (MAS) for **preliminary clinical orientation** built with LangGraph, LangChain, FastAPI, MCP, and Streamlit. This project is a **strictly academic exercise** — it is not a medical device.

**⚠️ This system does not replace a medical consultation.**

### Architecture

```
┌───────────────────────────────────────────────────────┐
│                 LANGGRAPH WORKFLOW                     │
│                                                       │
│  START → SUPERVISOR → DIAGNOSTIC_AGENT (5 questions)  │
│              │                                        │
│              ├──→ PHYSICIAN_REVIEW (HITL — pause)     │
│              │                                        │
│              ├──→ REPORT_AGENT (final report)         │
│              │                                        │
│              └──→ FINISH                              │
└───────────────────────────────────────────────────────┘
        │                           │
   FastAPI API                 MCP Server
   (Port 8000)                (Port 8001)
        │
   Streamlit UI
   (Port 8501)
```

### Prerequisites

- **Python 3.11+**
- **Groq API Key** (free): https://console.groq.com
- **pip** (Python package manager)

### Installation

```bash
# 1. Clone or unzip the project
cd project

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### Running

**Step 1 — Start MCP server** (terminal 1):
```bash
cd project
python -m uvicorn mcp_server.server:app --port 8001
```

**Step 2 — Start FastAPI backend** (terminal 2):
```bash
cd project
python -m uvicorn backend.app.api:app --host 0.0.0.0 --port 8000 --reload
```

**Step 3 — Start Streamlit frontend** (terminal 3):
```bash
cd project
streamlit run frontend/app.py
```

**Step 4 (optional) — Open LangGraph Studio**:
```bash
cd project/backend
langgraph dev
```

### API Documentation

Access the automatic Swagger documentation: http://localhost:8000/docs

### How to get a free Groq API key

1. Go to https://console.groq.com
2. Create a free account
3. Generate an API key from the dashboard
4. Copy the key to your `.env` file

### Test Scenarios

The project includes 3 test scenarios:

1. **Simple respiratory syndrome**: Dry cough, 3 days → medium urgency
2. **Cardiovascular red flags**: Intense chest pain → high urgency
3. **Benign case**: Mild fatigue → low urgency

Run tests:
```bash
cd project
python -m pytest tests/ -v
```

### Ethical Disclaimer

⚠️ **This system is an academic simulation.** It does not constitute professional medical advice. Never use it for real medical decisions. Always consult a qualified healthcare professional.

---

## Structure du Projet / Project Structure

```
project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── graph.py              # LangGraph workflow
│   │   ├── state.py              # MedicalState (TypedDict)
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── supervisor.py     # Deterministic routing
│   │   │   ├── diagnostic_agent.py  # 5 questions + LLM summary
│   │   │   ├── physician_review.py  # HITL interruption
│   │   │   └── report_agent.py   # Final report generation
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── patient_tools.py  # ask_patient, record_answer
│   │   │   ├── care_tools.py     # recommend_interim_care
│   │   │   └── mcp_client.py     # MCP HTTP client
│   │   └── api.py                # FastAPI (6 endpoints)
│   ├── langgraph.json            # LangGraph Studio config
│   └── requirements.txt          # Python dependencies
├── mcp_server/
│   ├── __init__.py
│   ├── server.py                 # MCP FastAPI server
│   └── data/
│       └── care_guidelines.json  # 10 medical conditions
├── frontend/
│   └── app.py                    # Streamlit (4 screens)
├── tests/
│   ├── __init__.py
│   ├── test_graph.py             # Graph tests
│   ├── test_api.py               # API tests
│   └── test_scenarios.py         # 3 clinical scenarios
├── .env.example                  # Environment template
├── rapport_technique.md          # Technical report (FR)
└── README.md                     # This file
```

---

**⚠️ Ce système ne remplace pas une consultation médicale. / This system does not replace a medical consultation.**
