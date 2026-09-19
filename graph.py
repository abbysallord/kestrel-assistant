import time
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from agents import AgentState, planner_node, retriever_node, verifier_node, synthesizer_node

def build_research_graph():
    """Builds and compiles the 4-agent LangGraph workflow for Kestrel Research Assistant."""
    builder = StateGraph(AgentState)

    # 1. Register Nodes
    builder.add_node("planner", planner_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("verifier", verifier_node)
    builder.add_node("synthesizer", synthesizer_node)

    # 2. Wire Linear Flow with explicit hand-off
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "retriever")
    builder.add_edge("retriever", "verifier")
    builder.add_edge("verifier", "synthesizer")
    builder.add_edge("synthesizer", END)

    return builder.compile()

# Global compiled graph
research_graph = build_research_graph()

# Simple in-memory response cache for repeated queries
_QUERY_CACHE: Dict[str, Dict[str, Any]] = {}

def clear_query_cache():
    """Clears the query response cache."""
    _QUERY_CACHE.clear()

def ask_kestrel(
    query: str,
    messages: List[Dict[str, str]] = None,
    mode: str = "baseline"
) -> Dict[str, Any]:
    """
    Main invocation entry point for the Multi-Agent Research Assistant.
    Supports multi-turn messages, caching, and dual verification mode (baseline vs jev).
    """
    if messages is None:
        messages = []

    # Cache lookup for repeated standalone queries
    clean_q = query.strip().lower()
    cache_key = f"{mode}::{clean_q}"

    if not messages and cache_key in _QUERY_CACHE:
        cached_result = dict(_QUERY_CACHE[cache_key])
        cached_result["cached"] = True
        cached_result["latency_seconds"] = 0.001
        return cached_result

    initial_state: AgentState = {
        "messages": messages,
        "query": query,
        "resolved_query": query,
        "sub_queries": [query],
        "retrieved_chunks": [],
        "verifier_verdict": "",
        "verifier_explanation": "",
        "answer": "",
        "citations": [],
        "mode": mode,
        "latency_seconds": 0.0
    }

    t0 = time.perf_counter()
    result = research_graph.invoke(initial_state)
    elapsed = round(time.perf_counter() - t0, 3)
    result["latency_seconds"] = elapsed
    result["cached"] = False

    # Store in cache if successful standalone answer
    if not messages and result.get("answer"):
        _QUERY_CACHE[cache_key] = dict(result)

    return result

if __name__ == "__main__":
    test_q = "What is the Beacon limit on the Starter plan?"
    print(f"[*] Asking: {test_q}")
    res = ask_kestrel(test_q)
    print(f"\n[+] Verdict: {res['verifier_verdict'].upper()}")
    print(f"[+] Citations: {res['citations']}")
    print(f"[+] Latency: {res['latency_seconds']}s")
    print(f"\n[+] Answer:\n{res['answer']}")
