# Medical Clinical Orientation Workflow - Multi-Agent SMA

## Francais

### Presentation

Systeme multi-agents (SMA) d'orientation clinique preliminaire construit avec LangGraph, LangChain, FastAPI, MCP, Streamlit et Groq. Ce projet est un exercice strictement academique; il ne constitue pas un dispositif medical.

**Ce systeme ne remplace pas une consultation medicale.**

### Architecture

```text
START -> SUPERVISOR -> DIAGNOSTIC_AGENT (5 questions)
              |
              +-> PHYSICIAN_REVIEW (HITL)
              |
              +-> REPORT_AGENT (rapport final)
              |
              +-> FINISH

FastAPI API  <->  Streamlit UI
    |
    +-> MCP Server (lignes directrices)
```

Services par defaut:

- FastAPI: `http://localhost:8000`
- MCP server: `http://localhost:8001`
- Streamlit: `http://localhost:8501`

Si le port `8000` est deja occupe, vous pouvez lancer FastAPI sur un autre port, par exemple `8010`, puis mettre `API_BASE_URL=http://localhost:8010` dans `.env`.

### Prerequis

- Python 3.11+
- Cle API Groq: https://console.groq.com
- pip

### Installation

```powershell
cd C:\Users\NITRO\Downloads\medical-sma-project

# Si la commande python n'est pas disponible sous Windows:
$PY="$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
& $PY -m venv venv

.\venv\Scripts\Activate.ps1
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt

Copy-Item .env.example .env
```

Editez ensuite `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8001
API_BASE_URL=http://localhost:8000
```

Le modele LLM est lu automatiquement depuis `.env` via `backend/app/config.py`.

### Lancement

Terminal 1 - MCP server:

```powershell
.\venv\Scripts\python.exe -m uvicorn mcp_server.server:app --port 8001
```

Terminal 2 - FastAPI:

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.app.api:app --host 0.0.0.0 --port 8000 --reload
```

Si le port `8000` reste bloque ou deja utilise, lancez plutot:

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.app.api:app --host 0.0.0.0 --port 8010 --reload
```

Dans ce cas, mettez aussi a jour votre fichier `.env`:

```env
API_BASE_URL=http://localhost:8010
```

Terminal 3 - Streamlit:

```powershell
.\venv\Scripts\streamlit.exe run frontend/app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Ouvrir l'application:

```text
http://localhost:8501
```

Documentation Swagger:

```text
http://localhost:8000/docs
```

### Fonctionnalites principales

- Questionnaire patient en 5 questions obligatoires
- Synthese clinique preliminaire via Groq
- Recommandation intermediaire avec appui MCP
- Revue medecin Human-in-the-Loop
- Rapport final structure
- Telechargement PDF professionnel du rapport final
- ID de session conserve dans le rapport PDF

### Tests

```powershell
.\venv\Scripts\python.exe -m pytest tests\ -v
```

La suite couvre notamment:

- Compilation et routage LangGraph
- Endpoints FastAPI
- Avancement Q1 -> Q2 du questionnaire
- Matching MCP
- Trois scenarios cliniques academiques

### Scenarios de test

1. Syndrome respiratoire simple: toux seche, 3 jours -> urgence medium
2. Red flags cardiovasculaires: douleur thoracique intense -> urgence high
3. Cas benin: fatigue legere -> urgence low

### Avertissement ethique

Ce systeme est une simulation academique. Il ne constitue pas un avis medical professionnel et ne doit jamais etre utilise pour des decisions medicales reelles.

---

## English

### Overview

Multi-agent system (MAS) for preliminary clinical orientation built with LangGraph, LangChain, FastAPI, MCP, Streamlit, and Groq. This project is strictly academic and is not a medical device.

**This system does not replace a medical consultation.**

### Default Services

- FastAPI: `http://localhost:8000`
- MCP server: `http://localhost:8001`
- Streamlit: `http://localhost:8501`

If port `8000` is already occupied, run FastAPI on another port such as `8010` and set `API_BASE_URL=http://localhost:8010` in `.env`.

### Installation

```powershell
cd C:\Users\NITRO\Downloads\medical-sma-project

$PY="$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
& $PY -m venv venv

.\venv\Scripts\Activate.ps1
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt

Copy-Item .env.example .env
```

Configure `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8001
API_BASE_URL=http://localhost:8000
```

### Running

Terminal 1:

```powershell
.\venv\Scripts\python.exe -m uvicorn mcp_server.server:app --port 8001
```

Terminal 2:

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.app.api:app --host 0.0.0.0 --port 8000 --reload
```

If port `8000` is blocked or already used, run:

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.app.api:app --host 0.0.0.0 --port 8010 --reload
```

Then update your real `.env`:

```env
API_BASE_URL=http://localhost:8010
```

Terminal 3:

```powershell
.\venv\Scripts\streamlit.exe run frontend/app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Open:

```text
http://localhost:8501
```

### Project Structure

```text
project/
├── backend/
│   ├── app/
│   │   ├── api.py
│   │   ├── config.py
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── nodes/
│   │   └── tools/
│   ├── langgraph.json
│   └── requirements.txt
├── frontend/
│   └── app.py
├── mcp_server/
│   ├── server.py
│   └── data/care_guidelines.json
├── tests/
├── .env.example
├── rapport_technique.md
└── README.md
```

### Disclaimer

This is an academic simulation. It is not professional medical advice and must not be used for real medical decisions.
