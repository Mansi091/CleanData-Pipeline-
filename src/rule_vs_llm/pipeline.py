import os
from .generation import generate_corrupted_data
from .rule_based import run_rule_based_cleaner
from .llm import run_llm_cleaner_mock, run_llm_cleaner_live
from .evaluate import run_evaluation

def run_full_pipeline(data_dir: str = "data", live_llm: bool = False):
    """
    Runs the end-to-end data cleaning pipeline.
    """
    os.makedirs(data_dir, exist_ok=True)
    
    clean_csv = os.path.join(data_dir, "sp500_clean.csv")
    corrupted_csv = os.path.join(data_dir, "corrupted_companies.csv")
    rule_output_csv = os.path.join(data_dir, "rule_based_output.csv")
    llm_output_csv = os.path.join(data_dir, "llm_based_output.csv")
    
    rule_timing = os.path.join(data_dir, "rule_based_timing.txt")
    llm_timing = os.path.join(data_dir, "llm_timing_estimate.json")
    
    llm_cache = os.path.join(data_dir, "llm_predictions_cache.json")
    summary_json = os.path.join(data_dir, "evaluation_summary.json")

    print("\n--- STEP 1: Generating Corrupted Data ---")
    generate_corrupted_data(clean_csv, corrupted_csv)

    print("\n--- STEP 2: Running Rule-Based Cleaner ---")
    run_rule_based_cleaner(corrupted_csv, clean_csv, rule_output_csv, timing_path=rule_timing)

    print("\n--- STEP 3: Running LLM-Based Cleaner ---")
    if live_llm:
        run_llm_cleaner_live(corrupted_csv, llm_output_csv)
    else:
        run_llm_cleaner_mock(corrupted_csv, llm_cache, llm_output_csv, timing_path=llm_timing)

    print("\n--- STEP 4: Evaluating Results ---")
    run_evaluation(rule_output_csv, llm_output_csv, rule_timing, llm_timing, summary_json)

    print("\nPipeline execution finished successfully!")
