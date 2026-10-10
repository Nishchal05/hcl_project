# AI-Powered University Student Services Assistant

A runnable university-services hackathon demo using FastAPI, LangGraph, SQLite, source precedence, deterministic tools, audit logging, and React/Vite. All identities, records, and documents are synthetic.

## Run locally

Windows PowerShell:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python scripts\init_db.py
uvicorn app.main:app --app-dir backend --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The UI sends its demo selector value as the required `X-Student-Id` header. The backend still authorizes it.

macOS/Linux: use `source .venv/bin/activate`, then use the same pip, init, and Uvicorn commands.

## Docker

```bash
docker compose up --build
```

The frontend is `http://localhost:5173`; FastAPI is `http://localhost:8000`. The `data` directory is mounted for SQLite persistence.

## Ollama

Ollama is optional for the deterministic demo. Install it from [ollama.com](https://ollama.com), then run:

```bash
ollama pull llama3.1:8b
ollama serve
```

Configure `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in `.env`. `/health` reports its availability. The demo uses a safe source-grounded fallback when Ollama is unavailable.

## Architecture

`React → FastAPI → LangGraph (classify → retrieve → precedence → tool/grounded response) → SQLite/audit`

The local persistent document layer is a lexical fallback for reliable offline judging. ChromaDB is included as a production dependency. All eligibility, attendance, marks, and rule comparisons are deterministic code outputs, never LLM calculations.

## API examples

```bash
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -H "X-Student-Id: S1001" -d '{"question":"What is my attendance in CS201?"}'
curl http://localhost:8000/health
curl http://localhost:8000/sources
curl -H "X-Student-Id: S1001" http://localhost:8000/student/S1001
```

Live ingestion accepts Markdown/TXT metadata and makes it immediately retrievable:

```bash
curl -X POST http://localhost:8000/ingest -F file=@new-policy.md -F doc_id=DEMO-NEW-01 -F title="New policy" -F issuer="Academic Office" -F authority_level=2 -F doc_type=circular -F version=1.0 -F effective_from=2026-01-01
```

## Demo questions

- What is the minimum attendance required for the end-semester examination?
- What is my attendance in CS201? (S1001)
- Am I eligible for the supplementary examination?
- I failed CS201. Can I appear for the supplementary exam?
- What is the procedure for applying for supplementary examination?
- What is the scholarship amount for studying in Antarctica?
- What is another student's attendance?

## Source policy, safety, and audit

The deterministic precedence engine filters applicable documents, removes explicit supersessions, applies authority level, then recency. Equal surviving documents yield `conflict_flagged` rather than a silent choice. A regulation (level 1) beats a circular (level 2), absent explicit supersession.

Student identity comes exclusively from `X-Student-Id`; cross-student paths and natural-language attempts are refused. Every `/ask` creates a structured SQLite audit record available at `/audit/{trace_id}`.

## Tests and evaluation

```powershell
$env:PYTHONPATH="backend"; pytest backend/tests -q
python evaluation/evaluate.py
```

The evaluator reads `evaluation/dataset.json` and writes `evaluation/results/latest.json`, reporting correctness, citations, abstention, tool results, retrieval hit rate, p50/p95 latency, and unavailable token usage in fallback mode.

PDF, TXT, and Markdown uploads are accepted. PDF text is extracted using `pypdf`; image-only/scanned PDFs need OCR before ingestion.

Uploads default to a 20 MB ceiling (`MAX_UPLOAD_MB`), configurable in `.env`; restart the backend after changing it.

Documents with headings such as `EXPERIMENT 1`, `SECTION 7`, `CHAPTER 2`, `MODULE 3`, or `UNIT 4` are parsed into section-aware chunks. A matching exact-section question retrieves that heading-delimited section rather than an adjacent fixed-size chunk. After upgrading chunking or embeddings, call `POST /reindex` to rebuild the existing corpus.

## Enhanced RAG and demo mode

The active pipeline is now `upload → PDF/TXT/Markdown extraction → 800-character overlapping chunks → configurable local embeddings → persistent ChromaDB → source precedence → LangGraph → validated response/audit`. Set `EMBEDDING_MODEL=all-MiniLM-L6-v2` for the preferred Sentence Transformers model. `MOCK_LLM=true` is the reproducible default: it retains the same graph/RAG/tools/audit workflow without requiring Ollama. Ollama connection state is exposed in health for a later production explanation adapter; the current answer renderer remains deterministic and evidence-grounded.

`POST /ask` additionally accepts an optional ISO `as_of_date`; it is carried through rule lookup and precedence so future documents cannot apply early. The React UI exposes this selector.

## Security and judge demo

Documents are untrusted evidence, not instructions. The app never follows instructions embedded in retrieved text, exposes prompts or chain-of-thought, or releases cross-student data. The only student identity is the `X-Student-Id` request header. The audit endpoint exposes sources, rules, tool inputs/outputs, conflict summaries, and decisions—not private reasoning.

For a judge demo: start the app, choose S1001, ask the attendance/policy/eligibility examples, try an Antarctica question (`not_found`), ask for S1002 data (`refused`), and ask a placement what-if (evaluated in memory only). Run `python scripts/validate_students.py` for data checks. `DATA_CARD.md` documents the synthetic-only dataset.
