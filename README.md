# Clinical Codes Finder

Agentic clinical coding search across ICD-10-CM, LOINC, RxTerms, HCPCS, UCUM, and HPO using Clinical Tables APIs.

## Key Features
- **Agentic RAG Engine**: LangGraph workflow with an LLM refiner node to self-correct searches if they fail.
- **Premium Visual Design**: An intuitive chat interface built with modern CSS glassmorphism.
- **Fully Asynchronous Execution**: High-concurrency scaling using `asyncio` for parallel API and LLM operations.
- **Dynamic Control Flow**: Automatically restricts or broadens API result volume based on the LLM's confidence score.

## 1) Setup

```bash
cd clinical-codes-finder
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your key in `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

## 2) Run

```bash
PYTHONPATH=. uvicorn app.main:app --reload
```

Open API docs:

- http://127.0.0.1:8000/docs
- Chat-style UI: http://127.0.0.1:8000/

## 3) Test

```bash
OPENAI_API_KEY='' PYTHONPATH=. pytest -q
```

## 4) Example request

```bash
curl -X POST http://127.0.0.1:8000/find-codes \
  -H "Content-Type: application/json" \
  -d '{"query":"metformin 500 mg","max_per_system":5}'
```

## Notes

- The graph has nodes for intent -> plan -> tool calls -> sanitize -> summary.
- If no OpenAI key is present, summarization falls back to a deterministic text summary.
- Ranking is a starter heuristic and can be improved for better relevance.
- Chatbot-style UI is available at `/`.
- Query normalization includes generalized typo handling with a controlled vocabulary.
- Potential PII/PHI in result text is masked before summarization/output.

## How to Run (Quick)

```bash
cd /Users/shivanipagadala/clinical-codes-finder
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# add OPENAI_API_KEY in .env
PYTHONPATH=. uvicorn app.main:app --reload
```

Open:
- Chatbot UI: http://127.0.0.1:8000/
- API docs: http://127.0.0.1:8000/docs

Optional test command:

```bash
OPENAI_API_KEY='' PYTHONPATH=. pytest -q
```

## Sample Prompt Results Summary

| Query | Expected Focus | Observed Focus |
| --- | --- | --- |
| `diabetes` | ICD-10-CM | ICD10CM |
| `glucose test` | LOINC | LOINC |
| `metformin 500 mg` | RxTerms / RxNorm | RXTERMS (and UCUM selected) |
| `wheelchair` | HCPCS | HCPCS |
| `mg/dL` | UCUM | UCUM (and RXTERMS selected) |
| `ataxia` | HPO | HPO |
| `tuberculosis` | ICD-10-CM | ICD10CM |
