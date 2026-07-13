"""
Node implementations for the triage agent graph. Each node takes and
returns the shared state dict (LangGraph convention) — this keeps nodes
independently testable, which is what your eval harness exercises.
"""
import json
import re
from typing import TypedDict

from app.agent.llm_client import call_llm
from app.config import settings
from app.retrieval.hybrid_search import HybridSearcher


class AgentState(TypedDict, total=False):
    eventId: str
    failureType: str
    rawLogExcerpt: str
    affectedModule: str
    retrieved_chunks: list[dict]
    root_cause: str
    proposed_fix: str
    confidence: float
    citations: list[str]
    escalated: bool
    escalation_reason: str


def make_retrieve_node(searcher: HybridSearcher):
    def retrieve(state: AgentState) -> AgentState:
        query = f"{state['failureType']}: {state['rawLogExcerpt']}"
        chunks = searcher.search(query, top_k=5)
        state["retrieved_chunks"] = chunks
        return state

    return retrieve


DIAGNOSE_SYSTEM_PROMPT = """You are a senior build/CI diagnostics engineer.
Given a build failure and retrieved context chunks, identify the root cause
and a proposed fix. You MUST ground every factual claim in the provided
chunks and cite the chunk_id for each claim.

Respond ONLY with JSON, no other text, in this exact shape:
{
  "root_cause": "...",
  "proposed_fix": "...",
  "confidence": 0.0-1.0,
  "citations": ["chunk_id1", "chunk_id2"]
}

If the retrieved context does not contain enough information to confidently
diagnose the failure, set confidence low (below 0.5) rather than guessing."""


def diagnose(state: AgentState) -> AgentState:
    context_block = "\n\n".join(
        f"[{c['chunk_id']}] (source: {c['source']})\n{c['text']}"
        for c in state.get("retrieved_chunks", [])
    )
    user_prompt = f"""Failure type: {state['failureType']}
Affected module: {state.get('affectedModule', 'unknown')}
Log excerpt:
{state['rawLogExcerpt']}

Retrieved context:
{context_block if context_block else '(no relevant context retrieved)'}
"""
    raw = call_llm(DIAGNOSE_SYSTEM_PROMPT, user_prompt)
    parsed = _safe_parse_json(raw)

    state["root_cause"] = parsed.get("root_cause", "Unable to determine root cause")
    state["proposed_fix"] = parsed.get("proposed_fix", "")
    state["confidence"] = float(parsed.get("confidence", 0.0))
    state["citations"] = parsed.get("citations", [])
    return state


def validate_grounding(state: AgentState) -> AgentState:
    """Grounding check: every cited chunk_id must actually exist in what was
    retrieved. An LLM citing a chunk_id it invented is treated the same as
    an ungrounded claim — confidence gets clamped down."""
    retrieved_ids = {c["chunk_id"] for c in state.get("retrieved_chunks", [])}
    cited_ids = set(state.get("citations", []))

    if not cited_ids:
        # No citations at all on a non-trivial diagnosis is itself a signal
        state["confidence"] = min(state.get("confidence", 0.0), 0.4)
    elif not cited_ids.issubset(retrieved_ids):
        # Hallucinated citation — don't trust the diagnosis
        state["confidence"] = min(state.get("confidence", 0.0), 0.3)
        state["citations"] = [c for c in cited_ids if c in retrieved_ids]

    return state


def confidence_router(state: AgentState) -> str:
    return (
        "propose_fix"
        if state.get("confidence", 0.0) >= settings.confidence_threshold
        else "escalate"
    )


def propose_fix(state: AgentState) -> AgentState:
    state["escalated"] = False
    return state


def escalate(state: AgentState) -> AgentState:
    state["escalated"] = True
    state["escalation_reason"] = (
        f"Confidence {state.get('confidence', 0.0):.2f} below threshold "
        f"{settings.confidence_threshold}; routing to human review."
    )
    # In production: fire a tool call here — open a ticket, page on-call, etc.
    return state


def _safe_parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {"root_cause": raw.strip()[:300], "confidence": 0.0, "citations": []}
