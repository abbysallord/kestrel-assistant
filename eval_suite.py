import os
import json
import time
from typing import List, Dict, Any

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

EVAL_QUESTIONS: List[Dict[str, Any]] = [
    # --- 1. Single-Hop Questions ---
    {
        "question_id": "q-single-01",
        "question": "How many Beacons can a customer create on the Starter plan?",
        "type": "single_hop",
        "conversation_id": None,
        "turn": None,
        "expected_answer": "A project on the Starter plan may create up to 5 Beacons.",
        "expected_chunk_ids": ["spec-beacons:4", "pricing-plans:1"]
    },
    {
        "question_id": "q-single-02",
        "question": "What destination channels can a Beacon notify when an alert condition is met?",
        "type": "single_hop",
        "conversation_id": None,
        "turn": None,
        "expected_answer": "A Beacon can notify up to four destinations at once: Slack, PagerDuty, generic webhooks, and email.",
        "expected_chunk_ids": ["spec-beacons:3"]
    },
    {
        "question_id": "q-single-03",
        "question": "What is the maximum event payload size accepted by Kestrel's Event Ingestion API?",
        "type": "single_hop",
        "conversation_id": None,
        "turn": None,
        "expected_answer": "The maximum payload size for a single event or batch is 1MB.",
        "expected_chunk_ids": ["spec-ingest-api:0", "spec-ingest-api:1"]
    },
    {
        "question_id": "q-single-04",
        "question": "How long is raw event data retained for customers on the Growth plan?",
        "type": "single_hop",
        "conversation_id": None,
        "turn": None,
        "expected_answer": "Raw event data is retained for 90 days on the Growth plan.",
        "expected_chunk_ids": ["policy-data-retention:0", "pricing-plans:1"]
    },

    # --- 2. Multi-Hop Questions ---
    {
        "question_id": "q-multi-05",
        "question": "Which release addressed the clock skew issue causing Beacon alert delays in incident INC-2026-02, and what technical change was made?",
        "type": "multi_hop",
        "conversation_id": None,
        "turn": None,
        "expected_answer": "Release 4.1.1 addressed the clock skew issue from incident INC-2026-02 by moving the scheduler to a monotonic clock and adding catch-up evaluation for skipped windows.",
        "expected_chunk_ids": ["pm-inc-2026-02:0", "pm-inc-2026-02:4", "rn-4-1:1", "spec-beacons:1"]
    },
    {
        "question_id": "q-multi-06",
        "question": "What caused duplicate rows in Warehouse Sync during INC-2025-11, and which plan level includes Snowflake sync?",
        "type": "multi_hop",
        "conversation_id": None,
        "turn": None,
        "expected_answer": "INC-2025-11 was caused by non-atomic retry logic in the Snowflake connector during warehouse re-sync. Snowflake Warehouse Sync is included on Growth and Scale plans.",
        "expected_chunk_ids": ["pm-inc-2025-11:0", "pm-inc-2025-11:2", "pricing-plans:2", "spec-warehouse-sync:0"]
    },
    {
        "question_id": "q-multi-07",
        "question": "What was the root cause of INC-2025-07, and how did release 3.6.2 mitigate future occurrences?",
        "type": "multi_hop",
        "conversation_id": None,
        "turn": None,
        "expected_answer": "INC-2025-07 was caused by schema migration lock contention on ingest nodes during the 3.6 rollout. Release 3.6.2 mitigated it by adding rolling lockless partition updates.",
        "expected_chunk_ids": ["pm-inc-2025-07:1", "pm-inc-2025-07:4", "rn-3-6:3"]
    },

    # --- 3. Conflicting Evidence Questions ---
    {
        "question_id": "q-conflict-08",
        "question": "Does Kestrel support PagerDuty as a Beacon notification destination, and when was it introduced?",
        "type": "conflicting",
        "conversation_id": None,
        "turn": None,
        "expected_answer": "Yes, PagerDuty is supported as of release 4.1 (published 2026-02-03/2026-02-24). Earlier documentation and versions prior to 4.1 only supported Slack, webhooks, and email.",
        "expected_chunk_ids": ["spec-beacons:0", "spec-beacons:3", "rn-4-1:0"]
    },
    {
        "question_id": "q-conflict-09",
        "question": "What is the typical ingest visibility lag for incoming events?",
        "type": "conflicting",
        "conversation_id": None,
        "turn": None,
        "expected_answer": "The older Ingest Pipeline Architecture (published 2025-07-08) stated visibility lag was around 60 seconds, but the newer Beacons Specification (published 2026-02-03) documents that ingest visibility lag is under 30 seconds.",
        "expected_chunk_ids": ["eng-ingest-architecture:1", "spec-beacons:1"]
    },
    {
        "question_id": "q-conflict-10",
        "question": "What is the maximum cooldown period that can be configured for a Beacon alert?",
        "type": "conflicting",
        "conversation_id": None,
        "turn": None,
        "expected_answer": "The default cooldown is 30 minutes, and it can be configured between 5 minutes and 24 hours.",
        "expected_chunk_ids": ["spec-beacons:3"]
    },

    # --- 4. Unsupported Questions ---
    {
        "question_id": "q-unsupported-11",
        "question": "How can I deploy Kestrel on-premises in my private Azure Kubernetes Service (AKS) cluster?",
        "type": "unsupported",
        "conversation_id": None,
        "turn": None,
        "expected_answer": None,
        "expected_chunk_ids": []
    },
    {
        "question_id": "q-unsupported-12",
        "question": "What is the discount policy and pricing structure for non-profit and educational institutions?",
        "type": "unsupported",
        "conversation_id": None,
        "turn": None,
        "expected_answer": None,
        "expected_chunk_ids": []
    },
    {
        "question_id": "q-unsupported-13",
        "question": "Does Kestrel provide an official server-side SDK for Ruby on Rails?",
        "type": "unsupported",
        "conversation_id": None,
        "turn": None,
        "expected_answer": None,
        "expected_chunk_ids": []
    },

    # --- 5. Multi-Turn Follow-up Questions ---
    {
        "question_id": "q-followup-14",
        "question": "How far back does its history reach?",
        "type": "follow_up",
        "conversation_id": "conv-trails",
        "turn": 2,
        "prior_messages": [
            {"role": "user", "content": "Tell me about Trails in Kestrel."},
            {"role": "assistant", "content": "Trails is Kestrel's user timeline specification that records sequential events per user [spec-trails:0]."}
        ],
        "expected_answer": "Trails history reaches back according to the project's data retention limit: 30 days on Starter, 90 days on Growth, and 365 days on Scale.",
        "expected_chunk_ids": ["spec-trails:1", "policy-data-retention:0", "pricing-plans:1"]
    },
    {
        "question_id": "q-followup-15",
        "question": "What plans include this feature?",
        "type": "follow_up",
        "conversation_id": "conv-warehouse",
        "turn": 2,
        "prior_messages": [
            {"role": "user", "content": "Can I sync my analytics data directly to Snowflake using Warehouse Sync?"},
            {"role": "assistant", "content": "Yes, Kestrel supports Warehouse Sync to Snowflake, BigQuery, and Redshift [spec-warehouse-sync:0]."}
        ],
        "expected_answer": "Warehouse Sync is available on Growth and Scale plans, but is not included in the Starter plan.",
        "expected_chunk_ids": ["spec-warehouse-sync:0", "pricing-plans:2"]
    },
    {
        "question_id": "q-followup-16",
        "question": "What is the sync frequency?",
        "type": "follow_up",
        "conversation_id": "conv-warehouse",
        "turn": 3,
        "prior_messages": [
            {"role": "user", "content": "Can I sync my analytics data directly to Snowflake using Warehouse Sync?"},
            {"role": "assistant", "content": "Yes, Kestrel supports Warehouse Sync [spec-warehouse-sync:0]."},
            {"role": "user", "content": "What plans include this feature?"},
            {"role": "assistant", "content": "Warehouse Sync is included on Growth and Scale plans [pricing-plans:2]."}
        ],
        "expected_answer": "Warehouse Sync runs daily on Growth plans and hourly on Scale plans.",
        "expected_chunk_ids": ["spec-warehouse-sync:2", "pricing-plans:2"]
    }
]


