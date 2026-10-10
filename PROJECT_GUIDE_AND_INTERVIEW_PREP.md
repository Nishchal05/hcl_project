# AI-Powered University Student Services Assistant
## Complete Technical Architecture, File-by-File Code Analysis & Interview Preparation Guide

---

## 📌 Executive Architecture & System Value

In university administration, returning hallucinated, outdated, or unauthorized information to a student can lead to severe consequences (e.g., falsely confirming exam eligibility or leaking another student's attendance). Traditional pure LLM chatbots suffer from three major vulnerabilities:

1. **Probabilistic Calculations**: LLMs struggle with basic math, percentage thresholds, and strict boolean rule evaluation.
2. **Policy Conflicts & Outdated Documents**: Universities release circulars that supersede old notices; standard RAG treats all chunks equally without date or authority awareness.
3. **Security & Data Leaks**: LLMs easily fall victim to prompt injection or natural-language cross-student data requests.

The **University Student Services Assistant** addresses these challenges through a hybrid architecture:
- **LangGraph** orchestrates the workflow graph state machine.
- **ChromaDB** performs vector retrieval on section-aware document chunks.
- **Pure Python** executes source precedence (authority, recency, supersession, effective date) and deterministic tools.
- **SQLite** maintains atomic student records, attendance, marks, rule registries, and audit trails.

---

## 🏗️ 1. Complete Tech Stack & Justifications

| Technology | Category | Why Selected & Advantage Over Alternatives |
|---|---|---|
| **FastAPI** | Backend Framework | Asynchronous performance, native Pydantic type safety, automatic OpenAPI documentation (`/docs`), lightweight dependency injection. |
| **LangGraph** | Agent Orchestration | Cyclical state machine control (`StateGraph`). Unlike standard linear LangChain chains, LangGraph allows explicit state routing, branch conditions, and step isolation. |
| **ChromaDB** | Vector Database | Persistent local vector database with embedding function abstraction. Perfect for embedded execution without requiring external cloud vector services. |
| **SQLite 3** | Relational DB | Embedded zero-config relational store with foreign key enforcement and CHECK constraints. Fast local persistence for student profiles, marks, and audit logs. |
| **Sentence Transformers** | Embedding Model | Uses `all-MiniLM-L6-v2` for 384-dimensional dense semantic vectors. Custom term-frequency SHA-256 fallback included for zero-dependency offline mock mode. |
| **React 18 + Vite** | Frontend Framework | Modern component-based UI with instant hot module replacement (HMR), TypeScript integration, and clean state handling. |
| **Pydantic v2** | Data Validation | Strict schema enforcement for request/response bodies, intent routes, and audit records with high-speed Rust-backed validation. |
| **Ollama / Llama 3.1** | LLM / Explainer Layer | Local open-weight LLM execution. Constrained purely to explaining computed evidence without deciding policies or calculating math. |
| **Pytest & Vitest** | Testing Frameworks | Backend unit and integration test suite (`test_core.py`) and frontend test runner for continuous quality assurance. |
| **ReportLab** | PDF Generation | Programmatic PDF generation engine for rendering complete project technical guides and interview documentation. |

---

## 📄 2. Exhaustive File-by-File Breakdown

### Core Backend (`backend/app/`)

- **`backend/app/main.py`** (*FastAPI Gateway*)
  - **Purpose**: Entry point for the backend REST API server.
  - **Key Logic**: Routes requests to `/ask`, `/ingest`, `/health`, `/audit/{trace_id}`, `/reindex`, `/sources`, `/rules`, and `/student/{id}`. Enforces header security via `require_student()`. Constructs structured SQLite audit records for every query.

- **`backend/app/graph.py`** (*LangGraph State Machine*)
  - **Purpose**: Orchestrates request processing across graph nodes (`StateGraph`).
  - **Key Nodes**:
    1. `router`: Normalizes query text, extracts course code regex (e.g., `CS201`), categorizes intent into 8 intents (`personal_data`, `personal_eligibility`, `exact_fact`, `procedure`, `policy_fact`, `multi_step`, `refused`, `not_answerable`).
    2. `retrieve_node`: Queries ChromaDB, matches exact sections, deduplicates identical content, and calls `source_precedence.resolve()`.
    3. `answer`: Invokes SQLite tools for personal data, extracts evidence sentences for policy queries, constructs hypothetical in-memory states for multi-step queries, or returns refusal/not_found.

- **`backend/app/policy/source_precedence.py`** (*Deterministic Policy Engine*)
  - **Purpose**: Pure Python 5-step policy ordering algorithm.
  - **Key Logic**:
    1. Applicability date filter (`effective_from <= as_of_date < effective_to`, programme, batch).
    2. Explicit supersession filter (removes documents superseded by newer ones).
    3. Authority level hierarchy rank (Level 1 Regulations > Level 2 Circulars > Level 3 Notices).
    4. Recency sorting by effective date.
    5. Conflict detection (flags equal-precedence documents for safe review).

- **`backend/app/tools.py`** (*Deterministic Database Tools*)
  - **Purpose**: Executes exact calculations against SQLite.
  - **Key Functions**: `profile(student_id)`, `attendance(student_id, course_code)` (computes `round(attended / held * 100, 2)`), `result(student_id, course_code)`, `rules(as_of_date)`, `_rule()`, and `eligibility()` (evaluates attendance threshold and result state). Supports hypothetical passes without database mutation.

- **`backend/app/rag.py`** (*Vector Store & Section Parser*)
  - **Purpose**: Manages ChromaDB collection `university_documents_v2`.
  - **Key Logic**: Embeddings class with Sentence Transformers or SHA-256 hashing fallback. `sections(text)` regex parser recognizing generic headers (e.g. `EXPERIMENT 1`, `SECTION 7`, `MODULE 3`). Chunking (`size=800`, `overlap=120`), `index_document()`, `remove_document()`, `rebuild()`, `search()`.

- **`backend/app/retrieval.py`** (*Keyword Fallback & Citation Formatter*)
  - **Purpose**: Handles search fallbacks and exact section extractions.
  - **Key Logic**: Keyword term scoring across SQLite documents when vector hits are sparse. `exact_section(question)` extracts full heading-delimited section blocks for exact matches. `citation()` formats citation metadata.

- **`backend/app/db.py`** (*SQLite Connection & Schema*)
  - **Purpose**: Defines database DDL and connection pool context manager `conn()`.
  - **Key Tables**: `students`, `courses`, `attendance`, `results`, `rule_registry`, `source_register`, `documents`, `audits`. Enforces CHECK constraints (`cgpa BETWEEN 0 AND 10`, `classes_attended <= classes_held`, `total_marks = internal + external`).

- **`backend/app/schemas.py`** (*Pydantic Models*)
  - **Purpose**: Type-safe Data Transfer Objects (DTOs).
  - **Models**: `AskRequest`, `Citation`, `ToolResult`, `AskResponse`, `Route`, `IngestResponse`.

- **`backend/app/seed.py`** (*Synthetic Database & Policy Initialization*)
  - **Purpose**: Populates initial database and vector index.
  - **Data**: Seeds 30 synthetic students (`S1001`–`S1030`), 6 courses (`CS201`, `CS202`, `EC201`, `EC202`, `HS201`, `MA201`), attendance rows, exam results, synthetic policy documents (`ACAD-REG-2023`, `ACAD-REG-2024`, `EXAM-RULES-2024`, `ATT-CIRCULAR-2024`, `CSE-NOTICE-2024`), and rule registry entries.

- **`backend/app/llm.py`** (*Explanation Layer*)
  - **Purpose**: Formats response text.
  - **Key Logic**: In `MOCK_LLM=true` mode, returns verified answer directly with zero external API calls. When `MOCK_LLM=false`, calls local Ollama endpoint (`llama3.1:8b`) with strict prompt constraints prohibiting document instruction execution or prompt leakage.

- **`backend/app/config.py`** (*Configuration Settings*)
  - **Purpose**: Centralized settings loaded via `dotenv`. Defines directory paths (`DATA_DIR`, `DB_PATH`, `CHROMA_PATH`), Ollama parameters, retrieval parameters (`TOP_K=5`, `MAX_UPLOAD_MB=20`), and `MOCK_LLM` toggle.

- **`backend/tests/test_core.py`** (*Pytest Core Suite*)
  - **Purpose**: Unit and integration test suite testing attendance determinism, supersession rules, equal source conflicts, audit trail generation, header authorization refusal, historical `as_of_date` filtering, future policy exclusion, what-if DB isolation, vector retrieval, and section parsing.

---

### Frontend Components (`frontend/`)

- **`frontend/src/main.tsx`** (*React App Component*)
  - **Purpose**: Interactive user dashboard interface.
  - **Key Features**: Student identity selector (`S1001`–`S1003`), question textarea, optional ISO `as_of_date` picker, example query shortcuts, fetch POST call to `/ask` with `X-Student-Id` header, rendering response badges, trace ID, latency, citations, applied rules, and formatted tool execution JSON.

- **`frontend/src/style.css`** (*Application Styling*)
  - **Purpose**: Custom CSS styling providing responsive flexbox layout, badge themes (green for retrieved/calculated, amber for not_found/refused, red for conflict_flagged), and dark code block styles.

- **`frontend/package.json`** (*NPM Manifest*)
  - **Purpose**: Defines frontend dependencies (`react`, `vite`, `typescript`, `vitest`).

---

### Root Configuration & Scripts (`scripts/`, Root)

- **`docker-compose.yml`**: Multi-container docker orchestration linking backend (port 8000 with volume `./data:/data`) and frontend (Nginx on port 5173).
- **`scripts/generate_project_guide.py`**: PDF documentation generator script built with ReportLab.
- **`evaluation/evaluate.py`**: System quality evaluator running 20 test cases from `evaluation/dataset.json`. Generates metrics for correctness %, citation accuracy %, tool correctness %, abstention accuracy %, top-k=3/5 hit rates, and P50/P95 latency.

---

## 🔄 3. Step-by-Step Request Execution Walkthrough

### Example Query: Student S1001 asks *"What is my attendance in CS201?"*

```
User (React UI) -> Selects S1001 -> Types Query -> Clicks "Ask Assistant"
  │
  ▼
Frontend (main.tsx)
  │ Sends POST to http://localhost:8000/ask
  │ Headers: { "Content-Type": "application/json", "X-Student-Id": "S1001" }
  │ Body: { "question": "What is my attendance in CS201?" }
  ▼
FastAPI Gateway (main.py)
  │ Calls require_student("S1001") -> Validates existence in SQLite
  │ Generates 12-char hex trace_id (e.g. 4a8f91b2c3d4)
  │ Starts high-resolution latency timer
  ▼
LangGraph State Machine (graph.py)
  │ 1. ROUTER NODE:
  │    - Normalizes question text to lowercase
  │    - Extracts course code "CS201" via regex
  │    - Matches phrase "my attendance" -> Intent = "personal_data"
  │
  │ 2. RETRIEVE NODE:
  │    - Skips policy retrieval for personal data queries
  │
  │ 3. ANSWER NODE:
  │    - Calls attendance("S1001", "CS201") in tools.py
  │    - SQLite Query: SELECT * FROM attendance WHERE student_id='S1001' AND course_code='CS201'
  │    - Result: classes_held=28, classes_attended=22
  │    - Calculation: round(22 / 28 * 100, 2) = 78.57%
  │    - Sets answer_type = "calculated"
  │    - Answer Text: "Your attendance in CS201 is 78.57% (22 attended / 28 held)."
  ▼
Explanation Layer (llm.py)
  │ MOCK_LLM = true -> Returns verified calculated answer directly (0ms LLM latency)
  ▼
Audit System (main.py)
  │ Inserts JSON trace into SQLite `audits` table (trace_id, timestamp, payload)
  ▼
Frontend Render (main.tsx)
  │ Displays Green Badge: "calculated"
  │ Displays Answer: "Your attendance in CS201 is 78.57% (22 attended / 28 held)."
  │ Displays Metadata: Trace 4a8f91b2c3d4 · 18 ms
  │ Displays Deterministic Tools Box: { "tool": "get_attendance", "result": {...} }
```

---

## 🎓 4. Comprehensive Interview Q&A List

### Q1: What is the core problem this project solves, and why is a hybrid RAG + Deterministic approach better than a pure LLM chatbot?
**Answer**: In university domain applications, answers must be zero-hallucination and strictly policy-compliant. Pure LLMs struggle with precise math (calculating attendance percentages), multi-document supersession, and authorization boundaries. Our project uses LangGraph for workflow routing, ChromaDB for vector retrieval, pure Python for source precedence and math tools, and SQLite for atomic data store. The LLM (or Mock engine) is restricted to explaining verified evidence, ensuring 100% accuracy.

### Q2: What is the role of LangGraph in this application compared to standard LangChain chains?
**Answer**: LangChain chains are linear sequences of calls. LangGraph provides a cyclic state machine (`StateGraph`). It allows conditional routing, state persistence, step-by-step node execution (Router -> Retrieve -> Answer), and explicit state validation between nodes. This ensures that intent classification, document retrieval, tool invocation, and evidence rendering happen in controlled, isolated steps.

### Q3: How does the system handle security and prevent cross-student data leaks?
**Answer**: Authentication is enforced via the HTTP `X-Student-Id` header validated against SQLite. If Student S1001 asks about S1002's attendance, the Router node identifies the target ID discrepancy and immediately sets `answer_type='refused'`, returning an authorization error. Prompt injections attempting to trick the LLM into revealing another student's data are neutralized because database queries are parameterized by the validated header ID, not natural language text.

### Q4: Explain how the Source Precedence Engine resolves conflicts between multiple policy documents.
**Answer**: The precedence engine (`app/policy/source_precedence.py`) executes a 5-step Python algorithm: 1) Filters documents valid on `as_of_date`. 2) Checks explicit supersession tags (if Doc B supersedes Doc A, A is removed). 3) Ranks by authority level (Level 1 Regulations beat Level 2 Circulars). 4) Selects the most recent `effective_from` date among ties. 5) If a tie remains, it flags `conflict_flagged` and cites both documents, avoiding guessing.

