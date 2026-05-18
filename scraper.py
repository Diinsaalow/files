"""
scraper.py — Core Scraping Engine
==================================
Handles HTTP fetching, pagination, article link discovery,
headline + content extraction, and retry/backoff logic.
"""

import re
import time
import random
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from config import USER_AGENTS, SCRAPER_CONFIG
from utils import get_logger, polite_sleep

logger = get_logger()
CFG    = SCRAPER_CONFIG


# ─── Session factory ─────────────────────────────────────────────────────────
def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent":      random.choice(USER_AGENTS),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "so,ar;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection":      "keep-alive",
        "DNT":             "1",
    })
    return s


# ─── HTTP fetch with retry ────────────────────────────────────────────────────
def fetch(url: str, session: requests.Session, retries: int = None) -> BeautifulSoup | None:
    """
    Fetch a URL and return a BeautifulSoup object.
    Retries with exponential backoff on transient failures.
    Returns None if all retries fail.
    """
    max_retries   = retries if retries is not None else CFG["max_retries"]
    backoff       = CFG["backoff_factor"]
    timeout       = CFG["request_timeout"]

    for attempt in range(1, max_retries + 1):
        try:
            # Rotate User-Agent on each retry
            session.headers["User-Agent"] = random.choice(USER_AGENTS)

            resp = session.get(url, timeout=timeout, allow_redirects=True)

            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "lxml")

            elif resp.status_code == 404:
                logger.debug(f"404 → skipping: {url}")
                return None

            elif resp.status_code in (429, 503):
                wait = backoff ** attempt + random.uniform(1, 3)
                logger.warning(f"Rate-limited ({resp.status_code}). Waiting {wait:.1f}s… (attempt {attempt}/{max_retries})")
                time.sleep(wait)

            elif resp.status_code in (403, 401):
                logger.warning(f"Access denied ({resp.status_code}): {url}")
                return None

            else:
                wait = backoff ** attempt
                logger.warning(f"HTTP {resp.status_code} on {url}. Retrying in {wait:.1f}s…")
                time.sleep(wait)

        except requests.exceptions.SSLError:
            logger.warning(f"SSL error on {url} — retrying without verification")
            try:
                resp = session.get(url, timeout=timeout, verify=False)
                if resp.status_code == 200:
                    return BeautifulSoup(resp.text, "lxml")
            except Exception as e:
                logger.error(f"SSL retry failed: {e}")

        except requests.exceptions.ConnectionError as e:
            wait = backoff ** attempt
            logger.warning(f"Connection error ({e}). Waiting {wait:.1f}s… (attempt {attempt}/{max_retries})")
            time.sleep(wait)

        except requests.exceptions.Timeout:
            wait = backoff ** attempt
            logger.warning(f"Timeout on {url}. Waiting {wait:.1f}s… (attempt {attempt}/{max_retries})")
            time.sleep(wait)

        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    logger.error(f"All {max_retries} attempts failed for: {url}")
    return None


# ─── Pagination ───────────────────────────────────────────────────────────────
def get_page_url(base_cat_url: str, page: int, pagination_cfg: dict) -> str:
    """Build the URL for a specific listing page number."""
    if page <= 1:
        return base_cat_url

    ptype = pagination_cfg.get("type", "path")

    if ptype == "path":
        pattern = pagination_cfg.get("pattern", "page/{n}/")
        suffix  = pattern.replace("{n}", str(page))
        return base_cat_url.rstrip("/") + "/" + suffix

    elif ptype == "query":
        param = pagination_cfg.get("param", "page")
        sep   = "&" if "?" in base_cat_url else "?"
        return f"{base_cat_url}{sep}{param}={page}"

    else:
        return base_cat_url


# ─── Article link discovery ───────────────────────────────────────────────────
def extract_article_links(
    soup: BeautifulSoup,
    base_url: str,
    link_sel: str,
    already_seen: set,
) -> list[str]:
    """
    Extract article URLs from a listing/category page.
    Falls back to heuristic link detection if CSS selector yields nothing.
    """
    links = []

    # Primary: use site-specific CSS selector
    for a in soup.select(link_sel):
        href = a.get("href", "")
        if href:
            full = urljoin(base_url, href)
            if full not in already_seen and _looks_like_article(full, base_url):
                links.append(full)

    # Fallback: heuristic — look for links with article-like URL patterns
    if not links:
        for a in soup.find_all("a", href=True):
            href = urljoin(base_url, a["href"])
            if href not in already_seen and _looks_like_article(href, base_url):
                links.append(href)

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for l in links:
        if l not in seen:
            seen.add(l)
            deduped.append(l)

    return deduped


