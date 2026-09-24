# AI Document Search — Enterprise RAG Chatbot

A full-stack, production-quality RAG application built with **FastAPI**, **React**, **LangChain**, **LangGraph**, **ChromaDB**, and **PostgreSQL**.

---

## Project Structure

```
myprojectsin/
├── backend/            # FastAPI Python backend
│   ├── app/
│   │   ├── api/v1/     # Auth, Documents, Chat routers
│   │   ├── core/       # Config, Security, Logger, Dependencies, Exceptions
│   │   ├── db/         # SQLAlchemy models + async session
│   │   ├── schemas/    # Pydantic v2 request/response models
│   │   ├── services/   # AuthService, DocumentService, ChatService
│   │   ├── repositories/ # BaseRepository + domain repos
│   │   ├── ai/         # Extractors, Chunker, Embeddings, VectorStore, LangGraph Workflow
│   │   └── main.py     # FastAPI app entry point
│   ├── alembic/        # Database migrations
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
└── frontend/           # React + Vite + TailwindCSS
    ├── src/
    │   ├── pages/      # Login, Register, Dashboard, Chat
    │   ├── hooks/      # useAuth, useDocuments, useChats
    │   ├── services/   # Axios API client
    │   └── routes/     # React Router config
    ├── package.json
    └── vite.config.ts
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ running locally
- A [Google AI Studio](https://aistudio.google.com/) API key (for Gemini)

---

## Backend Setup

```powershell
# 1. Enter the backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1    # Windows PowerShell
# or: source venv/bin/activate  # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Open .env and fill in:
#   POSTGRES_DSN  — e.g. postgresql+asyncpg://postgres:password@localhost:5432/docapp
#   JWT_SECRET_KEY — any long random string
#   GEMINI_API_KEY — from Google AI Studio

# 5. Create the PostgreSQL database
# (run in psql or pgAdmin)
# CREATE DATABASE docapp;

# 6. Run Alembic migrations (creates all tables)
alembic upgrade head

# 7. Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at **http://localhost:8000/docs**

---

## Frontend Setup

```powershell
# From the project root
cd frontend

# Install dependencies (if not already done)
npm install

# Start the dev server
npm run dev
```

App available at **http://localhost:5173**

The Vite proxy forwards `/api/*` requests to the backend automatically — no CORS issues.

---

## First-Time Usage

1. Open **http://localhost:5173**
2. Click **Register here** to create an account
3. You'll land on the **Dashboard** — upload a PDF, DOCX, or TXT file
4. Wait for the upload to finish (the file is chunked and embedded locally)
5. Click **+ New Chat** in the sidebar
6. Ask a question about your document — the AI will answer with citations

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, TailwindCSS, React Query, React Router |
| Backend | Python 3.11, FastAPI, SQLAlchemy (async), Pydantic v2, Alembic |
| Auth | JWT (argon2 password hashing, access + refresh tokens) |
| Database | PostgreSQL 15 |
| Vector DB | ChromaDB (local persistent) |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` (runs locally, free) |
| LLM | Google Gemini 1.5 Flash |
| AI Framework | LangChain + LangGraph |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/refresh` | Refresh JWT tokens |
| GET | `/api/v1/auth/me` | Get current user |
| POST | `/api/v1/documents` | Upload document |
| GET | `/api/v1/documents` | List documents |
| DELETE | `/api/v1/documents/{id}` | Delete document |
| POST | `/api/v1/chat` | Create new chat |
| GET | `/api/v1/chat` | List all chats |
| GET | `/api/v1/chat/{id}` | Get chat + messages |
| DELETE | `/api/v1/chat/{id}` | Delete chat |
| POST | `/api/v1/chat/{id}/message` | Send message (RAG) |
| GET | `/api/v1/health` | Health check |

---

## Architecture Highlights

- **Repository Pattern** — services never touch SQLAlchemy directly
- **Dependency Injection** — all services built via FastAPI `Depends()`
- **LangGraph Workflow** — RAG pipeline as a compiled state graph: `retrieve → build_prompt → generate`
- **Multi-tenant isolation** — ChromaDB filtered by `user_id` metadata per query
- **Chunk/Vector sync** — chunk UUIDs are used as Chroma IDs to prevent duplication
- **Argon2 hashing** — memory-hard password security
- **Token type enforcement** — refresh tokens cannot be used as access tokens
