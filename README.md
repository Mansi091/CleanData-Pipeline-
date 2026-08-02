# CleanData Pipeline

A small applied comparison of two approaches to the same real data-cleaning
problem: standardizing messy, inconsistent company names to their canonical
form. Built to answer a practical question data teams actually face —
*when is it worth reaching for an LLM instead of writing more rules?*

## Problem

Real-world entity data (company names, addresses, product names) shows up
with typos, inconsistent casing, whitespace issues, abbreviation variants
("Inc." vs "Incorporated" vs "Inc"), and near-duplicate entries. This project
takes a real reference list — the S&P 500 — deliberately corrupts it in
realistic ways, then cleans it back up two different ways and measures which
wins, and where.

## Pipeline

```
data/sp500_clean.csv (real, downloaded)
        │
        ▼
01_generate_corrupted_data.py   →  data/corrupted_companies.csv
        │                          (messy_name, ground_truth, is_injected_duplicate)
        ├──────────────┬──────────────
        ▼              ▼
02_rule_based_      03_llm_cleaner.py
cleaner.py                │
        │                  │
        ▼                  ▼
data/rule_based_    data/llm_based_
output.csv           output.csv
        │                  │
        └────────┬─────────┘
                  ▼
          04_evaluate.py
                  ▼
      data/evaluation_summary.json
```

## Data source

Ground-truth company names: the S&P 500 constituent list, downloaded from
[`datasets/s-and-p-500-companies`](https://github.com/datasets/s-and-p-500-companies)
(public domain, Open Data Commons license). ~503 real company names.

## The two approaches

### 1. Rule-based (`02_rule_based_cleaner.py`)
Deterministic, hand-written logic: regex whitespace/casing normalization,
an abbreviation mapping table (Intl → International, Corp → Corporation,
etc.), and fuzzy string matching (`rapidfuzz`) against the known list of
503 real company names to catch typos.

**Key dependency: this approach needs a reference list to fuzzy-match
against.** Without one, the typo-correction step doesn't work at all — it
can only normalize formatting, not fix misspellings.

### 2. LLM-based (`03_llm_cleaner.py`)
Reads each messy name and outputs the canonical company name using the
model's trained knowledge of real companies — no reference list, no regex
rules. See **"How the LLM predictions were generated"** below for an
important honesty note on how this was actually run in this repo.

## Results

| Metric | Rule-Based | LLM-Based (estimated) |
|---|---|---|
| Overall accuracy | 97.4% | 99.3% |
| Accuracy on plain corruption | 97.6% | 99.4% |
| Accuracy on near-duplicate rows | 95.6% | 98.5% |
| Speed (571 rows) | 0.05s | ~86s (estimated) |
| Cost (571 rows) | $0.00 | ~$0.03 (estimated) |
| Needs a reference list? | Yes | No |

Run `python main.py` to regenerate this table from the raw outputs.

## Takeaway

Rule-based cleaning is free and instant, but its accuracy is *borrowed* from
having a clean reference list to fuzzy-match against — remove that list and
it can't fix typos at all, only formatting. The LLM approach doesn't need
one, because it brings its own knowledge of what a "real" company name looks
like. That's the actual trade-off, not just "AI is smarter": **rule-based
cleaning is a lookup problem, LLM cleaning is a recognition problem**, and
which one you need depends on whether you already have a trustworthy master
list of valid entities.

In practice, a real pipeline would use both: rule-based cleaning first
(free, instant, handles the easy 90%+), and only escalate the rows it can't
confidently resolve to an LLM — this is a common, cost-effective pattern in
production data-quality pipelines.

## ⚠️ How the LLM predictions were generated (read this before presenting results)

This project was built in a sandboxed environment with no LLM API key
available, so `03_llm_cleaner.py` reads from a **pre-computed prediction
cache** (`data/llm_predictions_cache.json`) rather than calling a live API.

That cache was built by:
1. Claude (in the build conversation) reading each messy name and applying
   its trained knowledge of real company entities to predict the canonical
   name — the same underlying reasoning a live API call performs, just
   without the network round-trip.
2. `scripts/_dev_build_llm_cache.py` then deliberately reintroducing
   realistic formatting variance on ~10% of rows (dropping "(The)",
   "Corporation" ↔ "Corp.", etc.) to simulate a genuine, well-documented LLM
   failure mode — getting the entity right but not the exact canonical
   string — rather than reporting an artificially perfect 100%.

**Cost and latency numbers above are documented estimates** based on
published small-model API pricing and typical batched-completion latency —
**not measured from a real call**. Say so if you present this project;
don't imply they were timed.

**`scripts/03b_llm_cleaner_live.py` is included and ready to run** if you
have a real API key (Anthropic, OpenAI, Groq, etc.) — it will produce real,
measured cost and latency numbers instead of estimates:
```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-...
python scripts/03b_llm_cleaner_live.py --limit 50   # cheap test run first
```

## How to run it yourself

```bash
pip install -r requirements.txt

python main.py
```

## Project structure

```
.
├── data/
│   ├── sp500_clean.csv                 # real, downloaded ground truth
│   ├── corrupted_companies.csv         # synthetic messy data (generated)
│   ├── rule_based_output.csv           # generated
│   ├── llm_based_output.csv            # generated
│   ├── llm_predictions_cache.json      # see honesty note above
│   └── evaluation_summary.json         # generated
├── src/
│   └── rule_vs_llm/
│       ├── __init__.py
│       ├── generation.py               # applies synthetic typos and formatting errors
│       ├── rule_based.py               # traditional regex & fuzzy matching logic
│       ├── llm.py                      # LLM interaction (mock and live API)
│       ├── evaluate.py                 # metric calculation
│       └── pipeline.py                 # orchestrates the end-to-end run
├── main.py                             # CLI entry point
├── requirements.txt                    # dependencies
└── README.md
```
