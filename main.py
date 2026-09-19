import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

def run_interactive_cli():
    from graph import ask_kestrel

    print("\n==================================================================")
    print("🦅 Kestrel Labs Multi-Agent Research Assistant (CLI Mode)")
    print("==================================================================")
    print("Type your questions below. Type 'exit' or 'quit' to stop.\n")

    history = []
    while True:
        try:
            query = input("\nUser Query > ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break

            print("\n[*] Orchestrating agents (Planner -> Retriever -> Verifier -> Synthesizer)...")
            res = ask_kestrel(query=query, messages=history)

            print(f"\n[Verdict: {res['verifier_verdict'].upper()}] (Latency: {res['latency_seconds']}s)")
            print(f"Citations: {res['citations']}\n")
            print("Answer:")
            print(res["answer"])

            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": res["answer"]})

        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

def main():
    parser = argparse.ArgumentParser(description="Kestrel Labs Multi-Agent Research Assistant")
    parser.add_argument("--eval", action="store_true", help="Run evaluation suite and generate results/ files")
    parser.add_argument("--mode", choices=["baseline", "jev"], default="baseline", help="Verification mode for evaluation")
    parser.add_argument("--ui", action="store_true", help="Launch Streamlit Web UI")

    args = parser.parse_args()

    if args.ui:
        import subprocess
        print("[*] Launching Streamlit interface...")
        subprocess.run(["streamlit", "run", os.path.join(os.path.dirname(__file__), "app.py")])
    elif args.eval:
        from eval_suite import run_full_evaluation
        print(f"[*] Running Evaluation Suite in mode: {args.mode.upper()}")
        summary = run_full_evaluation(mode=args.mode)
        print("\n================ EVALUATION SUMMARY ================")
        import json
        print(json.dumps(summary, indent=2))
    else:
        run_interactive_cli()

if __name__ == "__main__":
    main()
