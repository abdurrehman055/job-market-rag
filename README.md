# JobsRAG PK

**Pakistani Job Market Intelligence** — a RAG (Retrieval-Augmented Generation) web application that lets you upload job postings, ask natural-language questions across them, and match your CV against real market requirements.

---

## Features

- **Upload & index** job postings — text is chunked, embedded, and stored in ChromaDB
- **Search & Ask** — semantic search across all postings with GPT-4o-mini answers
- **CV Match Analyzer** — compare your CV against postings; get a match score, missing skills, and actionable recommendations
- **Dashboard analytics** — top in-demand skills, posting count, indexed chunk stats
- **Duplicate prevention** — identical postings are detected and rejected before indexing
- **Graceful error handling** — invalid API keys, rate limits, empty stores, and connection failures all surface clean user messages
- **Monochrome dark UI** — Apple × Linear × Notion-inspired design with amber accent

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI |
| Templating | Jinja2 + Bootstrap 5 |
| Vector store | ChromaDB (persistent, cosine similarity) |
| Embeddings | OpenAI `text-embedding-ada-002` |
| LLM | OpenAI `gpt-4o-mini` |
| Database | PostgreSQL via SQLAlchemy |
| Server | Uvicorn (ASGI) |

---

## Architecture

```
User browser
     │
     ▼
FastAPI (main.py)
     │
     ├── /upload     → PostgreSQL (JobPosting) + ChromaDB (vectors)
     ├── /dashboard  → PostgreSQL read + skill frequency analysis
     ├── /search     → ChromaDB semantic search → GPT-4o-mini
     └── /cv-match   → ChromaDB semantic search → GPT-4o-mini
```

**RAG pipeline:**
1. Job text is split into 500-character chunks with 50-character overlap
2. Each chunk is embedded via `text-embedding-ada-002` (batch call)
3. Vectors stored in ChromaDB with metadata (company, role, posting_id)
4. At query time: embed the query → cosine similarity search → deduplicate by posting → send top chunks as context to GPT-4o-mini

---

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 14+ running locally
- An OpenAI API key

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-username/job-market-rag.git
cd job-market-rag

# 2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your environment variables
cp .env.example .env
# Edit .env and fill in your values (see Setup below)
```

---

## Setup

Copy `.env.example` to `.env` and configure:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/job_market_rag
```

Create the PostgreSQL database:

```sql
CREATE DATABASE job_market_rag;
```

The application creates the `job_postings` table automatically on first run via SQLAlchemy `create_all`.

---

## Usage

```bash
# Start the development server
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) — you will be redirected to the dashboard.

### Workflow

1. **Upload** — go to `/upload`, paste a job posting (company name, role, full text)
2. **Dashboard** — view all indexed postings and top in-demand skills
3. **Search & Ask** — go to `/search`, ask any question ("What skills appear most?", "Write a cover letter for the Django role")
4. **CV Match** — go to `/cv-match`, paste your CV text, get a match score and missing skills

---

## Screenshots

### Dashboard
![Dashboard](screenshots/dashboard.png)

### Upload Job Posting
![Upload](screenshots/upload.png)

### Search & Ask
![Search](screenshots/search.png)

### CV Match Analyzer
![CV Match](screenshots/cv-match.png)

---

## Project Structure

```
job-market-rag/
├── main.py              # FastAPI app, lifespan, router registration
├── database.py          # SQLAlchemy models, get_db, hash_text
├── vector_store.py      # ChromaDB ops: chunk, embed, search, deduplicate
├── llm_service.py       # OpenAI wrapper with typed error handling
├── routes/
│   ├── dashboard.py     # Analytics + posting list + delete
│   ├── upload.py        # Upload form + duplicate detection
│   ├── search.py        # Semantic search + GPT Q&A
│   └── cv_match.py      # CV analysis + match scoring
├── templates/
│   ├── base.html        # Sidebar layout
│   ├── dashboard.html
│   ├── upload.html
│   ├── search.html
│   └── cv_match.html
├── static/
│   └── style.css        # Custom dark theme (monochrome + amber)
├── requirements.txt
└── .env.example
```

---

## Future Improvements

- [ ] PDF/DOCX upload support for job postings and CVs
- [ ] Alembic migrations for schema changes
- [ ] Multi-user support with authentication
- [ ] Export dashboard analytics as CSV/PDF
- [ ] Automatic skill taxonomy normalization (e.g. "JS" → "JavaScript")
- [ ] Job posting scraper (LinkedIn, Rozee.pk, Mustakbil)
- [ ] Deployment guide (Docker + Railway/Render)
- [ ] Test suite (pytest + httpx)

---

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI secret key |
| `DATABASE_URL` | PostgreSQL connection string |

**Never commit your `.env` file.** It is listed in `.gitignore`.