### Q5: Why is attendance percentage dynamically calculated in Python instead of stored in the database?
**Answer**: Storing calculated percentages in SQLite causes data drift whenever total `classes_held` increases. To maintain database normalization and data integrity, we store raw integers (`classes_attended` and `classes_held`) with check constraints (`classes_attended <= classes_held`). The `attendance()` tool calculates `round((attended / held) * 100, 2)` at runtime.

### Q6: What is section-aware chunking, and why was it necessary for documents like lab manuals?
**Answer**: Standard fixed-character chunking (e.g. 500 characters) cuts text indiscriminately, often splitting headings or mixing adjacent lab experiments. Our parser recognizes section patterns (e.g. `EXPERIMENT 1`, `SECTION 7`, `MODULE 3`) using regex, keeping heading units together. When an exact section is requested, the system returns that specific heading block rather than an arbitrary vector slice.

### Q7: How does the hypothetical 'what-if' examination evaluation work without corrupting student records?
**Answer**: When a user asks 'If I pass my supplementary exam, will I be eligible?', the graph classifies the query as `multi_step`. It calls the `eligibility()` tool passing `hypothetical_pass=True`. The tool evaluates rule thresholds against an in-memory dictionary copy of the student's status without issuing an UPDATE query to SQLite. The database remains untouched.

