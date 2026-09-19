import os
import streamlit as st
from graph import ask_kestrel

st.set_page_config(
    page_title="Kestrel Labs · Multi-Agent Research Assistant",
    page_icon="🦅",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .reportview-container { background: #f8fafc; }
    .badge-supported { background-color: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 13px; }
    .badge-conflicting { background-color: #fef3c7; color: #92400e; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 13px; }
    .badge-insufficient { background-color: #fee2e2; color: #991b1b; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 13px; }
    .badge-partially { background-color: #e0f2fe; color: #075985; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 13px; }
    .citation-card { background: #f1f5f9; border-left: 3px solid #0284c7; padding: 8px 12px; margin: 6px 0; border-radius: 4px; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

st.title("🦅 Kestrel Labs Research Assistant")
st.caption("Multi-Agent Wiki & Technical Intelligence System · Powered by LangGraph & Groq")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Agent Configuration")
    mode = st.radio(
        "Verification Architecture",
        options=["baseline", "jev"],
        format_func=lambda x: "Baseline (Groq LLM Critic)" if x == "baseline" else "JEV System 1 (Sub-150ms Fast Critic)",
        help="Switch between standard generative LLM verification and TypeSafe AI Jev System-1 verification."
    )
    
    st.markdown("---")
    st.subheader("📚 Corpus Overview")
    st.markdown("""
    - **Total Documents:** 25
    - **Total Chunks:** 154
    - **Local Embeddings:** `all-MiniLM-L6-v2`
    - **LLM Generator:** `qwen/qwen3.8-27b`
    """)

    st.markdown("---")
    if st.button("Clear Conversation History"):
        st.session_state.messages = []
        st.rerun()

# Initialize session state for multi-turn conversations
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "meta" in msg:
            meta = msg["meta"]
            verdict = meta.get("verdict", "supported")
            badge_class = f"badge-{verdict.split('_')[0]}"
            st.markdown(f"<span class='{badge_class}'>Verdict: {verdict.upper()}</span> (Latency: {meta.get('latency', 0)}s)", unsafe_allow_html=True)

            if meta.get("citations"):
                with st.expander(f"📌 {len(meta['citations'])} Verified Citations"):
                    for c_id in meta["citations"]:
                        st.markdown(f"- `[{c_id}]`")

# Chat input
user_input = st.chat_input("Ask about Kestrel products, release notes, pricing, runbooks...")

if user_input:
    # Append and show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Multi-agent execution with status spinner
    with st.chat_message("assistant"):
        status_box = st.status("Agent Swarm Orchestrating...", expanded=True)
        
        with status_box:
            st.write("🧭 **Planner:** Resolving multi-turn context & decomposing queries...")
            st.write("🔍 **Retriever:** Scanning local Chroma vector store & metadata...")
            st.write("⚖️ **Verifier:** Cross-examining claims against retrieved chunks...")
            st.write("✍️ **Synthesizer:** Generating grounded answer with inline citations...")

        # Invoke the LangGraph workflow
        history_for_agent = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]
        
        res = ask_kestrel(query=user_input, messages=history_for_agent, mode=mode)
        
        status_box.update(label=f"Completed in {res['latency_seconds']}s", state="complete", expanded=False)

        # Render Answer
        st.markdown(res["answer"])

        # Render Verdict Badge
        verdict = res.get("verifier_verdict", "supported")
        badge_class = f"badge-{verdict.split('_')[0]}"
        st.markdown(f"<span class='{badge_class}'>Verdict: {verdict.upper()}</span> · {res.get('verifier_explanation', '')}", unsafe_allow_html=True)

        # Render Citations & Evidence Drawer
        chunks = res.get("retrieved_chunks", [])
        if chunks:
            with st.expander(f"📚 Inspect Retrieved Evidence ({len(chunks)} Chunks)"):
                for c in chunks:
                    st.markdown(f"""
                    <div class="citation-card">
                        <strong>[{c['chunk_id']}] {c['title']}</strong> (Category: {c['category']}, Published: {c['published']})<br>
                        <em>Score: {c.get('score', 'N/A')}</em><br>
                        <p style="margin-top:4px;">{c['text']}</p>
                    </div>
                    """, unsafe_allow_html=True)

        # Save assistant reply to session state
        st.session_state.messages.append({
            "role": "assistant",
            "content": res["answer"],
            "meta": {
                "verdict": verdict,
                "citations": res.get("citations", []),
                "latency": res["latency_seconds"]
            }
        })
