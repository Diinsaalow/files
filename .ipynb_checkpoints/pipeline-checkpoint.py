"""
pipeline.py — Scraping Pipeline Orchestrator
=============================================
Ties together config, scraper, checkpointing, and writing.
Call run_pipeline() from the Jupyter notebook.
"""

from config import SITES, SCRAPER_CONFIG, CATEGORIES

from scraper import (
    make_session,
    fetch,
    get_page_url,
    extract_article_links,
    extract_article,
    is_empty_listing,
)

from utils import (
    get_logger,
    Checkpoint,
    RawWriter,
    DedupCache,
    polite_sleep,
    print_progress,
    merge_raw_files,
)

logger = get_logger()
CFG    = SCRAPER_CONFIG


# ─── Single category × single site ───────────────────────────────────────────
def scrape_site_category(
    site_name:  str,
    category:   str,
    target:     int  = 10_000,
    max_pages:  int  = None,
    force_restart: bool = False,
) -> int:
    """
    Scrape all articles for one (site, category) pair.
    Resumes from checkpoint automatically unless force_restart=True.

    Returns the number of new articles written in this run.
    """
    site_cfg = SITES.get(site_name)
    if not site_cfg:
        logger.error(f"Unknown site: {site_name}")
        return 0

    cat_url = site_cfg["categories"].get(category)
    if not cat_url:
        logger.warning(f"{site_name} has no URL configured for category '{category}'")
        return 0

    max_pages = max_pages or CFG["max_pages_per_category"]

    # ── Setup ──
    ckpt      = Checkpoint(site_name, category)
    writer    = RawWriter(site_name, category)
    dedup     = DedupCache(category)
    session   = make_session()
    delay     = site_cfg.get("delay", 2.0)
    link_sel  = site_cfg["article_link_sel"]
    pagcfg    = site_cfg["pagination"]

    if force_restart:
        ckpt.delete()
        ckpt = Checkpoint(site_name, category)

    start_page   = max(1, ckpt.last_page)    # resume from last checkpoint
    scraped_urls = ckpt.scraped_urls
    new_count    = 0

    # ADD: sync count from writer if checkpoint was wiped but CSV still has data
    if ckpt.article_count == 0 and writer.count > 0:
        ckpt.article_count = writer.count
        ckpt.save()

    logger.info(
        f"▶ [{site_name}] [{category}] "
        f"Starting at page {start_page} | "
        f"checkpoint: {ckpt.article_count} | writer: {writer.count}"
    )

    # ── Pagination loop ───────────────────────────────────────────────────────
    for page_num in range(start_page, max_pages + 1):

        # Stop if target already reached across all sites
        if ckpt.article_count >= target:
            logger.info(f"  [{site_name}][{category}] Target reached. Stopping.")
            break

        page_url = get_page_url(cat_url, page_num, pagcfg)
        logger.debug(f"  Fetching listing page {page_num}: {page_url}")

        soup = fetch(page_url, session)

        if soup is None or is_empty_listing(soup, link_sel, site_cfg["base_url"]):
            logger.info(f"  [{site_name}][{category}] Empty/unreachable page {page_num}. End of pagination.")
            break

        article_links = extract_article_links(soup, site_cfg["base_url"], link_sel, scraped_urls)

        if not article_links:
            logger.info(f"  [{site_name}][{category}] No new links on page {page_num}. Stopping.")
            break

        logger.info(f"  [{site_name}][{category}] Page {page_num}: {len(article_links)} links found")

        # ── Article loop ──────────────────────────────────────────────────────
        for url in article_links:

            if ckpt.article_count >= target:
                break

            if url in scraped_urls:
                continue

            polite_sleep(delay, jitter=0.8)
            art_soup = fetch(url, session)

            if art_soup is None:
                ckpt.mark_url(url)
                scraped_urls.add(url)
                continue

            article = extract_article(art_soup, url, site_cfg)

            if article is None:
                ckpt.mark_url(url)
                scraped_urls.add(url)
                continue

            if dedup.is_duplicate(article["title"]):
                logger.debug(f"  Duplicate title skipped: {article['title'][:60]}")
                ckpt.mark_url(url)
                scraped_urls.add(url)
                continue

            # Write record
            record = {
                "site":     site_name,
                "category": category,
                **article,
            }
            writer.write(record)
            ckpt.mark_url(url)
            scraped_urls.add(url)
            ckpt.article_count = writer.count
            new_count += 1

            logger.debug(f"  ✔ [{ckpt.article_count}] {article['title'][:70]}")

            # Periodic checkpoint save
            if new_count % CFG["checkpoint_every"] == 0:
                ckpt.last_page = page_num
                ckpt.save()
                dedup.save()
                logger.info(
                    f"  ✦ Checkpoint saved: {ckpt.article_count} articles "
                    f"({site_name}/{category}, page {page_num})"
                )

        # Save checkpoint at end of each listing page
        ckpt.last_page = page_num
        ckpt.save()
        polite_sleep(delay, jitter=1.0)

    # Final save
    ckpt.save()
    dedup.save()
    logger.info(
        f"✔ [{site_name}][{category}] Done. "
        f"New: {new_count} | Total: {ckpt.article_count}"
    )
    return new_count


