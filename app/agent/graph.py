from langgraph.graph import StateGraph, END

from app.agent.nodes import (
    AgentState,
    confidence_router,
    diagnose,
    escalate,
    make_retrieve_node,
    propose_fix,
    validate_grounding,
)
from app.retrieval.hybrid_search import HybridSearcher


def build_triage_graph(searcher: HybridSearcher):
    """
    Flow:
        retrieve -> diagnose -> validate_grounding -> [confidence gate]
            -> propose_fix -> END      (confidence >= threshold)
            -> escalate -> END          (confidence < threshold)
    """
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", make_retrieve_node(searcher))
    graph.add_node("diagnose", diagnose)
    graph.add_node("validate_grounding", validate_grounding)
    graph.add_node("propose_fix", propose_fix)
    graph.add_node("escalate", escalate)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "diagnose")
    graph.add_edge("diagnose", "validate_grounding")
    graph.add_conditional_edges(
        "validate_grounding",
        confidence_router,
        {"propose_fix": "propose_fix", "escalate": "escalate"},
    )
    graph.add_edge("propose_fix", END)
    graph.add_edge("escalate", END)

    return graph.compile()
