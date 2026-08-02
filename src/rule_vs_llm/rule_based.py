import re
import time
import pandas as pd
from rapidfuzz import process, fuzz

ABBREVIATION_MAP = {
    r"\bincorporated\b": "inc.",
    r"\bcorp\b\.?": "corporation",
    r"\bco\b\.?": "company",
    r"\bintl\b\.?": "international",
    r"\bint'l\b": "international",
    r"\bgrp\b\.?": "group",
    r"\bhldgs\b\.?": "holdings",
}

def normalize_whitespace(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip()

def normalize_casing(name: str) -> str:
    return name.strip()

def normalize_abbreviations(name: str) -> str:
    lowered = name.lower()
    for pattern, replacement in ABBREVIATION_MAP.items():
        lowered = re.sub(pattern, replacement, lowered)
    return lowered

def rule_based_clean(messy_name: str) -> str:
    name = normalize_whitespace(messy_name)
    name = normalize_abbreviations(name)
    name = name.strip().rstrip(".").strip()
    return name

def fuzzy_match_to_reference(cleaned_name: str, reference_names: list, threshold: int = 80):
    match = process.extractOne(cleaned_name, reference_names, scorer=fuzz.token_sort_ratio)
    if match and match[1] >= threshold:
        return match[0], match[1]
    return cleaned_name, None

def run_rule_based_cleaner(input_path: str, reference_path: str, output_path: str, timing_path: str = None):
    messy = pd.read_csv(input_path)
    reference = pd.read_csv(reference_path)["Security"].dropna().unique().tolist()
    reference_normalized = {normalize_abbreviations(normalize_whitespace(r)).rstrip("."): r for r in reference}
    reference_lookup_keys = list(reference_normalized.keys())

    start = time.time()

    predictions = []
    match_scores = []
    for messy_name in messy["messy_name"]:
        step1 = rule_based_clean(messy_name)
        matched_key, score = fuzzy_match_to_reference(step1, reference_lookup_keys)
        final_name = reference_normalized.get(matched_key, step1)
        predictions.append(final_name)
        match_scores.append(score)

    elapsed = time.time() - start

    out = messy.copy()
    out["rule_based_prediction"] = predictions
    out["fuzzy_match_score"] = match_scores
    out.to_csv(output_path, index=False)

    print(f"Rule-based cleaning complete: {len(out)} rows in {elapsed:.3f}s "
          f"({elapsed / len(out) * 1000:.2f} ms/row)")
    print(f"Saved to {output_path}")
    
    if timing_path:
        with open(timing_path, "w") as f:
            f.write(str(elapsed))
    
    return out
