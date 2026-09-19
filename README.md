# 🦅 Kestrel Labs Multi-Agent Research Assistant

An intelligent, grounded multi-agent research assistant designed for Kestrel Labs' internal wiki and event-pipeline documentation. Built with **LangGraph**, **Groq (`qwen/qwen3.8-27b`)**, **local sentence-transformers (`all-MiniLM-L6-v2`)**, and **ChromaDB**.

---

## 🌟 Key Features

1. **4-Agent Collaborative Swarm:**
   - 🧭 **Planner Agent:** Coreference resolution for multi-turn chats & multi-hop query decomposition.
   - 🔍 **Evidence Scout (Retriever):** Dense vector similarity + recency metadata arbitration.
   - ⚖️ **Critic / Verifier:** Formally verifies claims (`supported`, `partially_supported`, `conflicting_evidence`, `insufficient_evidence`).
   - ✍️ **Synthesizer:** Drafts authoritative answers with mandatory inline `[chunk_id]` citations and handles document contradictions.
2. **Strict Grounding & Anti-Hallucination:**
   - Never hallucinates on out-of-scope queries (e.g. private on-premise AKS clusters, unlisted SDKs).
   - Recency-aware arbitration: Older specifications are reconciled against newer release notes (`published` dates).
3. **Dual Verification Architecture (Documented in `results/improvement.md`):**
   - **Baseline Mode:** Generative LLM verification via Groq.
   - **Fast Mode (Optional):** Sub-150ms calibrated verification via TypeSafe AI JEV System 1.
   - Seamless zero-config fallback to Groq if no JEV key is provided.
4. **Interactive Streamlit Web UI & Unified CLI:**
   - Multi-turn conversation support with visible live status for every agent.
   - Expandable citations panel and visual verifier verdict badges.

---

## 🚀 Quick Start (Single Command)

### 1. Clone & Setup Environment
```bash
git clone <your-repo-url>
cd kestrel-assistant

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Fill in your API keys in `.env`:
```env
GROQ_API_KEY=gsk_...
LANGSMITH_API_KEY=lsv2_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=kestrel-research-assistant
```

### 3. Run the System

- **Launch Interactive Web UI (Streamlit):**
  ```bash
  python main.py --ui
  # Or: streamlit run app.py
  ```

- **Run in Terminal (CLI Mode):**
  ```bash
  python main.py
  ```

- **Run Evaluation Suite (Generates all `results/` artifacts):**
  ```bash
  python main.py --eval
  ```

---

## 🏗️ Architecture Overview

```
User Query / Follow-up
        │
        ▼
[Agent 1: Planner]  ────────►  Resolves pronouns & decomposes multi-hop queries
        │
        ▼
[Agent 2: Retriever] ───────►  Searches local ChromaDB (all-MiniLM-L6-v2)
        │
        ▼
[Agent 3: Verifier]  ───────►  Assigns verdict (supported / conflicting / insufficient)
        │
        ▼
[Agent 4: Synthesizer] ─────►  Generates grounded text with [chunk_id] citations
        │
        ▼
Final Grounded Answer
```

Detailed design decisions and trade-offs are documented in [DESIGN.md](DESIGN.md).

---

## 📊 Evaluation Suite & Results

The system is evaluated against a 16-question benchmark spanning all required challenge categories:
- `single_hop`: Direct factual lookup against specs and limits.
- `multi_hop`: Multi-document dependency traversal (Incident $\rightarrow$ Release Notes $\rightarrow$ Pricing).
- `conflicting`: Temporal contradictions resolved via `published` date recency.
- `unsupported`: Verifiable refusal on absent topics (AKS deployment, non-profit discounts).
- `follow_up`: Multi-turn coreference resolution across conversation history.

Generated artifacts in `results/`:
- `results/eval_questions.jsonl`: Benchmark test questions.
- `results/eval_results.jsonl`: Detailed per-question metrics, verdicts, and citations.
- `results/metrics_summary.json`: Summary scores, token counts, and latency benchmarks.
- `results/improvement.md`: Before-and-after improvement analysis.

---

## 🔭 LangSmith Observability & Sharing

Every execution trace, state transition, and sub-query is logged to LangSmith.

- **Project Name:** `kestrel-research-assistant`
- **Reviewer Access:** Project access has been granted to **`radialpulse@nxtwave.co.in`**.
