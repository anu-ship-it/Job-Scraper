"""
scrapers/job_scrapers.py
Scrapes job listings from LinkedIn, Indeed, Naukri (no login required).
Uses rotating headers to avoid blocks. Returns normalized job dicts.
"""

import time
import random
import requests
from bs4 import BeautifulSoup
from typing import List, Dict


HEADERS_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    },
]


def _get(url: str, timeout: int = 15) -> requests.Response | None:
    headers = random.choice(HEADERS_POOL)
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"[Scraper] GET failed {url}: {e}")
        return None


def _sleep():
    time.sleep(random.uniform(1.5, 3.5))


# ─── LinkedIn ─────────────────────────────────────────────────────────────────

def scrape_linkedin(query: str, location: str = "India", max_jobs: int = 20) -> List[Dict]:
    """Scrape LinkedIn public job listings (no auth)."""
    jobs = []
    page = 0
    while len(jobs) < max_jobs:
        url = (
            f"https://www.linkedin.com/jobs/search?"
            f"keywords={requests.utils.quote(query)}"
            f"&location={requests.utils.quote(location)}"
            f"&start={page * 25}&position=1&pageNum=0"
        )
        resp = _get(url)
        if not resp:
            break

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.find_all("div", class_="base-card")
        if not cards:
            break

        for card in cards:
            try:
                title_el = card.find("h3", class_="base-search-card__title")
                company_el = card.find("h4", class_="base-search-card__subtitle")
                location_el = card.find("span", class_="job-search-card__location")
                link_el = card.find("a", class_="base-card__full-link")
                date_el = card.find("time")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                loc = location_el.get_text(strip=True) if location_el else ""
                url_job = link_el["href"].split("?")[0] if link_el else ""
                posted = date_el.get("datetime", "") if date_el else ""

                if title:
                    jobs.append({
                        "source": "linkedin",
                        "title": title,
                        "company": company,
                        "location": loc,
                        "url": url_job,
                        "posted_date": posted,
                        "description": "",
                    })
            except Exception:
                continue

        page += 1
        _sleep()
        if len(cards) < 10:
            break

    return jobs[:max_jobs]


# ─── Indeed ───────────────────────────────────────────────────────────────────

def scrape_indeed(query: str, location: str = "India", max_jobs: int = 20) -> List[Dict]:
    """Scrape Indeed job listings."""
    jobs = []
    start = 0
    while len(jobs) < max_jobs:
        url = (
            f"https://in.indeed.com/jobs?"
            f"q={requests.utils.quote(query)}"
            f"&l={requests.utils.quote(location)}"
            f"&start={start}&fromage=14"  # last 14 days
        )
        resp = _get(url)
        if not resp:
            break

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.find_all("div", class_="job_seen_beacon")
        if not cards:
            break

        for card in cards:
            try:
                title_el = card.find("h2", class_="jobTitle")
                company_el = card.find("span", attrs={"data-testid": "company-name"})
                location_el = card.find("div", attrs={"data-testid": "text-location"})
                link_el = title_el.find("a") if title_el else None
                date_el = card.find("span", attrs={"data-testid": "myJobsStateDate"})

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                loc = location_el.get_text(strip=True) if location_el else ""
                href = link_el["href"] if link_el else ""
                url_job = f"https://in.indeed.com{href}" if href.startswith("/") else href
                posted = date_el.get_text(strip=True) if date_el else ""

                if title:
                    jobs.append({
                        "source": "indeed",
                        "title": title,
                        "company": company,
                        "location": loc,
                        "url": url_job,
                        "posted_date": posted,
                        "description": "",
                    })
            except Exception:
                continue

        start += 10
        _sleep()
        if len(cards) < 5:
            break

    return jobs[:max_jobs]


# ─── Naukri ───────────────────────────────────────────────────────────────────

def scrape_naukri(query: str, location: str = "", max_jobs: int = 20) -> List[Dict]:
    """Scrape Naukri job listings (India-focused)."""
    jobs = []
    q = query.lower().replace(" ", "-")
    loc = location.lower().replace(" ", "-") if location else ""
    page = 1

    while len(jobs) < max_jobs:
        url = f"https://www.naukri.com/{q}-jobs" + (f"-in-{loc}" if loc else "") + f"?pageNo={page}"
        resp = _get(url)
        if not resp:
            break

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.find_all("article", class_="jobTuple")
        if not cards:
            # Try newer class name
            cards = soup.find_all("div", class_="srp-jobtuple-wrapper")

        for card in cards:
            try:
                title_el = card.find("a", class_="title")
                company_el = card.find("a", class_="subTitle")
                location_el = card.find("li", class_="location")
                posted_el = card.find("span", class_="fleft job-post-day")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                loc_text = location_el.get_text(strip=True) if location_el else ""
                url_job = title_el["href"] if title_el else ""
                posted = posted_el.get_text(strip=True) if posted_el else ""

                if title:
                    jobs.append({
                        "source": "naukri",
                        "title": title,
                        "company": company,
                        "location": loc_text,
                        "url": url_job,
                        "posted_date": posted,
                        "description": "",
                    })
            except Exception:
                continue

        page += 1
        _sleep()
        if len(cards) < 5:
            break

    return jobs[:max_jobs]


# ─── Job Detail Fetcher ────────────────────────────────────────────────────────

def fetch_job_description(job: Dict) -> str:
    """Fetch and extract the full job description from the job URL."""
    if not job.get("url"):
        return ""

    resp = _get(job["url"])
    if not resp:
        return ""

    soup = BeautifulSoup(resp.text, "lxml")

    # Try common JD selectors
    selectors = [
        ("div", "show-more-less-html__markup"),          # LinkedIn
        ("div", "jobsearch-jobDescriptionText"),         # Indeed
        ("div", "job-desc"),                             # Naukri
        ("section", "description"),
        ("div", "description"),
    ]

    for tag, cls in selectors:
        el = soup.find(tag, class_=cls)
        if el:
            text = el.get_text(separator="\n", strip=True)
            if len(text) > 100:
                return text[:5000]

    # Fallback: grab largest text block
    paragraphs = soup.find_all(["p", "li"])
    text = "\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)
    return text[:5000]


# ─── Main scrape orchestrator ─────────────────────────────────────────────────

def scrape_all(
    suggested_roles: list,
    location: str = "India",
    max_per_role: int = 5,
    sources: list = None,
) -> List[Dict]:
    """
    Scrape all configured sources for given roles.
    Deduplicates by (title, company).
    """
    if sources is None:
        sources = ["linkedin", "indeed", "naukri"]

    all_jobs = []
    seen = set()

    for role in suggested_roles[:5]:  # top 5 roles
        print(f"[Scraper] Searching: {role}")
        if "linkedin" in sources:
            jobs = scrape_linkedin(role, location, max_per_role)
            all_jobs.extend(jobs)
        if "indeed" in sources:
            jobs = scrape_indeed(role, location, max_per_role)
            all_jobs.extend(jobs)
        if "naukri" in sources:
            jobs = scrape_naukri(role, location, max_per_role)
            all_jobs.extend(jobs)
        _sleep()

    # Deduplicate
    deduped = []
    for j in all_jobs:
        key = (j["title"].lower().strip(), j["company"].lower().strip())
        if key not in seen and j["title"]:
            seen.add(key)
            deduped.append(j)

    print(f"[Scraper] Total unique jobs found: {len(deduped)}")
    return deduped