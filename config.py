"""
config.py — Somali News Scraper Site Configurations
=====================================================
All category URL patterns and extraction rules per site.
Categories: Siyaasad (Politics), Amni (Security), Caalamka (World)
"""

CATEGORIES = ["siyaasad", "amni", "caalamka"]

CATEGORY_ALIASES = {
    "siyaasad": ["siyaasad", "politics", "political", "dowladda", "xukuumadda"],
    "amni":     ["amni", "security", "dagaal", "amniga", "colaad", "military"],
    "caalamka": ["caalamka", "world", "international", "dunida", "aduunka", "foreign"],
}

# ─── Site registry ────────────────────────────────────────────────────────────
# Each site entry:
#   base_url        : root domain (used for resolving relative links)
#   categories      : dict[label → category page URL]
#   article_link_sel: CSS selector that finds <a> tags of article links on listing pages
#   title_sel       : CSS selectors tried in order to extract the headline
#   content_sel     : CSS selectors tried in order to extract body text
#   pagination      : how to detect/build next-page URLs
#     type "query"  : appends ?page=N or /page/N
#     type "next"   : follows a "next page" link matching next_sel
#   delay           : per-request sleep in seconds (be respectful)
#   js_render       : True = needs Selenium (skip if not installed)

SITES = {

    # ── TIER 1 ────────────────────────────────────────────────────────────────
#     "caasimada": {
#     "base_url": "https://www.caasimada.net",
#     "categories": {
#         "siyaasad": "https://www.caasimada.net/category/wararka/",
#     },
# }

    "caasimada": {
        "base_url": "https://caasimada.net",
        "categories": {
            "siyaasad": "https://www.caasimada.net/category/wararka/",
            "amni":     "https://caasimada.net/category/amni/",
            "caalamka": "https://caasimada.net/category/caalamka/",
        },
        "article_link_sel": "h2.entry-title a, h3.entry-title a, .post-title a",
        "title_sel":   ["h1.entry-title", "h1.post-title", "h1"],
        "content_sel": [".entry-content p", ".post-content p", "article p"],
        "pagination": {"type": "path", "pattern": "page/{n}/"},
        "delay": 2.0,
        "js_render": False,
    },

   "goobjoog": {
    "base_url": "https://goobjoog.com",
    "categories": {
        "siyaasad": "https://goobjoog.com/qayb/war/dalka/",
        "amni":     "https://goobjoog.com/qayb/amniga/",
        "caalamka": "https://goobjoog.com/qayb/war/caalamka/",
    },
    "article_link_sel": (
        ".jeg_post_title a, "
        ".jeg_post_title > a, "
        "h3.jeg_post_title a, "
        "h2.jeg_post_title a, "
        ".entry-title a, "
        "h2.entry-title a, "
        "h3.entry-title a"
    ),
    "title_sel": [
        "h1.jeg_post_title",
        "h1.entry-title",
        ".jeg_post_title",
        "h1",
    ],
    "content_sel": [
        ".content-inner p",
        ".jeg_main_content p",
        ".entry-content p",
        ".td-post-content p",
        "article p",
    ],
    "pagination": {"type": "path", "pattern": "page/{n}/"},
    "delay": 1.5,
    "js_render": False,
},

    "radiodalsan": {
        "base_url": "https://radiodalsan.com",
        "categories": {
            "siyaasad": "https://radiodalsan.com/category/siyaasad/",
            "amni":     "https://radiodalsan.com/category/amni/",
            "caalamka": "https://radiodalsan.com/category/caalamka/",
        },
        "article_link_sel": "h2.entry-title a, h3.entry-title a",
        "title_sel":   ["h1.entry-title", "h1"],
        "content_sel": [".entry-content p", ".post-content p"],
        "pagination": {"type": "path", "pattern": "page/{n}/"},
        "delay": 2.0,
        "js_render": False,
    },

    "hiiraan": {
        "base_url": "https://www.hiiraan.com",
        "categories": {
            "siyaasad": "https://www.hiiraan.com/news4/somali/",
            "amni":     "https://www.hiiraan.com/news4/somali/",  # filter by keyword
            "caalamka": "https://www.hiiraan.com/news4/somali/",
        },
        "article_link_sel": "a[href*='/news4/somali/']",
        "title_sel":   ["h1", ".article_title", "title"],
        "content_sel": [".article_body p", "#article_body p", "p"],
        "pagination": {"type": "query", "param": "page", "start": 1},
        "delay": 2.5,
        "js_render": False,
    },

    "mustaqbalmedia": {
        "base_url": "https://mustaqbalmedia.net",
        "categories": {
            "siyaasad": "https://mustaqbalmedia.net/category/siyaasad/",
            "amni":     "https://mustaqbalmedia.net/category/amni/",
            "caalamka": "https://mustaqbalmedia.net/category/caalamka/",
        },
        "article_link_sel": "h2.entry-title a, h3.entry-title a",
        "title_sel":   ["h1.entry-title", "h1"],
        "content_sel": [".entry-content p"],
        "pagination": {"type": "path", "pattern": "page/{n}/"},
        "delay": 2.0,
        "js_render": False,
    },

    # ── TIER 2 ────────────────────────────────────────────────────────────────

    "horseedmedia": {
        "base_url": "https://horseedmedia.net",
        "categories": {
            "siyaasad": "https://horseedmedia.net/category/siyaasad/",
            "amni":     "https://horseedmedia.net/category/amni/",
            "caalamka": "https://horseedmedia.net/category/caalamka/",
        },
        "article_link_sel": "h2.entry-title a, h3.entry-title a",
        "title_sel":   ["h1.entry-title", "h1"],
        "content_sel": [".entry-content p"],
        "pagination": {"type": "path", "pattern": "page/{n}/"},
        "delay": 2.0,
        "js_render": False,
    },

    "garoweonline": {
        "base_url": "https://www.garoweonline.com",
        "categories": {
            "siyaasad": "https://www.garoweonline.com/so/category/siyaasad",
            "amni":     "https://www.garoweonline.com/so/category/amni",
            "caalamka": "https://www.garoweonline.com/so/category/caalamka",
        },
        "article_link_sel": "h2 a, h3 a, .article-title a",
        "title_sel":   ["h1", ".article-title"],
        "content_sel": [".article-body p", ".entry-content p", "article p"],
        "pagination": {"type": "path", "pattern": "page/{n}"},
        "delay": 2.0,
        "js_render": False,
    },

    "wariye": {
        "base_url": "https://wariye.com",
        "categories": {
            "siyaasad": "https://wariye.com/category/siyaasad/",
            "amni":     "https://wariye.com/category/amni/",
            "caalamka": "https://wariye.com/category/caalamka/",
        },
        "article_link_sel": "h2.entry-title a, h3.entry-title a",
        "title_sel":   ["h1.entry-title", "h1"],
        "content_sel": [".entry-content p"],
        "pagination": {"type": "path", "pattern": "page/{n}/"},
        "delay": 2.0,
        "js_render": False,
    },

    "dalsoor": {
        "base_url": "https://dalsoor.net",
        "categories": {
            "siyaasad": "https://dalsoor.net/category/siyaasad/",
            "amni":     "https://dalsoor.net/category/amni/",
            "caalamka": "https://dalsoor.net/category/caalamka/",
        },
        "article_link_sel": "h2.entry-title a, h3.entry-title a",
        "title_sel":   ["h1.entry-title", "h1"],
        "content_sel": [".entry-content p"],
        "pagination": {"type": "path", "pattern": "page/{n}/"},
        "delay": 2.0,
        "js_render": False,
    },

    "ogaalnews": {
        "base_url": "https://ogaalnews.com",
        "categories": {
            "siyaasad": "https://ogaalnews.com/category/siyaasad/",
            "amni":     "https://ogaalnews.com/category/amni/",
            "caalamka": "https://ogaalnews.com/category/caalamka/",
        },
        "article_link_sel": "h2.entry-title a, h3.entry-title a",
        "title_sel":   ["h1.entry-title", "h1"],
        "content_sel": [".entry-content p"],
        "pagination": {"type": "path", "pattern": "page/{n}/"},
        "delay": 2.0,
        "js_render": False,
    },

    "jowhar": {
        "base_url": "https://jowhar.com",
        "categories": {
            "siyaasad": "https://jowhar.com/category/siyaasad/",
            "amni":     "https://jowhar.com/category/amni/",
            "caalamka": "https://jowhar.com/category/caalamka/",
        },
        "article_link_sel": "h2.entry-title a, h3.entry-title a",
        "title_sel":   ["h1.entry-title", "h1"],
        "content_sel": [".entry-content p"],
        "pagination": {"type": "path", "pattern": "page/{n}/"},
        "delay": 2.0,
        "js_render": False,
    },

    "wardheernews": {
        "base_url": "https://wardheernews.com",
        "categories": {
            "siyaasad": "https://wardheernews.com/category/politics/",
            "amni":     "https://wardheernews.com/category/security/",
            "caalamka": "https://wardheernews.com/category/world/",
        },
        "article_link_sel": "h2.entry-title a, h3.entry-title a",
        "title_sel":   ["h1.entry-title", "h1"],
        "content_sel": [".entry-content p"],
        "pagination": {"type": "path", "pattern": "page/{n}/"},
        "delay": 2.0,
        "js_render": False,
    },

    # ── TIER 3 ────────────────────────────────────────────────────────────────

    "puntlandpost": {
        "base_url": "https://puntlandpost.net",
        "categories": {
            "siyaasad": "https://puntlandpost.net/category/siyaasad/",
            "amni":     "https://puntlandpost.net/category/amni/",
            "caalamka": "https://puntlandpost.net/category/caalamka/",
        },
        "article_link_sel": "h2.entry-title a, h3.entry-title a",
        "title_sel":   ["h1.entry-title", "h1"],
        "content_sel": [".entry-content p"],
        "pagination": {"type": "path", "pattern": "page/{n}/"},
        "delay": 2.5,
        "js_render": False,
    },

    "haatuf": {
        "base_url": "https://haatuf.net",
        "categories": {
            "siyaasad": "https://haatuf.net/category/siyaasad/",
            "amni":     "https://haatuf.net/category/amni/",
            "caalamka": "https://haatuf.net/category/caalamka/",
        },
        "article_link_sel": "h2.entry-title a, h3.entry-title a",
        "title_sel":   ["h1.entry-title", "h1"],
        "content_sel": [".entry-content p"],
        "pagination": {"type": "path", "pattern": "page/{n}/"},
        "delay": 2.5,
        "js_render": False,
    },

    "jubbaonline": {
        "base_url": "https://jubbaonline.com",
        "categories": {
            "siyaasad": "https://jubbaonline.com/category/siyaasad/",
            "amni":     "https://jubbaonline.com/category/amni/",
            "caalamka": "https://jubbaonline.com/category/caalamka/",
        },
        "article_link_sel": "h2.entry-title a, h3.entry-title a",
        "title_sel":   ["h1.entry-title", "h1"],
        "content_sel": [".entry-content p"],
        "pagination": {"type": "path", "pattern": "page/{n}/"},
        "delay": 2.5,
        "js_render": False,
    },
}

# ─── Scraper behaviour ────────────────────────────────────────────────────────
SCRAPER_CONFIG = {
    "max_pages_per_category": 500,   # max listing pages to paginate through
    "max_articles_per_category": 12000,  # stop early if exceeded
    "target_per_category": 10000,
    "request_timeout": 20,           # seconds
    "max_retries": 4,
    "backoff_factor": 2.0,           # exponential backoff multiplier
    "checkpoint_every": 100,         # save progress every N articles
    "min_title_length": 10,          # discard very short titles
    "min_content_length": 50,        # discard stubs
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/124.0.0.0 Safari/537.36",
]
