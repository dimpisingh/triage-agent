# Triage Agent — RAG + Agentic Build Failure Diagnosis

A working reference implementation of the autonomous debugging agent: ingest a
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
