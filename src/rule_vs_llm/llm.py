import json
import time
import pandas as pd

EST_COST_PER_1000_ROWS_USD = 0.05
EST_LATENCY_PER_ROW_SECONDS = 0.15

def run_llm_cleaner_mock(input_path: str, cache_path: str, output_path: str, timing_path: str = None):
    messy = pd.read_csv(input_path)
    with open(cache_path) as f:
        cache = json.load(f)

    start = time.time()
    predictions = [cache.get(str(rid), None) for rid in messy["row_id"]]
    lookup_time = time.time() - start

    out = messy.copy()
    out["llm_prediction"] = predictions
    out.to_csv(output_path, index=False)

    n = len(out)
    est_total_latency = n * EST_LATENCY_PER_ROW_SECONDS
    est_total_cost = (n / 1000) * EST_COST_PER_1000_ROWS_USD

    print(f"LLM-based cleaning complete: {n} rows")
    print(f"  Cache lookup time (not real inference): {lookup_time:.4f}s")
    print(f"  ESTIMATED live-API latency: ~{est_total_latency:.1f}s total "
          f"(~{EST_LATENCY_PER_ROW_SECONDS*1000:.0f}ms/row, documented assumption)")
    print(f"  ESTIMATED live-API cost: ~${est_total_cost:.4f} total "
          f"(~${EST_COST_PER_1000_ROWS_USD}/1000 rows, documented assumption)")
    print(f"Saved to {output_path}")

    if timing_path:
        with open(timing_path, "w") as f:
            json.dump({
                "rows": n,
                "estimated_total_latency_seconds": est_total_latency,
                "estimated_total_cost_usd": est_total_cost,
                "note": "ESTIMATED, not measured — see script docstring",
            }, f, indent=2)
            
    return out

PROMPT_TEMPLATE = """You are a master data cleaner.
I will give you a list of messy, typo-ridden company names (one per line).
Your job is to identify the TRUE, CANONICAL name of the company and return exactly that name, one per line.
Do not output anything else. Do not number the list.

For example, if you see:
microooosoft  corp
at& t inc
alphabet (google)

You should return:
Microsoft Corporation
AT&T
Alphabet

Here are the names to clean:
{names}"""

def call_llm(batch_names: list[str]) -> tuple[list[str], int, int]:
    import groq
    import os
    
    client = groq.Groq()
    prompt = PROMPT_TEMPLATE.format(names="\n".join(batch_names))

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.choices[0].message.content
    predictions = [line.strip() for line in text.strip().split("\n") if line.strip()]
    usage = response.usage

    return predictions, usage.prompt_tokens, usage.completion_tokens

def run_llm_cleaner_live(input_path: str, output_path: str, batch_size: int = 20, limit: int = None):
    messy = pd.read_csv(input_path)
    if limit:
        messy = messy.head(limit)

    predictions = []
    total_input_tokens = 0
    total_output_tokens = 0

    print(f"Running LIVE LLM cleaning on {len(messy)} rows (batch size {batch_size})...")
    start = time.time()

    for i in range(0, len(messy), batch_size):
        batch = messy.iloc[i:i + batch_size]
        batch_names = batch["messy_name"].tolist()
        try:
            batch_preds, in_toks, out_toks = call_llm(batch_names)
            total_input_tokens += in_toks
            total_output_tokens += out_toks

            if len(batch_preds) != len(batch_names):
                print(f"WARNING: Batch {i} returned {len(batch_preds)} predictions for {len(batch_names)} names. Padding with missing values.")
                while len(batch_preds) < len(batch_names):
                    batch_preds.append(batch_names[len(batch_preds)])
                batch_preds = batch_preds[:len(batch_names)]

            predictions.extend(batch_preds)
        except Exception as e:
            print(f"ERROR on batch {i}: {e}")
            predictions.extend(batch_names)

        time.sleep(0.5)

    elapsed = time.time() - start

    out = messy.copy()
    out["llm_prediction"] = predictions
    out.to_csv(output_path, index=False)
    
    print(f"Completed in {elapsed:.2f}s")
    print(f"Tokens used: {total_input_tokens} input, {total_output_tokens} output")
    
    return out