def _looks_like_article(url: str, base_url: str) -> bool:
    """
    Heuristic: does this URL look like an article (not a category/tag/page)?
    """
    parsed    = urlparse(url)
    base_host = urlparse(base_url).netloc

    # Must be same domain
    if base_host not in parsed.netloc:
        return False

    path = parsed.path.lower()

    # Skip obvious non-articles
    skip_patterns = [
        "/category/", "/tag/", "/author/", "/page/", "/feed/",
        "/wp-admin/", "/wp-content/", "#", "?s=", "/search/",
        ".jpg", ".png", ".pdf", ".mp3", ".mp4", "/cdn-cgi/",
    ]
    for pat in skip_patterns:
        if pat in path:
            return False

    # Must have at least one path segment with meaningful length
    segments = [s for s in path.split("/") if s]
    if not segments:
        return False

    # Likely an article if path is deep enough or contains numbers (date/ID)
    has_slug = any(len(s) > 5 for s in segments)
    has_date_or_id = bool(re.search(r"\d{4}", path))

    return has_slug or has_date_or_id


# ─── Article extraction ───────────────────────────────────────────────────────
def extract_article(
    soup: BeautifulSoup,
    url: str,
    site_cfg: dict,
) -> dict | None:
    """
    Extract title and content from an article page.
    Tries multiple CSS selectors in priority order.
    Returns None if minimum quality thresholds aren't met.
    """
    title   = _try_selectors(soup, site_cfg["title_sel"])
    content = _try_selectors(soup, site_cfg["content_sel"], join=True)

    if not title:
        # Last-resort: use <title> tag, strip site name suffix
        raw = soup.find("title")
        if raw:
            title = re.split(r"\s*[|\-–—]\s*", raw.get_text())[0].strip()

    if not content:
        # Last-resort: collect all <p> tags from <main> or <article>
        container = soup.find("main") or soup.find("article") or soup.body
        if container:
            paragraphs = container.find_all("p")
            content = " ".join(p.get_text(" ", strip=True) for p in paragraphs)

    # Quality gates
    if not title or len(title) < CFG["min_title_length"]:
        logger.debug(f"Rejected (title too short): {url}")
        return None
    if not content or len(content) < CFG["min_content_length"]:
        logger.debug(f"Rejected (content too short): {url}")
        return None

    return {
        "url":        url,
        "title":      clean_text(title),
        "content":    clean_text(content),
        "scraped_at": _now(),
    }


def _try_selectors(soup: BeautifulSoup, selectors: list, join: bool = False) -> str:
    """Try CSS selectors in order; return first non-empty match."""
    for sel in selectors:
        try:
            if join:
                tags = soup.select(sel)
                if tags:
                    text = " ".join(t.get_text(" ", strip=True) for t in tags)
                    if text.strip():
                        return text.strip()
            else:
                tag = soup.select_one(sel)
                if tag:
                    text = tag.get_text(" ", strip=True)
                    if text.strip():
                        return text.strip()
        except Exception:
            continue
    return ""


def clean_text(text: str) -> str:
    """Normalize whitespace, strip zero-width chars and HTML entities."""
    if not text:
        return ""
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)  # zero-width chars
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


# ─── Empty page detector ──────────────────────────────────────────────────────
def is_empty_listing(soup: BeautifulSoup, link_sel: str, base_url: str = "") -> bool:
    """
    Returns True if a listing page has no article links,
    signalling we've gone past the last page.
    Checks CSS selector first, then falls back to heuristic scan.
    """
    if soup is None:
        return True
    body = soup.get_text().lower()
    if "nothing found" in body or "no posts" in body:
        return True
    # Primary: CSS selector
    if soup.select(link_sel):
        return False
    # Fallback: heuristic — if ANY article-like link exists, page is not empty
    if base_url:
        for a in soup.find_all("a", href=True):
            href = urljoin(base_url, a["href"])
            if _looks_like_article(href, base_url):
                return False
    return True


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
