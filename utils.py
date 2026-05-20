"""
utils.py — Checkpoint, Logging, Rate-limiting & Deduplication Utilities
========================================================================
"""

import os
import json
import time
import random
import hashlib
import logging
import csv
from datetime import datetime
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent.parent
DATA_DIR        = BASE_DIR / "data"
RAW_DIR         = DATA_DIR / "raw"
CHECKPOINT_DIR  = DATA_DIR / "checkpoints"
FINAL_DIR       = DATA_DIR / "final"
LOG_DIR         = BASE_DIR / "logs"

for d in [RAW_DIR, CHECKPOINT_DIR, FINAL_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ─── Logging ─────────────────────────────────────────────────────────────────
def get_logger(name: str = "somali_scraper") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    # File handler (full debug log)
    fh = logging.FileHandler(LOG_DIR / f"scraper_{_today()}.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console handler (INFO and above)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def _today():
    return datetime.now().strftime("%Y%m%d")


# ─── Checkpointing ───────────────────────────────────────────────────────────
class Checkpoint:
    """
    Persists scraping progress so runs can resume after interruption.

    Checkpoint file layout:
    {
      "site": "caasimada",
      "category": "siyaasad",
      "last_page": 14,
      "scraped_urls": ["https://...", ...],
      "article_count": 342,
      "updated_at": "2024-05-01 12:34:56"
    }
    """

    def __init__(self, site: str, category: str):
        self.site     = site
        self.category = category
        self.path     = CHECKPOINT_DIR / f"{site}__{category}.json"
        self._data    = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return {
            "site":          self.site,
            "category":      self.category,
            "last_page":     0,
            "scraped_urls":  [],
            "article_count": 0,
            "updated_at":    None,
        }

    def save(self):
        self._data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ── properties ──
    @property
    def last_page(self) -> int:
        return self._data["last_page"]

    @last_page.setter
    def last_page(self, v: int):
        self._data["last_page"] = v

    @property
    def scraped_urls(self) -> set:
        return set(self._data["scraped_urls"])

    def mark_url(self, url: str):
        if url not in self._data["scraped_urls"]:
            self._data["scraped_urls"].append(url)

    @property
    def article_count(self) -> int:
        return self._data["article_count"]

    @article_count.setter
    def article_count(self, v: int):
        self._data["article_count"] = v
    
    @property
    def url_index(self) -> int:
        return self._data.get("url_index", 0)

    @url_index.setter
    def url_index(self, v: int):
        self._data["url_index"] = v

    def delete(self):
        """Remove checkpoint (used after a category is complete)."""
        if self.path.exists():
            self.path.unlink()


# ─── Raw CSV writer ──────────────────────────────────────────────────────────
class RawWriter:
    """
    Appends scraped articles to a per-site-per-category CSV.
    Creates the file with headers on first write.
    """

    FIELDS = ["id", "site", "category", "url", "title",
              "content", "scraped_at", "word_count"]

    def __init__(self, site: str, category: str):
        self.path = RAW_DIR / f"{site}__{category}.csv"
        self._init_file()
        self._counter = self._count_existing()

    def _init_file(self):
        if not self.path.exists():
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=self.FIELDS).writeheader()

    def _count_existing(self) -> int:
        if not self.path.exists():
            return 0
        with open(self.path, encoding="utf-8") as f:
            return max(0, sum(1 for _ in f) - 1)   # minus header

    def write(self, record: dict):
        self._counter += 1
        record["id"] = f"{record['site']}__{record['category']}__{self._counter:06d}"
        record["word_count"] = len(str(record.get("content", "")).split())
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.FIELDS, extrasaction="ignore")
            w.writerow(record)

    @property
    def count(self) -> int:
        return self._counter


# ─── Deduplication ───────────────────────────────────────────────────────────
class DedupCache:
    """
    In-memory + disk-backed set of seen title hashes.
    Prevents duplicate articles from being saved.
    """

    def __init__(self, category: str):
        self.path = CHECKPOINT_DIR / f"dedup__{category}.json"
        self._seen: set = self._load()

    def _load(self) -> set:
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                return set(json.load(f))
        return set()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(list(self._seen), f)

    def is_duplicate(self, title: str) -> bool:
        h = hashlib.md5(title.strip().lower().encode()).hexdigest()
        if h in self._seen:
            return True
        self._seen.add(h)
        return False


# ─── Rate limiter ────────────────────────────────────────────────────────────
def polite_sleep(base: float = 2.0, jitter: float = 1.0):
    """Sleep for base ± random jitter seconds to avoid hammering servers."""
    time.sleep(base + random.uniform(0, jitter))


# ─── Progress summary ────────────────────────────────────────────────────────
def print_progress(counts: dict, target: int = 10000):
    """Pretty-print current collection counts for each category."""
    print("\n" + "═" * 52)
    print(f"  {'CATEGORY':<20} {'COLLECTED':>10} {'TARGET':>8} {'%':>6}")
    print("─" * 52)
    for cat, n in counts.items():
        pct = min(100, n / target * 100)
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {cat:<20} {n:>10,} {target:>8,} {pct:>5.1f}%")
        print(f"  {bar}")
    print("═" * 52 + "\n")


# ─── Merge helper ────────────────────────────────────────────────────────────
def merge_raw_files(category: str, logger=None):
    """
    Merge all per-site CSVs for a given category into one final CSV.
    Deduplicates by title hash across sites.
    """
    log = logger or get_logger()
    out_path = FINAL_DIR / f"{category}_final.csv"
    seen_hashes = set()
    written = 0

    files = list(RAW_DIR.glob(f"*__{category}.csv"))
    if not files:
        log.warning(f"No raw files found for category: {category}")
        return

    with open(out_path, "w", newline="", encoding="utf-8") as fout:
        writer = None
        for fp in files:
            with open(fp, encoding="utf-8") as fin:
                reader = csv.DictReader(fin)
                if writer is None:
                    writer = csv.DictWriter(fout, fieldnames=reader.fieldnames or [])
                    writer.writeheader()
                for row in reader:
                    h = hashlib.md5(row.get("title", "").strip().lower().encode()).hexdigest()
                    if h in seen_hashes:
                        continue
                    seen_hashes.add(h)
                    writer.writerow(row)
                    written += 1

    log.info(f"[merge] {category}: {written:,} unique articles → {out_path.name}")
    return out_path
