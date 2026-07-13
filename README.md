# Triage Agent — RAG + Agentic Build Failure Diagnosis

A working reference implementation of an autonomous debugging agent: ingest a
build/CI failure event (from Kafka, see the Java producer/consumer you already
have), retrieve grounded context via hybrid RAG, reason over it with an
LLM-driven agent graph, and emit a diagnosis with a confidence score and a
citation trail back to source docs.

Each piece (chunking, retrieval, reranking, agent orchestration,
eval) is a separate, swappable module.

## Architecture

```
Kafka topic: build-failures
        │
        ▼
 ┌─────────────┐      ┌────────────────────┐      ┌──────────────────┐
 │  FastAPI     │─────▶│  Agent Graph        │─────▶│  Diagnosis +      │
 │  /diagnose   │      │  (LangGraph)        │      │  confidence score │
 └─────────────┘      └─────────┬──────────┘      └──────────────────┘
                                  │
                     ┌────────────┴─────────────┐
                     ▼                            ▼
            ┌─────────────────┐         ┌──────────────────┐
            │ Hybrid Retrieval │         │ Tools:            │
            │ (BM25 + vector   │         │ - log_parser       │
            │  + rerank)        │         │ - stacktrace_lookup│
            └─────────────────┘         │ - runbook_search    │
                     │                    └──────────────────┘
                     ▼
            ┌─────────────────┐
            │ Chroma vector DB │
            │ (docs, runbooks, │
            │  past incidents) │
            └─────────────────┘
```

**Agent graph flow** (`app/agent/graph.py`):

```
retrieve → diagnose → confidence_check ─┬─(high)─▶ propose_fix → END
                                          └─(low)──▶ escalate → END
```

This "confidence-gated escalation" pattern is the single most interview-relevant
design decision in this project: it demonstrates you understand that agentic
systems need a defined failure mode, not just a happy path. An agent that's
unsure should say so and hand off, not hallucinate a fix.

## Why these design choices (talking points)

- **Hybrid retrieval, not pure vector search**: stack traces and error codes
  are keyword-exact (BM25 wins), while "why does this happen" reasoning is
  semantic (embeddings win). `hybrid_search.py` combines both and reranks.
- **Grounding validation**: every claim in the diagnosis must cite a
  retrieved chunk ID. If the LLM asserts something with no supporting
  citation, the grounding check in `nodes.py::validate_grounding` flags it
  and routes to escalation instead of returning an ungrounded answer.
- **Small Kafka messages, pointer to full log**: matches the schema you
  already designed — `rawLogExcerpt` + `logStorageUrl`, not the whole log
  blob, in the agent's input.
- **Eval harness with a golden dataset**: `app/eval/golden_dataset.json` has
  labeled failure→root-cause pairs. `eval_harness.py` runs the agent against
  all of them and reports root-cause accuracy, citation precision, and
  escalation rate — the numbers you'd quote in an interview.
- **Java service stays the system of record**: Kafka producer/consumer
  (already built) owns ingestion and durability; this Python service is a
  stateless reasoning layer called over REST. This is a realistic
  polyglot pattern — Java for infra/durability, Python for the
  LangGraph/RAG ecosystem, which is where the tooling actually lives.

## Project layout

```
triage-agent/
├── app/
│   ├── main.py                 # FastAPI entrypoint, /diagnose endpoint
│   ├── config.py                # env-driven settings
│   ├── models/schemas.py        # Pydantic request/response models
│   ├── ingestion/chunker.py     # chunking strategy for docs/runbooks
│   ├── retrieval/
│   │   ├── vector_store.py      # Chroma wrapper
│   │   └── hybrid_search.py     # BM25 + vector + rerank
│   ├── agent/
│   │   ├── graph.py             # LangGraph state machine
│   │   └── nodes.py             # node implementations (retrieve/diagnose/etc)
│   └── eval/
│       ├── golden_dataset.json  # labeled test cases
│       └── eval_harness.py      # scoring script
├── tests/test_retrieval.py
├── requirements.txt
└── docker-compose.yml
```

## The polyglot bridge (`java-consumer/`)

The Kafka producer/consumer you already had is now wired end-to-end:

```
CI failure → Kafka (build-failures) → BuildFailureConsumer
    → TriageAgentService.handleFailure()
        → POST http://app:8000/diagnose   (RestClient, 15s timeout)
        → logs DIAGNOSED or ESCALATED, same shape either way
```

Key file: `java-consumer/src/main/java/com/dimpi/triage/service/TriageAgentService.java`.
Two things worth pointing at in an interview:

1. **DTOs mirror the Python Pydantic models field-for-field** (`RetrievedChunk`,
   `Diagnosis`, `DiagnoseResponse` in `service/dto/`), with `@JsonProperty`
   mapping the snake_case fields FastAPI returns onto idiomatic Java camelCase
   — no manual translation layer, no drift risk between the two services'
   contracts.
2. **The Java side is fail-open, matching the agent's own escalate pattern.**
   If the Python service is down or times out, `TriageAgentService` doesn't
   retry forever and stall the Kafka partition — it logs a forced escalation
   and moves on, the same downstream action as a low-confidence diagnosis.
   Reliability of the pipeline doesn't depend on the AI service being up.

Run the whole stack (Kafka + Chroma + Python agent + Java consumer) together:

```bash
docker compose up --build
```

Then publish a test event onto Kafka (e.g. via `kafka-console-producer` or a
short test in the Java module) and watch `triage-consumer` logs show either
`DIAGNOSED ...` or `ESCALATED ...`.

## Running it

```bash
cp .env.example .env        # add your ANTHROPIC_API_KEY or OPENAI_API_KEY
docker compose up --build
```

This starts Chroma (vector DB) and the FastAPI app on `localhost:8000`.

Seed it with a few runbooks/docs, then test:

```bash
curl -X POST localhost:8000/diagnose -H "Content-Type: application/json" -d '{
  "eventId": "evt-1",
  "repo": "enterprise-knowledge-assistant",
  "failureType": "DEPENDENCY_CONFLICT",
  "rawLogExcerpt": "Could not resolve com.fasterxml.jackson.core:jackson-databind:2.15.0..."
}'
```

Run the eval harness:

```bash
python -m app.eval.eval_harness
```
