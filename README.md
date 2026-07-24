# AIVOA — AI-Powered Customer Complaint Management System

Round 1 Full Stack Developer Assessment for AIVOA. An AI-assisted intake system for
pharmaceutical customer complaints: drop/paste a raw complaint document and an LLM
extraction pipeline fills out the structured QA complaint form, flags completeness,
suggests risk/priority, checks for duplicates, and summarizes it — with a chat assistant
alongside for asking questions about the complaint.

Full architecture, data model, and design rationale: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

## Stack

React + Redux Toolkit · FastAPI · LangGraph · Groq (`llama-3.1-8b-instant` / `llama-3.3-70b-versatile`) · PostgreSQL

## Setup

### 1. Database

```bash
docker compose up -d
```

Starts Postgres on `localhost:5432` (user/db/password: `aivoa`). Tables are created
automatically on backend startup — no migration step needed.

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1    # Windows PowerShell
# .venv\Scripts\activate.bat  # Windows cmd.exe
# source .venv/bin/activate   # macOS/Linux/Git Bash
pip install -r requirements.txt
cp .env.example .env          # macOS/Linux/Git Bash; then fill in GROQ_API_KEY
# copy .env.example .env      # Windows cmd.exe; then edit .env and fill in GROQ_API_KEY
uvicorn app.main:app --reload --port 8000
```

Get a Groq API key at https://console.groq.com. Runs at `http://localhost:8000`
(`/api/health` for a liveness check).

Run tests: `pytest` (from `backend/`).

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`, proxying `/api/*` to the backend (see
`vite.config.ts`) — no CORS setup needed in dev.

## How it works

1. Drop a complaint document (PDF/DOCX/TXT/EML, ≤10MB) or paste text into the AI
   Intake Assistant panel.
2. A LangGraph pipeline (`backend/app/agents/extraction_graph.py`) parses it, extracts
   structured fields via Groq, scores completeness, suggests severity/priority, checks
   for duplicates against saved complaints, and summarizes — streaming progress to the
   UI as each step completes.
3. Review/edit the auto-filled form, then **Save Complaint** to persist it.
4. Ask the AI Assistant questions about the complaint at any point during intake — it
   answers from the current form context, not a saved record (works before you save).

## Project layout

```
backend/app/    FastAPI app: api/ (routes), agents/ (LangGraph + Groq), db/, services/
frontend/src/   React app: features/ (form + AI intake), api/ (RTK Query + SSE), pages/
docker-compose.yml   Postgres only — backend/frontend run natively for fast iteration
IMPLEMENTATION_PLAN.md   Full architecture, schema, and design decisions
```

## Scope notes

Built for a graded take-home, not production: no auth (single-user demo), no DB
migrations tool (single schema), no vector DB (duplicate detection is a fuzzy text
match, sufficient at demo scale), no production OCR. Full reasoning in
[IMPLEMENTATION_PLAN.md §9](IMPLEMENTATION_PLAN.md#9-explicitly-out-of-scope-and-why).
