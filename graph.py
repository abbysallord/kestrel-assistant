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

def ask_kestrel(
    query: str,
    messages: List[Dict[str, str]] = None,
    mode: str = "baseline"
) -> Dict[str, Any]:
    """
    Main invocation entry point for the Multi-Agent Research Assistant.
    Supports multi-turn messages and dual verification mode (baseline vs jev).
    """
    if messages is None:
        messages = []

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

    return result

if __name__ == "__main__":
    test_q = "What is the Beacon limit on the Starter plan?"
    print(f"[*] Asking: {test_q}")
    res = ask_kestrel(test_q)
    print(f"\n[+] Verdict: {res['verifier_verdict'].upper()}")
    print(f"[+] Citations: {res['citations']}")
    print(f"[+] Latency: {res['latency_seconds']}s")
    print(f"\n[+] Answer:\n{res['answer']}")
