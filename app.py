import os
import streamlit as st
from graph import ask_kestrel, clear_query_cache

st.set_page_config(
    page_title="Kestrel Labs · Research Assistant",
    page_icon="K",
    layout="wide"
)

# Refined, theme-adaptive custom styling
st.markdown("""
<style>
    .meta-status-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 10px;
        margin-bottom: 8px;
        font-size: 12.5px;
        color: #94a3b8;
    }
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11.5px;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .status-supported { background: rgba(16, 185, 129, 0.12); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.25); }
    .status-partially { background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.25); }
    .status-conflicting { background: rgba(245, 158, 11, 0.12); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.25); }
    .status-insufficient { background: rgba(244, 63, 94, 0.12); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.25); }
</style>
""", unsafe_allow_html=True)

st.title("Kestrel Labs Research Assistant")
st.caption("Multi-Agent Documentation & Technical Intelligence · LangGraph + Groq")

# Sidebar Configuration
with st.sidebar:
    st.header("Agent Configuration")
    mode = st.radio(
        "Verification Engine",
        options=["baseline", "jev"],
        format_func=lambda x: "Baseline (Groq LLM Critic)" if x == "baseline" else "JEV System 1 (Calibrated Decision Engine)",
        help="Select between generative LLM critique or TypeSafe AI Jev System-1 fast verification."
    )
    
    st.markdown("---")
    st.subheader("Corpus Overview")
    st.markdown("""
    - **Total Documents:** 25
    - **Total Chunks:** 154
    - **Local Embeddings:** `all-MiniLM-L6-v2`
    - **LLM Generator:** `qwen/qwen3.8-27b`
    - **Caching:** In-memory query response cache active
    """)

    st.markdown("---")
    if st.button("Clear Conversation & Cache"):
        st.session_state.messages = []
        clear_query_cache()
        st.rerun()

# Initialize session state for multi-turn conversations
if "messages" not in st.session_state:
    st.session_state.messages = []

def render_verdict_bar(meta: dict):
    verdict = meta.get("verdict", "supported")
    verdict_map = {
        "supported": ("Supported by Evidence", "status-supported", "#10b981"),
        "partially_supported": ("Partially Supported", "status-partially", "#38bdf8"),
        "conflicting_evidence": ("Conflicting Sources", "status-conflicting", "#f59e0b"),
        "insufficient_evidence": ("No Direct Evidence", "status-insufficient", "#f43f5e")
    }
    label, css_class, dot_color = verdict_map.get(verdict, ("Evaluated", "status-supported", "#10b981"))
    
    latency = meta.get("latency", 0.0)
    cached_badge = " · Cached" if meta.get("cached") else ""
    expl = meta.get("explanation", "")
    expl_str = f" · {expl}" if expl else ""
    
    st.markdown(f"""
    <div class="meta-status-row">
        <span class="status-pill {css_class}">
            <span class="status-dot" style="background-color: {dot_color};"></span>
            {label}
        </span>
        <span>{latency:.3f}s{cached_badge}{expl_str}</span>
    </div>
    """, unsafe_allow_html=True)

# Display conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "meta" in msg:
            meta = msg["meta"]
            render_verdict_bar(meta)

            if meta.get("citations"):
                with st.expander(f"Verified Citations ({len(meta['citations'])})"):
                    for c_id in meta["citations"]:
                        st.markdown(f"- `{c_id}`")

# Chat input
user_input = st.chat_input("Ask about Kestrel products, specs, release notes, pricing, runbooks...")

if user_input:
    # Append and show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Multi-agent execution with minimal status box
    with st.chat_message("assistant"):
        status_box = st.status("Orchestrating agents...", expanded=True)
        
        with status_box:
            st.write("Planner: Resolving conversational intent & query decomposition...")
            st.write("Retriever: Querying local Chroma vector store...")
            st.write("Verifier: Evaluating evidence claims & factual calibration...")
            st.write("Synthesizer: Drafting grounded response with inline citations...")

        # Invoke the LangGraph workflow
        history_for_agent = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]
        
        res = ask_kestrel(query=user_input, messages=history_for_agent, mode=mode)
        
        cached_info = " (Cache Hit)" if res.get("cached") else ""
        status_box.update(label=f"Completed in {res['latency_seconds']}s{cached_info}", state="complete", expanded=False)

        # Render Answer
        st.markdown(res["answer"])

        # Render Natural Verdict Bar
        meta_dict = {
            "verdict": res.get("verifier_verdict", "supported"),
            "explanation": res.get("verifier_explanation", ""),
            "citations": res.get("citations", []),
            "latency": res["latency_seconds"],
            "cached": res.get("cached", False)
        }
        render_verdict_bar(meta_dict)

        # Render Citations
        if res.get("citations"):
            with st.expander(f"Verified Citations ({len(res['citations'])})"):
                for c_id in res["citations"]:
                    st.markdown(f"- `{c_id}`")

        # Render Evidence Drawer using theme-native containers (100% dark & light mode compatible)
        chunks = res.get("retrieved_chunks", [])
        if chunks:
            with st.expander(f"Retrieved Evidence ({len(chunks)} Chunks)"):
                for c in chunks:
                    with st.container(border=True):
                        st.markdown(f"**[{c['chunk_id']}] {c['title']}** &nbsp;·&nbsp; `Published: {c['published']}` &nbsp;·&nbsp; `Category: {c['category']}`")
                        if c.get("score") is not None:
                            st.caption(f"Relevance Score: {c['score']:.4f}")
                        st.markdown(c["text"])

        # Save assistant reply to session state
        st.session_state.messages.append({
            "role": "assistant",
            "content": res["answer"],
            "meta": meta_dict
        })