# ─── Full pipeline ────────────────────────────────────────────────────────────
def run_pipeline(
    categories:       list  = None,
    sites:            list  = None,
    target_per_cat:   int   = 10_000,
    skip_completed:   bool  = True,
    force_restart:    bool  = False,
) -> dict:
    """
    Run the full scraping pipeline across all sites and categories.

    Parameters
    ----------
    categories     : list of category names to scrape (default: all 3)
    sites          : list of site names to use (default: all configured)
    target_per_cat : stop scraping a category after this many articles
    skip_completed : skip (site, category) pairs that already hit the target
    force_restart  : wipe all checkpoints and start fresh

    Returns
    -------
    dict : { category: total_article_count }
    """
    categories = categories or CATEGORIES
    sites      = sites      or list(SITES.keys())
    totals     = {cat: 0 for cat in categories}

    logger.info("=" * 60)
    logger.info(" SOMALI NEWS SCRAPER — PIPELINE START")
    logger.info(f" Categories : {categories}")
    logger.info(f" Sites      : {sites}")
    logger.info(f" Target/cat : {target_per_cat:,}")
    logger.info("=" * 60)

    for category in categories:
        logger.info(f"\n{'━'*60}")
        logger.info(f"  CATEGORY: {category.upper()}")
        logger.info(f"{'━'*60}")

        for site_name in sites:
            # Count already collected for this category across ALL sites
            current_total = _count_category_total(category)
            totals[category] = current_total

            if skip_completed and current_total >= target_per_cat:
                logger.info(f"  [{category}] Target already reached ({current_total:,}). Skipping remaining sites.")
                break

            remaining = target_per_cat - current_total
            logger.info(f"\n  → {site_name} | {remaining:,} articles still needed for {category}")

            if site_name not in SITES:
                logger.warning(f"  Site '{site_name}' not in config. Skipping.")
                continue

            if category not in SITES[site_name]["categories"]:
                logger.info(f"  {site_name} has no '{category}' category configured. Skipping.")
                continue

            scrape_site_category(
                site_name=site_name,
                category=category,
                target=remaining,
                force_restart=force_restart,
            )

        # Refresh total after all sites for this category
        totals[category] = _count_category_total(category)

    # Print summary
    print_progress(totals, target=target_per_cat)

    # Merge into final files
    logger.info("\nMerging raw files into final datasets…")
    for category in categories:
        merge_raw_files(category, logger)

    logger.info("\n✅ Pipeline complete.")
    return totals


# ─── Helper ───────────────────────────────────────────────────────────────────
def _count_category_total(category: str) -> int:
    """Count total unique articles across all raw CSV files for a category."""
    import csv
    from utils import RAW_DIR
    total = 0
    for fp in RAW_DIR.glob(f"*__{category}.csv"):
        with open(fp, encoding="utf-8") as f:
            total += max(0, sum(1 for _ in f) - 1)
    return total

   

def get_status() -> dict:
    """Return current article counts per (site, category). Call from notebook."""
    from utils import RAW_DIR
    import csv
    status = {}
    for fp in RAW_DIR.glob("*.csv"):
        stem   = fp.stem                       # e.g. "caasimada__siyaasad"
        parts  = stem.split("__", 1)
        if len(parts) != 2:
            continue
        site, cat = parts
        with open(fp, encoding="utf-8") as f:
            count = max(0, sum(1 for _ in f) - 1)
        status[f"{site}/{cat}"] = count
    return status
