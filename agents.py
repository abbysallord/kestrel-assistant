import os
import re
import json
import time
from typing import TypedDict, List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from vector_store import retrieve_evidence

load_dotenv()

# Always temperature=0.0 on Groq for determinism and reliable tool calling
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY")

llm = ChatGroq(model="qwen/qwen3.8-27b", temperature=0.0, max_tokens=500)

def safe_llm_invoke(messages):
    """Invokes the LLM with exponential backoff on HTTP 429 rate limit errors (Free Tier safety)."""
    for attempt in range(5):
        try:
            return llm.invoke(messages)
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate_limit" in err_str:
                wait_sec = (2 ** attempt) + 1.5
                time.sleep(wait_sec)
            else:
                raise e
    return llm.invoke(messages)

# Optional LangSmith tracing setup
if os.getenv("LANGSMITH_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ.setdefault("LANGCHAIN_PROJECT", "kestrel-research-assistant")


# =============================================================
# State Definition
# =============================================================
class AgentState(TypedDict):
    messages: List[Dict[str, str]]          # Multi-turn history: [{"role": "user"|"assistant", "content": str}]
    query: str                             # Current turn query
    resolved_query: str                    # Query after resolving multi-turn context
    sub_queries: List[str]                 # Decomposed sub-queries for multi-hop
    retrieved_chunks: List[Dict[str, Any]] # Retrieved evidence chunks
    verifier_verdict: str                  # 'supported' | 'partially_supported' | 'conflicting_evidence' | 'insufficient_evidence'
    verifier_explanation: str              # Detailed rationale for the verdict
    answer: str                            # Final grounded answer
    citations: List[str]                   # List of chunk_ids cited
    mode: str                              # 'baseline' or 'jev'
    latency_seconds: float


# =============================================================
# Agent 1: Planner & Query Reformulator
# =============================================================
PLANNER_PROMPT = """You are the Lead Research Planner for Kestrel Labs.
Analyze the user's current query in the context of any previous conversation history.

Tasks:
1. Coreference Resolution: If the user asks a follow-up (e.g. "how many of them can I create?", "what plan includes it?"), rewrite it into a fully self-contained question using prior context.
2. Query Decomposition: If the question requires multi-hop reasoning (e.g., finding an incident, then the fixing release, then which plan gets it), split it into 1 to 3 focused search queries.

Output format (JSON ONLY):
{
  "resolved_query": "<standalone question>",
  "sub_queries": ["<search query 1>", "<search query 2>"]
}"""

def planner_node(state: AgentState) -> Dict[str, Any]:
    history = state.get("messages", [])
    query = state["query"]

    # Build context from past turns (last 4 messages)
    context_str = ""
    if history:
        recent = history[-4:]
        context_str = "Conversation History:\n" + "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in recent
        ) + "\n\n"

    prompt = f"{context_str}Current User Question: {query}\n\nRespond with strict JSON."
    
    try:
        resp = safe_llm_invoke([
            ("system", PLANNER_PROMPT),
            ("user", prompt)
        ])
        content = resp.content.strip()
        # Clean markdown fences if any
        content = re.sub(r"^```json\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        data = json.loads(content)
        resolved_query = data.get("resolved_query", query)
        sub_queries = data.get("sub_queries", [resolved_query])
    except Exception:
        resolved_query = query
        sub_queries = [query]

    if not sub_queries:
        sub_queries = [resolved_query]

    return {
        "resolved_query": resolved_query,
        "sub_queries": sub_queries
    }


# =============================================================
# Agent 2: Evidence Scout (Retriever)
# =============================================================
def retriever_node(state: AgentState) -> Dict[str, Any]:
    sub_queries = state.get("sub_queries", [state["query"]])
    resolved_query = state.get("resolved_query", state["query"])

    all_chunks = []
    seen_ids = set()

    # Search for the resolved query first
    primary_hits = retrieve_evidence(resolved_query, top_k=5)
    for hit in primary_hits:
        if hit["chunk_id"] not in seen_ids:
            seen_ids.add(hit["chunk_id"])
            all_chunks.append(hit)

    # Search for decomposed sub-queries
    for sq in sub_queries:
        if sq == resolved_query:
            continue
        sub_hits = retrieve_evidence(sq, top_k=3)
        for hit in sub_hits:
            if hit["chunk_id"] not in seen_ids:
                seen_ids.add(hit["chunk_id"])
                all_chunks.append(hit)

    # Re-rank: prioritize highest similarity, and break ties using document recency (published date)
    all_chunks.sort(key=lambda x: (x["score"], x["published"]), reverse=True)

    # Cap context at top 4 chunks to keep token usage compact and within limits
    return {"retrieved_chunks": all_chunks[:4]}


# =============================================================
# Agent 3: Critic & Claim Verifier (Dual Mode: Baseline vs JEV)
# =============================================================
VERIFIER_PROMPT = """You are the Lead Fact-Checking Critic for Kestrel Labs.
Evaluate whether the retrieved documentation chunks contain sufficient, trustworthy evidence to answer the user's question.

Valid Verdicts:
- 'supported': The retrieved chunks contain explicit, verifiable facts that fully settle the question.
- 'partially_supported': Some aspects are answered, but critical details are missing.
- 'conflicting_evidence': Two or more documents disagree (e.g. an older spec vs a newer release note or incident fix).
- 'insufficient_evidence': The retrieved chunks DO NOT answer the question, or the topic is not covered in Kestrel documentation.

Output format (JSON ONLY):
{
  "verdict": "supported" | "partially_supported" | "conflicting_evidence" | "insufficient_evidence",
  "explanation": "<concise explanation of why this verdict was reached, noting any date discrepancies or missing points>"
}"""

def _run_baseline_verifier(question: str, chunks: List[Dict[str, Any]]) -> Dict[str, str]:
    """Evaluates evidence using standard Groq LLM reasoning."""
    if not chunks:
        return {
            "verdict": "insufficient_evidence",
            "explanation": "No relevant documents were retrieved from the corpus."
        }

    context_blocks = []
    for c in chunks:
        context_blocks.append(f"[{c['chunk_id']}] (Date: {c['published']}, Title: {c['title']})\n{c['text']}")
    context_str = "\n\n---\n\n".join(context_blocks)

    user_msg = f"Question: {question}\n\nRetrieved Chunks:\n{context_str}\n\nEvaluate and return JSON."
    
    try:
        resp = safe_llm_invoke([
            ("system", VERIFIER_PROMPT),
            ("user", user_msg)
        ])
        content = resp.content.strip()
        content = re.sub(r"^```json\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        data = json.loads(content)
        verdict = data.get("verdict", "supported")
        explanation = data.get("explanation", "")
    except Exception as e:
        verdict = "supported"
        explanation = f"Fallback verification: {str(e)}"

    return {"verdict": verdict, "explanation": explanation}


def _run_jev_verifier(question: str, chunks: List[Dict[str, Any]]) -> Dict[str, str]:
    """Evaluates evidence using TypeSafe AI Jev System 1 (Sub-150ms calibrated decision)."""
    import requests

    if not TYPESAFE_API_KEY:
        # Graceful fallback to baseline if Jev key missing
        return _run_baseline_verifier(question, chunks)

    if not chunks:
        return {
            "verdict": "insufficient_evidence",
            "explanation": "Zero chunks retrieved."
        }

    context_summary = " ".join([f"[{c['chunk_id']} {c['published']}] {c['text'][:150]}" for c in chunks[:4]])
    state_str = f"Question: {question} | Evidence: {context_summary}"

    url = "https://api.typesafe.ai/v1/systemone"
    headers = {
        "Authorization": f"Bearer {TYPESAFE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "state": state_str,
        "model": "jev-latest",
        "questions": {
            "verdict": {
                "type": "choice",
                "options": ["supported", "partially_supported", "conflicting_evidence", "insufficient_evidence"],
                "description": "Does the evidence support, partially support, contradict, or lack information to answer the question?"
            },
            "grounding_confidence": {
                "type": "noul",
                "description": "Is the question directly answerable from this text without guessing?"
            }
        }
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=5)
        if r.status_code == 200:
            data = r.json()
            verdict_choice = data["choices"]["verdict"]["choice"]
            conf = data["nouls"]["grounding_confidence"]["value"]
            return {
                "verdict": verdict_choice,
                "explanation": f"Jev System 1 verified with calibrated grounding confidence: {conf:.2%}"
            }
    except Exception:
        pass

    # Fallback to baseline if Jev request encounters issue
    return _run_baseline_verifier(question, chunks)


def verifier_node(state: AgentState) -> Dict[str, Any]:
    resolved_query = state.get("resolved_query", state["query"])
    chunks = state.get("retrieved_chunks", [])
    mode = state.get("mode", "baseline")

    if mode == "jev" and TYPESAFE_API_KEY:
        res = _run_jev_verifier(resolved_query, chunks)
    else:
        res = _run_baseline_verifier(resolved_query, chunks)

    return {
        "verifier_verdict": res["verdict"],
        "verifier_explanation": res["explanation"]
    }


# =============================================================
# Agent 4: Synthesizer & Citation Specialist
# =============================================================
SYNTHESIZER_PROMPT = """You are Kestrel Labs' Senior Research Assistant.
Draft an accurate, authoritative answer strictly grounded in the provided documentation chunks.

MANDATORY RULES:
1. Grounding & Citations: Every material claim MUST cite the chunk ID using format `[chunk_id]` (e.g. `[spec-beacons:0]`).
2. If Verifier Verdict is 'insufficient_evidence':
   - Plainly state that Kestrel's internal documentation does not contain information to answer the question.
   - Do NOT invent or speculate.
3. If Verifier Verdict is 'conflicting_evidence':
   - Present both claims clearly.
   - Cite their respective document titles and published dates (e.g. `[rn-4-1:0]` published 2026-02-24 vs `[spec-beacons:1]` published 2026-02-03).
   - State clearly which document is newer and therefore represents the current behavior.
4. Tone: Clear, technical, professional. Cite document titles alongside chunk IDs."""

def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    resolved_query = state.get("resolved_query", state["query"])
    chunks = state.get("retrieved_chunks", [])
    verdict = state.get("verifier_verdict", "supported")
    explanation = state.get("verifier_explanation", "")

    context_blocks = []
    for c in chunks:
        context_blocks.append(
            f"--- CHUNK ID: {c['chunk_id']} | Title: {c['title']} | Published: {c['published']} | Version: {c['version']} ---\n{c['text']}"
        )
    context_str = "\n\n".join(context_blocks)

    user_msg = f"""User Question: {resolved_query}
Verifier Verdict: {verdict}
Verifier Note: {explanation}

Available Evidence Chunks:
{context_str}

Please generate the grounded response following all citation and conflict rules."""

    resp = safe_llm_invoke([
        ("system", SYNTHESIZER_PROMPT),
        ("user", user_msg)
    ])
    answer = resp.content.strip()

    # Extract all cited chunk_ids from answer (e.g. [spec-beacons:0])
    cited_chunks = list(set(re.findall(r"\[([a-zA-Z0-9\-_]+:\d+)\]", answer)))

    return {
        "answer": answer,
        "citations": cited_chunks
    }