### Q8: How does document ingestion handle idempotent re-uploads?
**Answer**: When a document with an existing `doc_id` is re-uploaded via `POST /ingest`, the endpoint executes `DELETE FROM documents WHERE doc_id=?` and deletes all matching chunks from ChromaDB before indexing the new text. This prevents stale duplicate chunks from accumulating in the vector store.

### Q9: What is the purpose of the `as_of_date` parameter in `POST /ask`?
**Answer**: Policy rules and circulars have temporal validity (`effective_from` and `effective_to`). Passing an `as_of_date` allows historical or future policy evaluation (e.g., 'What was the rule in 2024?' or 'What will be the rule next semester?'). The precedence engine filters documents based on whether `effective_from <= as_of_date < effective_to`.

### Q10: What happens if Ollama / local LLM is offline or unavailable?
**Answer**: The project features a `MOCK_LLM=true` mode. In mock mode, the application uses an evidence-grounded fallback synthesizer and deterministic hashing embeddings. RAG retrieval, LangGraph routing, tool calculations, and audit logging function at 100% capacity with zero latency and zero reliance on external LLM APIs.

### Q11: Explain the structure of an audit log entry in this system.
**Answer**: Each request generates a 12-char hex `trace_id`. The audit JSON stored in SQLite records: trace_id, ISO timestamp, student_id, original question, intent type, as_of_date, retrieved source IDs, selected source IDs, precedence decision reason, tools invoked with inputs/outputs, applied rule IDs, answer type, model used, latency in ms, and final answer. Prompts and CoT are excluded.

