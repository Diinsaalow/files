# Somali News Scraper
Automatic collection of Somali news articles for NLP dataset construction.

## Project Structure
```
somali_scraper/
│
├── Somali_News_Scraper.ipynb   ← Main notebook (start here)
│
├── scraper/
│   ├── __init__.py             ← Package exports
│   ├── config.py               ← All 15 site configs + scraper settings
│   ├── scraper.py              ← HTTP fetch, retry, pagination, extraction
│   ├── pipeline.py             ← Orchestrates sites × categories
│   └── utils.py                ← Checkpointing, logging, dedup, writers
│
├── data/
│   ├── raw/                    ← Per-site CSVs  (caasimada__siyaasad.csv …)
│   ├── checkpoints/            ← JSON progress files (auto-created)
│   └── final/                  ← Merged final CSVs per category
│
└── logs/                       ← Daily log files
```

## Quick Start
1. Open `Somali_News_Scraper.ipynb` in Jupyter
2. Run **Cell 0** to install dependencies, then restart the kernel
3. Run **Cell 1** to import the scraper
4. Run **Cell 3** to start the full pipeline

## Resuming After Interruption
Just re-run **Cell 3**. Checkpoints are saved every 100 articles
and at the end of every listing page — nothing is lost.

## Categories
| Somali       | English    | Est. available |
|--------------|------------|----------------|
| Siyaasad     | Politics   | 50,000+        |
| Amni         | Security   | 40,000+        |
| Caalamka     | World News | 35,000+        |

## Output Format (CSV columns)
| Column      | Description                      |
|-------------|----------------------------------|
| id          | Unique article ID                |
| site        | Source site name                 |
| category    | siyaasad / amni / caalamka       |
| url         | Original article URL             |
| title       | Cleaned headline                 |
| content     | Cleaned body text                |
| scraped_at  | Timestamp                        |
| word_count  | Body word count                  |

## Reliability Features
- Exponential backoff retry (up to 4 attempts per URL)
- Rotating User-Agent headers
- Per-site configurable request delay (default 2s + jitter)
- Checkpoint saves every 100 articles AND every listing page
- Cross-site title deduplication (MD5 hash)
- SSL error fallback
- Empty-page detection (stops pagination automatically)
- Quality gates: min title length 10 chars, min content 50 chars
