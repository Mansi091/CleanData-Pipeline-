import argparse
from src.rule_vs_llm.pipeline import run_full_pipeline

def main():
    parser = argparse.ArgumentParser(description="Rule-Based vs LLM-Based Data Cleaning")
    parser.add_argument("--live", action="store_true", help="Run with live LLM API (requires GROQ_API_KEY)")
    parser.add_argument("--data-dir", type=str, default="data", help="Path to data directory")
    
    args = parser.parse_args()
    
    run_full_pipeline(data_dir=args.data_dir, live_llm=args.live)

if __name__ == "__main__":
    main()
