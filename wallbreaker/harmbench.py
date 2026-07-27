from __future__ import annotations

import asyncio
import csv
import random
from pathlib import Path

import httpx

DATASET_URL = (
    "https://raw.githubusercontent.com/centerforaisafety/HarmBench/main/"
    "data/behavior_datasets/harmbench_behaviors_text_all.csv"
)


def dataset_path() -> Path:
    return Path(__file__).resolve().parent.parent / "library" / "harmbench_behaviors.csv"


def is_cached() -> bool:
    return dataset_path().is_file()


def _download() -> str | None:
    path = dataset_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = httpx.get(DATASET_URL, timeout=30, follow_redirects=True)
        if resp.status_code != 200:
            return f"HarmBench download failed: HTTP {resp.status_code}"
        path.write_text(resp.text, encoding="utf-8")
        return None
    except httpx.HTTPError as exc:
        return f"HarmBench download failed: {exc}"


async def ensure(offline: bool = False) -> str | None:
    if is_cached():
        return None
    if offline:
        return "HarmBench not cached and offline."
    return await asyncio.to_thread(_download)


def load_behaviors() -> list[dict]:
    if not is_cached():
        return []
    rows = []
    with open(dataset_path(), encoding="utf-8") as handle:
        for r in csv.DictReader(handle):
            # skip contextual behaviors (they need a separate context string)
            if r.get("FunctionalCategory", "").strip() == "contextual":
                continue
            rows.append(
                {
                    "id": r.get("BehaviorID", ""),
                    "behavior": r.get("Behavior", "").strip(),
                    "category": r.get("SemanticCategory", "").strip(),
                }
            )
    return [r for r in rows if r["behavior"]]


def categories() -> list[str]:
    return sorted({b["category"] for b in load_behaviors()})


def sample(category: str | None = None, n: int = 8, seed: int = 0) -> list[dict]:
    behaviors = load_behaviors()
    if not behaviors:
        return []
    rng = random.Random(seed)
    if category:
        pool = [b for b in behaviors if b["category"] == category]
        rng.shuffle(pool)
        return pool[:n]
    # stratified: round-robin across categories for a balanced, unbiased battery
    by_cat: dict[str, list] = {}
    for b in behaviors:
        by_cat.setdefault(b["category"], []).append(b)
    for lst in by_cat.values():
        rng.shuffle(lst)
    out: list[dict] = []
    cats = sorted(by_cat)
    rng.shuffle(cats)
    i = 0
    while len(out) < n and any(by_cat[c] for c in cats):
        c = cats[i % len(cats)]
        if by_cat[c]:
            out.append(by_cat[c].pop())
        i += 1
    return out[:n]


async def battery(category: str | None = None, n: int = 8, seed: int = 0) -> list[str] | None:
    """Return n HarmBench behavior strings, downloading on first use. None if unavailable."""
    err = await ensure()
    if err or not is_cached():
        return None
    return [b["behavior"] for b in sample(category, n, seed)]