def write_eval_questions_file():
    """Writes results/eval_questions.jsonl following exact schema requirements."""
    path = os.path.join(RESULTS_DIR, "eval_questions.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for q in EVAL_QUESTIONS:
            record = {
                "question_id": q["question_id"],
                "question": q["question"],
                "type": q["type"],
                "conversation_id": q["conversation_id"],
                "turn": q["turn"],
                "expected_answer": q["expected_answer"],
                "expected_chunk_ids": q["expected_chunk_ids"]
            }
            f.write(json.dumps(record) + "\n")
    print(f"[+] Wrote {len(EVAL_QUESTIONS)} questions to {path}")


def compute_eval_metrics(
    q_item: Dict[str, Any],
    result: Dict[str, Any]
) -> Dict[str, float]:
    """Computes retrieval recall, citation precision, faithfulness, and correctness scores."""
    expected_chunks = set(q_item["expected_chunk_ids"])
    retrieved_chunks = set([c["chunk_id"] for c in result.get("retrieved_chunks", [])])
    citations = set(result.get("citations", []))
    q_type = q_item["type"]
    verdict = result.get("verifier_verdict", "")
    answer = result.get("answer", "")

    # 1. Retrieval Recall
    if expected_chunks:
        retrieval_recall = len(expected_chunks.intersection(retrieved_chunks)) / len(expected_chunks)
    else:
        retrieval_recall = 1.0 if len(retrieved_chunks) == 0 or q_type == "unsupported" else 0.5

    # 2. Citation Precision
    if citations:
        if expected_chunks:
            citation_precision = len(citations.intersection(expected_chunks)) / len(citations)
        else:
            citation_precision = 0.0  # Cited chunks when none expected
    else:
        citation_precision = 1.0 if not expected_chunks else 0.0

    # 3. Verifier Correctness
    if q_type == "unsupported":
        verifier_score = 1.0 if verdict == "insufficient_evidence" else 0.0
    elif q_type == "conflicting":
        verifier_score = 1.0 if verdict in ["conflicting_evidence", "supported"] else 0.5
    else:
        verifier_score = 1.0 if verdict in ["supported", "partially_supported"] else 0.0

    # 4. Answer Faithfulness & Honesty
    if q_type == "unsupported":
        # Check if model correctly refused to answer / noted lack of evidence
        is_honest = any(w in answer.lower() for w in ["does not", "no information", "not found", "insufficient", "unsupported", "not mentioned"])
        faithfulness_score = 1.0 if is_honest else 0.0
    else:
        # Check if citations are present for factual claims
        has_citations = len(citations) > 0
        faithfulness_score = 1.0 if has_citations else 0.3

    # Composite correctness score
    correctness = round(0.35 * retrieval_recall + 0.25 * citation_precision + 0.20 * verifier_score + 0.20 * faithfulness_score, 3)

    return {
        "retrieval_recall": round(retrieval_recall, 3),
        "citation_precision": round(citation_precision, 3),
        "verifier_agreement": round(verifier_score, 3),
        "faithfulness": round(faithfulness_score, 3),
        "end_to_end_correctness": correctness
    }


def run_full_evaluation(mode: str = "baseline"):
    """Runs all 16 questions, logs results to results/eval_results.jsonl, and produces metrics_summary.json."""
    from graph import ask_kestrel

    write_eval_questions_file()

    results_path = os.path.join(RESULTS_DIR, "eval_results.jsonl")
    summary_path = os.path.join(RESULTS_DIR, "metrics_summary.json")

    results_records = []
    total_tokens_approx = 0
    t_start = time.perf_counter()

    print(f"\n[*] Starting evaluation suite in [{mode.upper()}] mode across {len(EVAL_QUESTIONS)} questions...")

    for idx, item in enumerate(EVAL_QUESTIONS, 1):
        q_id = item["question_id"]
        q_text = item["question"]
        q_type = item["type"]
        history = item.get("prior_messages", [])

        print(f"[{idx}/{len(EVAL_QUESTIONS)}] Running {q_id} ({q_type}): '{q_text[:45]}...'")

        res = ask_kestrel(query=q_text, messages=history, mode=mode)
        metrics = compute_eval_metrics(item, res)

        retrieved_ids = [c["chunk_id"] for c in res.get("retrieved_chunks", [])]
        record = {
            "question_id": q_id,
            "answer": res.get("answer", ""),
            "citations": res.get("citations", []),
            "retrieved_chunk_ids": retrieved_ids,
            "verifier_verdict": res.get("verifier_verdict", ""),
            "scores": metrics,
            "latency_seconds": res.get("latency_seconds", 0.0),
            "langsmith_run_url": os.getenv("LANGCHAIN_PROJECT_URL", "https://smith.langchain.com/o/kestrel/projects/p/kestrel-assistant")
        }
        results_records.append(record)

        # Approx token calculation for reporting
        total_tokens_approx += len(q_text.split()) + len(res.get("answer", "").split()) + sum(len(c.get("text", "").split()) for c in res.get("retrieved_chunks", []))

    # Write results/eval_results.jsonl
    with open(results_path, "w", encoding="utf-8") as f:
        for r in results_records:
            f.write(json.dumps(r) + "\n")
    print(f"[+] Successfully wrote {len(results_records)} records to {results_path}")

    # Compute summary metrics
    total_wall_clock = round(time.perf_counter() - t_start, 2)
    avg_correctness = sum(r["scores"]["end_to_end_correctness"] for r in results_records) / len(results_records)
    avg_retrieval_recall = sum(r["scores"]["retrieval_recall"] for r in results_records) / len(results_records)
    avg_citation_precision = sum(r["scores"]["citation_precision"] for r in results_records) / len(results_records)
    avg_faithfulness = sum(r["scores"]["faithfulness"] for r in results_records) / len(results_records)
    avg_latency = sum(r["latency_seconds"] for r in results_records) / len(results_records)

    by_type = {}
    for q_type in ["single_hop", "multi_hop", "conflicting", "unsupported", "follow_up"]:
        matching = [r for r, q in zip(results_records, EVAL_QUESTIONS) if q["type"] == q_type]
        if matching:
            by_type[q_type] = {
                "count": len(matching),
                "avg_correctness": round(sum(m["scores"]["end_to_end_correctness"] for m in matching) / len(matching), 3),
                "avg_latency": round(sum(m["latency_seconds"] for m in matching) / len(matching), 3)
            }

    metrics_summary = {
        "evaluation_mode": mode,
        "generation_model": "qwen/qwen3.8-27b (Groq, temperature=0.0)",
        "embedding_model": "all-MiniLM-L6-v2 (Local sentence-transformers via ChromaDB)",
        "total_questions": len(results_records),
        "total_wall_clock_seconds": total_wall_clock,
        "average_latency_seconds": round(avg_latency, 3),
        "aggregate_scores": {
            "end_to_end_correctness": round(avg_correctness, 3),
            "retrieval_recall": round(avg_retrieval_recall, 3),
            "citation_precision": round(avg_citation_precision, 3),
            "answer_faithfulness": round(avg_faithfulness, 3)
        },
        "breakdown_by_type": by_type,
        "approx_total_tokens": total_tokens_approx
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)
    print(f"[+] Successfully wrote summary metrics to {summary_path}")

    return metrics_summary


if __name__ == "__main__":
    write_eval_questions_file()
    print("[*] Questions file verified.")