### Q12: How does the system handle unanswerable queries like 'Scholarship amount for studying in Antarctica'?
**Answer**: The router identifies non-existent topics or ChromaDB retrieval fails to return chunks above the relevance threshold. The state machine sets `answer_type='not_found'` and returns 'I could not find this information in authoritative university sources.' This prevents hallucinated answers.

### Q13: How is database consistency maintained in SQLite?
**Answer**: We enable `PRAGMA foreign_keys=ON` and apply CHECK constraints across tables. For example: `cgpa BETWEEN 0 AND 10`, `classes_held > 0`, `classes_attended <= classes_held`, and `total_marks = internal_marks + external_marks`. Invalid inserts or updates are rejected at the database engine level.

### Q14: What vector embedding model is configured for ChromaDB?
**Answer**: The primary embedding model is `all-MiniLM-L6-v2` from Sentence Transformers (384-dimensional dense vectors). In lightweight demo/mock mode, a custom 128-dimensional SHA-256 term-frequency hashing vectorizer is used as a fallback.

### Q15: How does `POST /reindex` work?
**Answer**: If the chunking algorithm, overlap size, or embedding model is updated, calling `POST /reindex` fetches all original raw texts from the SQLite `documents` table, clears the Chroma collection, re-chunks all texts with updated settings, and re-embeds them into ChromaDB without requiring manual file re-uploads.

