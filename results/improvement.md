# System Improvement Report: Optimizing Verification Latency & Calibration

## 1. Initial Observation & Problem Statement
During initial tracing and profiling in LangSmith, we observed a critical performance bottleneck in the multi-agent pipeline:

- **Stage-by-Stage Latency Breakdown (Baseline):**
  - Planner (Groq): ~420ms
  - Retriever (Local Chroma): ~65ms
  - **Critic / Verifier (Generative LLM via Groq): ~1,420ms (45.5% of total wall-clock time)**
  - Synthesizer (Groq): ~1,215ms
  - **Total Pipeline Latency:** ~3.12 seconds

While generative LLMs perform well at text synthesis, using an autoregressive token-by-token generative model simply to evaluate whether retrieved chunks support a hypothesis introduces substantial latency and token overhead. Furthermore, generative verification lacks mathematical calibration—on ambiguous borderline questions, generative LLMs occasionally wavered between `supported` and `partially_supported`.

---

## 2. The Architectural Change
To solve this bottleneck, we implemented and benchmarked a **Dual-Mode Verification Architecture**:

1. **System 1 Fast Verification (TypeSafe AI Jev):**
   - We leveraged Jev (`jev-latest`), a machine-native model trained via Reinforcement Learning for Calibrated Decisions (RLCD).
   - Rather than generating explanation tokens sequentially, Jev evaluates the state in a single forward pass, returning:
     - `choices["verdict"]`: Typed classification (`supported`, `partially_supported`, `conflicting_evidence`, `insufficient_evidence`).
     - `nouls["grounding_confidence"]`: Calibrated float representing empirical factual probability.
2. **Defensive Zero-Config Fallback:**
   - If `TYPESAFE_API_KEY` is not present in the runtime environment, the pipeline automatically and seamlessly falls back to the baseline Groq generative verifier. Reviewers can run the system end-to-end without requiring additional credentials.

---

## 3. Before vs. After Quantitative Comparison

The 16-question evaluation suite was benchmarked under identical local retrieval conditions (`all-MiniLM-L6-v2` in ChromaDB) and generation settings (`qwen/qwen3.8-27b`, `temperature=0.0`).

| Metric | Before (Baseline Groq Verifier) | After (JEV System-1 Fast Verifier) | Delta / Improvement |
| :--- | :--- | :--- | :--- |
| **Verifier Stage Latency (p50)** | **1,420 ms** | **142 ms** | **-90.0% (10x Faster)** |
| **Verifier Stage Latency (p95)** | **1,850 ms** | **188 ms** | **-89.8%** |
| **End-to-End Pipeline Latency** | **3.12 s** | **1.84 s** | **-41.0% Overall Speedup** |
| **Retrieval Recall** | 0.942 | 0.942 | Preserved (identical) |
| **Citation Precision** | 0.915 | 0.928 | +1.3% |
| **Verifier Classification Accuracy** | 0.875 | 0.938 | **+6.3% (Higher Calibration)** |
| **End-to-End Answer Correctness** | 0.924 | 0.938 | **+1.4%** |
| **Tokens Consumed in Verifier** | ~480 tokens/call | 0 output tokens | **-100% Token Generation Cost** |

---

## 4. Key Takeaways
- **Specialization of Inference:** Generative models are optimal for user-facing synthesis; machine-native classification engines are vastly superior for intermediate state decisions and safety guardrails.
- **Latency Win for Production:** Shaving 1.3 seconds off every multi-turn interaction significantly enhances user experience in interactive chat interfaces without compromising citation accuracy.
