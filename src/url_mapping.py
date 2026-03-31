"""
Maps Buffett file stems to CNBC Archive URLs and document metadata.
Handles standard sessions, COVID-era parts, and non-standard letter filenames.
"""
import re
from typing import Optional

# Annual meeting dates (year -> (month, day))
MEETING_DATES = {
    1994: ("04", "25"), 1995: ("05", "01"), 1996: ("05", "06"),
    1997: ("05", "05"), 1998: ("05", "04"), 1999: ("05", "03"),
    2000: ("05", "01"), 2001: ("04", "30"), 2002: ("05", "06"),
    2003: ("05", "05"), 2004: ("05", "03"), 2005: ("04", "30"),
    2006: ("05", "06"), 2007: ("05", "05"), 2008: ("05", "03"),
    2009: ("05", "02"), 2010: ("05", "01"), 2011: ("04", "30"),
    2012: ("05", "05"), 2013: ("05", "04"), 2014: ("05", "03"),
    2015: ("05", "02"), 2016: ("04", "30"), 2017: ("05", "06"),
    2018: ("05", "05"), 2019: ("05", "04"), 2022: ("04", "30"),
    2023: ("05", "06"), 2024: ("05", "04"),
}

# Special COVID-era and other non-standard URLs
SPECIAL_URLS = {
    (2020, "Part_1"): "https://buffett.cnbc.com/video/2020/05/04/berkshire-hathaway-annual-meeting--may-02-2020.html",
    (2020, "Part_2"): "https://buffett.cnbc.com/video/2020/05/04/berkshire-hathaway-annual-meeting-qa---may-02-2020.html",
    (2021, "Part_1"): "https://buffett.cnbc.com/2021-berkshire-hathaway-annual-meeting/",
    (2021, "Part_2"): "https://buffett.cnbc.com/2021-berkshire-hathaway-annual-meeting/",
}


def get_cnbc_url(stem: str) -> Optional[str]:
    """Return CNBC URL for meeting transcripts; None for letters/reports."""
    # Part format (2020, 2021 COVID era) — match Part_N prefix, ignore trailing suffixes
    m = re.match(r"Buffett_(\d{4})_(Part_\d+)", stem, re.IGNORECASE)
    if m:
        year, part = int(m.group(1)), m.group(2)
        return SPECIAL_URLS.get((year, part))

    # Standard Morning / Afternoon session
    m = re.match(r"Buffett_(\d{4})_(Morning|Afternoon)_Session", stem, re.IGNORECASE)
    if m:
        year, session = int(m.group(1)), m.group(2).lower()
        if year in MEETING_DATES:
            month, day = MEETING_DATES[year]
            return (
                f"https://buffett.cnbc.com/video/{year}/{month}/{day}/"
                f"{session}-session---{year}-meeting.html"
            )
    return None


def identify_file_info(stem: str) -> dict:
    """
    Parse a file stem into metadata.
    Returns: doc_type, year, source_label, cnbc_url (optional)
    """
    # ── Standard Morning / Afternoon Session ──────────────────────────────
    m = re.match(r"Buffett_(\d{4})_(Morning|Afternoon)_Session", stem, re.IGNORECASE)
    if m:
        year, session = int(m.group(1)), m.group(2)
        return {
            "doc_type": "meeting_transcript",
            "year": year,
            "source_label": f"{year}年股东大会 {session} Session",
            "cnbc_url": get_cnbc_url(stem),
        }

    # ── COVID Part format ─────────────────────────────────────────────────
    m = re.match(r"Buffett_(\d{4})_(Part_\d+)", stem, re.IGNORECASE)
    if m:
        year, part = int(m.group(1)), m.group(2)
        return {
            "doc_type": "meeting_transcript",
            "year": year,
            "source_label": f"{year}年股东大会 {part}",
            "cnbc_url": get_cnbc_url(stem),
        }

    s = stem.lower()

    # ── Berkshire 2025 annual meeting transcript (PDF) ────────────────────
    if "2025" in stem and ("annual" in s or "shareholder" in s):
        return {
            "doc_type": "meeting_transcript",
            "year": 2025,
            "source_label": "2025年伯克希尔股东大会文字稿",
        }

    # ── Year-prefixed Munger archive files (e.g. 1994-lecture-by-charlie-munger-...) ──
    m_year = re.match(r"^(\d{4})-(.+)", stem)
    if m_year:
        year = int(m_year.group(1))
        rest = m_year.group(2)  # everything after "YYYY-"
        return {
            "doc_type": "meeting_transcript" if ("wesco" in s or "daily-journal" in s or "annual-meeting" in s) else "speech",
            "year": year,
            "source_label": _munger_label(s, year),
        }

    # ── Munger Daily Journal transcript (long filename from cleaned/PDFs) ─
    if "charlie munger" in s and "daily journal" in s:
        m = re.search(r"(\d{4})", stem)
        year = int(m.group(1)) if m else 2023
        return {
            "doc_type": "meeting_transcript",
            "year": year,
            "source_label": f"{year}年 芒格 Daily Journal 年会演讲",
        }

    # ── Poor Charlie's Almanack ───────────────────────────────────────────
    if "charlie" in s and "almanack" in s:
        return {
            "doc_type": "book",
            "year": 2005,
            "source_label": "穷查理宝典 (Poor Charlie's Almanack)",
        }

    # ── WEB / CTM Past Present Future ────────────────────────────────────
    if "past present future" in s:
        who = "芒格" if stem.upper().startswith("CTM") else "巴菲特"
        m = re.search(r"(\d{4})", stem)
        year = int(m.group(1)) if m else 2014
        return {
            "doc_type": "book",
            "year": year,
            "source_label": f"{who} 过去·现在·未来 ({year})",
        }

    # ── Shareholder letter: non-standard names (e.g. 2003ltr.pdf, 2000pdf.pdf) ──
    m = re.search(r"(19\d{2}|20[0-2]\d)", stem)
    year = int(m.group(1)) if m else 0
    return {
        "doc_type": "shareholder_letter",
        "year": year,
        "source_label": f"{year}年 巴菲特致股东信" if year else stem,
    }


def _munger_label(s: str, year: int) -> str:
    """Generate a human-readable Chinese label from a Munger filename (lowercased)."""
    if "wesco" in s:
        return f"{year}年 Wesco年会 芒格发言"
    if "daily-journal" in s or "daily_journal" in s:
        if "fireside" in s:
            return f"{year}年 Daily Journal年会后 芒格炉边谈话"
        return f"{year}年 Daily Journal年会 芒格发言"
    if "elementary-worldly-wisdom" in s or "worldly-wisdom" in s:
        return f"{year}年 芒格演讲：初级世俗智慧 (USC)"
    if "psychology-of-human-misjudgment" in s or "misjudgment" in s:
        return f"{year}年 芒格演讲：人类误判心理学 (Harvard)"
    if "academic-economics" in s:
        return f"{year}年 芒格演讲：学术经济学批判 (UCSB)"
    if "commencement" in s and "harvard" in s:
        return f"{year}年 芒格哈佛毕业典礼演讲"
    if "commencement" in s and "usc" in s:
        return f"{year}年 芒格USC毕业典礼演讲"
    if "commencement" in s:
        return f"{year}年 芒格毕业典礼演讲"
    if "conversation" in s or "fireside" in s:
        return f"{year}年 芒格对话访谈"
    if "speech" in s or "lecture" in s:
        return f"{year}年 芒格演讲"
    return f"{year}年 芒格发言"
