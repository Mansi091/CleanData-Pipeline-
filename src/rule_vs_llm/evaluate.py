import json
import pandas as pd

def run_evaluation(rule_output_path: str, llm_output_path: str, 
                   rule_timing_path: str, llm_timing_path: str, 
                   summary_output_path: str):
    rule_df = pd.read_csv(rule_output_path)
    llm_df = pd.read_csv(llm_output_path)

    with open(rule_timing_path) as f:
        rule_time = float(f.read().strip())
    with open(llm_timing_path) as f:
        llm_timing = json.load(f)

    n = len(rule_df)

    rule_correct = (rule_df["rule_based_prediction"].str.strip().str.lower()
                     == rule_df["ground_truth"].str.strip().str.lower())
    llm_correct = (llm_df["llm_prediction"].fillna("").str.strip().str.lower()
                   == llm_df["ground_truth"].str.strip().str.lower())

    rule_accuracy = rule_correct.mean() * 100
    llm_accuracy = llm_correct.mean() * 100

    dupe_mask = rule_df["is_injected_duplicate"] == True              
    rule_acc_dupes = rule_correct[dupe_mask].mean() * 100 if dupe_mask.sum() else None
    llm_acc_dupes = llm_correct[dupe_mask].mean() * 100 if dupe_mask.sum() else None
    rule_acc_plain = rule_correct[~dupe_mask].mean() * 100
    llm_acc_plain = llm_correct[~dupe_mask].mean() * 100

    summary = {
        "total_rows": n,
        "rule_based": {
            "accuracy_pct": round(rule_accuracy, 2),
            "accuracy_pct_plain_corruption": round(rule_acc_plain, 2),
            "accuracy_pct_near_duplicates": round(rule_acc_dupes, 2) if rule_acc_dupes is not None else None,
            "total_time_seconds": round(rule_time, 4),
            "ms_per_row": round(rule_time / n * 1000, 3),
            "total_cost_usd": 0.0,
            "requires_reference_list": True,
        },
        "llm_based": {
            "accuracy_pct": round(llm_accuracy, 2),
            "accuracy_pct_plain_corruption": round(llm_acc_plain, 2),
            "accuracy_pct_near_duplicates": round(llm_acc_dupes, 2) if llm_acc_dupes is not None else None,
            "estimated_total_time_seconds": round(llm_timing["estimated_total_latency_seconds"], 2),
            "estimated_ms_per_row": round(llm_timing["estimated_total_latency_seconds"] / n * 1000, 1),
            "estimated_total_cost_usd": round(llm_timing["estimated_total_cost_usd"], 4),
            "requires_reference_list": False,
            "note": "timing/cost are documented estimates, not measured — see llm.py",
        },
    }

    with open(summary_output_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("=" * 72)
    print("RULE-BASED vs LLM-BASED DATA CLEANING — EVALUATION")
    print("=" * 72)
    print(f"\n{'Metric':<38}{'Rule-Based':<18}{'LLM-Based (est.)':<18}")
    print("-" * 72)
    print(f"{'Overall accuracy':<38}{rule_accuracy:>6.2f}%{'':<11}{llm_accuracy:>6.2f}%")
    print(f"{'Accuracy on plain corruption':<38}{rule_acc_plain:>6.2f}%{'':<11}{llm_acc_plain:>6.2f}%")
    if rule_acc_dupes is not None:
        print(f"{'Accuracy on near-duplicate rows':<38}{rule_acc_dupes:>6.2f}%{'':<11}{llm_acc_dupes:>6.2f}%")
    print(f"{'Speed (total, ' + str(n) + ' rows)':<38}{rule_time:>6.3f}s{'':<10}"
          f"~{llm_timing['estimated_total_latency_seconds']:.1f}s")
    print(f"{'Cost (total, ' + str(n) + ' rows)':<38}{'$0.0000':<18}"
          f"~${llm_timing['estimated_total_cost_usd']:.4f}")
    print(f"{'Needs a reference list?':<38}{'Yes':<18}{'No':<18}")

    print("\n--- Takeaway ---")
    print(f"Rule-based is essentially free and instant, but only works because it had a\n"
          f"clean reference list of all 503 real company names to fuzzy-match against —\n"
          f"without that list, its accuracy would collapse. The LLM approach needs no\n"
          f"reference list at all (it uses trained knowledge of real companies), which\n"
          f"matters when you're cleaning entities you don't already have a master list\n"
          f"for. Its cost is small in absolute terms but scales linearly with volume in\n"
          f"a way rule-based cleaning doesn't — at large scale (millions of rows) that\n"
          f"gap compounds. A practical pipeline would run rule-based cleaning first and\n"
          f"only escalate low-confidence / unmatched rows to an LLM.")

    print(f"\nSaved to {summary_output_path}")
    return summary