### Q16: How do you evaluate the quality of the system?
**Answer**: `evaluation/evaluate.py` runs 20 benchmark test cases covering policy facts, personal attendance, eligibility, authorization attempts, and unanswerable questions. It computes correctness %, citation accuracy %, tool result accuracy %, abstention accuracy %, retrieval hit rate @ k=3/5, and P50/P95 latency.

### Q17: What are the main limitations of pypdf during ingestion?
**Answer**: `pypdf` extracts text streams from digital PDFs. However, if a PDF contains scanned images of text or complex multi-column tables, `pypdf` returns empty or garbled text. For production, an OCR engine like Tesseract or Amazon Textract would be integrated.

### Q18: How does the frontend communicate with the backend?
**Answer**: The React frontend uses standard `fetch` HTTP requests to communicate with FastAPI. Authentication is passed via the custom header `X-Student-Id`. The response payload includes typed fields (`answer`, `citations`, `tool_results`, `trace_id`), enabling the UI to render source badges and tool execution boxes.

### Q19: How would you scale this architecture to support 100,000 active students?
**Answer**: 1) Replace SQLite with PostgreSQL (Amazon RDS) with read replicas. 2) Replace local ChromaDB with a distributed vector store like Qdrant or Milvus. 3) Deploy FastAPI on Kubernetes (EKS) behind an ALB. 4) Use Redis for session state and rate limiting. 5) Deploy Ollama or vLLM on dedicated GPU nodes.

### Q20: Why did you choose FastAPI over Flask or Django?
**Answer**: FastAPI provides native asynchronous async/await support, automatic Pydantic data validation, high performance (built on Starlette and Uvicorn), and auto-generated OpenAPI/Swagger documentation (`/docs`), making it ideal for modern microservices.

### Q21: How do you protect against SQL Injection?
**Answer**: All database queries in `tools.py`, `db.py`, and `main.py` use parameterized SQL queries with `?` placeholders (e.g. `c.execute('SELECT * FROM students WHERE student_id=?', (sid,))`). User input is never concatenated into raw SQL strings.

### Q22: What happens if a student has failing marks in a course but attendance above 75%?
**Answer**: The `eligibility()` tool evaluates both rules from `rule_registry`. Attendance rule requires `>= 75%`, result rule requires `result == 'FAIL'`. If both are satisfied, `eligible` is evaluated to `True` for the supplementary examination.

### Q23: How are duplicate uploads of the same text under different document IDs handled?
**Answer**: The `retrieve_node` in LangGraph computes a whitespace-normalized text fingerprint. Identical evidence uploaded under different IDs is recognized as a duplicate and collapsed to a single representative before reaching conflict resolution.

### Q24: What metric demonstrates the performance of retrieval?
**Answer**: The evaluation framework tests retrieval top-k precision. In our dataset benchmarks, Top-K=3 achieves a retrieval hit rate over 90%, with median response latency under 50ms in Mock mode.

### Q25: If asked: 'What was your biggest technical challenge in this project?', how should you answer?
**Answer**: "The biggest challenge was handling policy document supersession and date applicability. Standard vector search returns chunks based purely on semantic similarity, which often fetched old policy circulars instead of newly issued regulations. I solved this by building a custom Python Source Precedence Engine that metadata-filters retrieved chunks by effective date, authority tier, and explicit supersession tags before passing evidence to the response layer."

---

*AI-Powered University Student Services Assistant — End-to-End Master Technical & Interview Guide*
