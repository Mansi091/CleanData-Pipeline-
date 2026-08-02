import random
import re
import pandas as pd

random.seed(42)

SUFFIX_VARIANTS = {
    "Inc.": ["Inc.", "Inc", "Incorporated", ", Inc.", ", Inc"],
    "Corporation": ["Corporation", "Corp.", "Corp", "Corp."],
    "Company": ["Company", "Co.", "Co"],
    "International": ["International", "Intl.", "Intl", "Int'l"],
    "Group": ["Group", "Grp"],
    "Holdings": ["Holdings", "Hldgs"],
}

KEYBOARD_NEIGHBORS = {
    "a": "sq", "b": "vn", "c": "xv", "d": "sf", "e": "wr", "f": "dg",
    "g": "fh", "h": "gj", "i": "uo", "j": "hk", "k": "jl", "l": "k",
    "m": "n", "n": "bm", "o": "ip", "p": "o", "q": "wa", "r": "et",
    "s": "ad", "t": "ry", "u": "yi", "v": "cb", "w": "qe", "x": "zc",
    "y": "tu", "z": "x",
}

def apply_casing_noise(name: str) -> str:
    choice = random.random()
    if choice < 0.25:
        return name.upper()
    if choice < 0.45:
        return name.lower()
    if choice < 0.55:
        return name.title()
    return name

def apply_whitespace_noise(name: str) -> str:
    if random.random() < 0.3:
        name = re.sub(r" ", "  ", name, count=1)
    if random.random() < 0.15:
        name = " " + name
    if random.random() < 0.15:
        name = name + " "
    return name

def apply_suffix_swap(name: str) -> str:
    for canonical, variants in SUFFIX_VARIANTS.items():
        if canonical in name:
            replacement = random.choice(variants)
            return name.replace(canonical, replacement)
    return name

def apply_typo(name: str) -> str:
    if len(name) < 4:
        return name
    op = random.choice(["swap", "drop", "insert", "keyneighbor"])
    idx = random.randint(1, len(name) - 2)
    chars = list(name)

    if op == "swap" and idx < len(chars) - 1:
        chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
    elif op == "drop":
        del chars[idx]
    elif op == "insert":
        chars.insert(idx, chars[idx])
    elif op == "keyneighbor":
        c = chars[idx].lower()
        if c in KEYBOARD_NEIGHBORS:
            chars[idx] = random.choice(KEYBOARD_NEIGHBORS[c])

    return "".join(chars)

def corrupt_name(name: str, n_dupes: int = 0):
    variants = []

    messy = name
    if random.random() < 0.5:
        messy = apply_suffix_swap(messy)
    if random.random() < 0.35:
        messy = apply_typo(messy)
    messy = apply_whitespace_noise(messy)
    messy = apply_casing_noise(messy)
    variants.append((messy.strip() if random.random() < 0.7 else messy, False))

    for _ in range(n_dupes):
        dup = name
        if random.random() < 0.6:
            dup = apply_suffix_swap(dup)
        if random.random() < 0.5:
            dup = apply_typo(dup)
        dup = apply_whitespace_noise(dup)
        dup = apply_casing_noise(dup)
        variants.append((dup, True))

    return variants

def generate_corrupted_data(input_path: str, output_path: str):
    clean = pd.read_csv(input_path)
    names = clean["Security"].dropna().unique().tolist()

    rows = []
    row_id = 1
    for name in names:
        n_dupes = 1 if random.random() < 0.15 else 0
        for messy_name, is_dupe in corrupt_name(name, n_dupes=n_dupes):
            rows.append({
                "row_id": row_id,
                "messy_name": messy_name,
                "ground_truth": name,
                "is_injected_duplicate": is_dupe,
            })
            row_id += 1

    out = pd.DataFrame(rows).sample(frac=1, random_state=7).reset_index(drop=True)
    out["row_id"] = range(1, len(out) + 1)
    out.to_csv(output_path, index=False)

    print(f"Generated {len(out)} messy rows from {len(names)} clean S&P 500 company names")
    print(f"  Injected near-duplicates: {out['is_injected_duplicate'].sum()}")
    print(f"Saved to {output_path}")
    return out
