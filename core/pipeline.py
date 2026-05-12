"""
core/pipeline.py
Full end-to-end pipeline: scrape → describe → score → report
Designed to be called by the scheduler or manually via Flask API.
"""

import time
from datetime import datetime

from core.database import (
    get_latest_resume,
    get_unmatched_jobs,
    save_jobs,
    save_match,
    get_top_matches,
    mark_matches_reported,
    save_report,
    update_job_description,
)
from core.ollama_engine import score_job_match
from scrapers.job_scrapers import scrape_all, fetch_job_description
from reports.report_generator import generate_weekly_report


def run_scrape_phase(location: str = "India", max_per_role: int = 10) -> int:
    """Phase 1: Scrape jobs based on resume's suggested roles."""
    resume = get_latest_resume()
    if not resume:
        print("[Pipeline] No resume found. Upload one first.")
        return 0

    profile = resume["profile"]
    roles = profile.get("suggested_roles", ["Software Engineer"])
    print(f"[Pipeline] Scraping for roles: {roles}")

    jobs = scrape_all(roles, location=location, max_per_role=max_per_role)
    saved = save_jobs(jobs)
    print(f"[Pipeline] Saved {saved} new jobs to DB.")
    return saved


def run_description_phase(limit: int = 50) -> int:
    """Phase 2: Fetch full JDs for jobs without descriptions."""
    resume = get_latest_resume()
    if not resume:
        return 0

    jobs = get_unmatched_jobs(resume["id"], limit=limit)
    fetched = 0
    for job in jobs:
        if not job.get("description") or len(job["description"]) < 100:
            desc = fetch_job_description(job)
            if desc:
                update_job_description(job["id"], desc)
                fetched += 1
            time.sleep(1.5)
    print(f"[Pipeline] Fetched descriptions for {fetched} jobs.")
    return fetched


def run_matching_phase(threshold: int = 80) -> int:
    """Phase 3: Score all unmatched jobs via Ollama."""
    resume = get_latest_resume()
    if not resume:
        return 0

    profile = resume["profile"]
    jobs = get_unmatched_jobs(resume["id"], limit=100)
    if not jobs:
        print("[Pipeline] No new jobs to score.")
        return 0

    print(f"[Pipeline] Scoring {len(jobs)} jobs...")
    scored = 0
    high_matches = 0

    for job in jobs:
        if not job.get("description"):
            # Quick score without full description
            job["description"] = f"{job['title']} at {job['company']}"

        match = score_job_match(profile, job)
        save_match(resume["id"], job["id"], match)
        scored += 1
        if match.get("score", 0) >= threshold:
            high_matches += 1
        print(
            f"  [{scored}/{len(jobs)}] {job['title']} @ {job['company']} → {match.get('score', 0)}%"
        )
        time.sleep(0.5)  # Respect Ollama rate

    print(f"[Pipeline] Scored {scored} jobs. High matches (≥{threshold}%): {high_matches}")
    return high_matches


def run_report_phase(threshold: int = 80) -> str | None:
    """Phase 4: Generate weekly HTML report from top matches."""
    resume = get_latest_resume()
    if not resume:
        return None

    matches = get_top_matches(
        resume["id"],
        threshold=threshold,
        limit=30,
        unreported_only=True,
    )

    if not matches:
        print("[Pipeline] No unreported matches above threshold.")
        # Fallback: show all matches (not just new)
        matches = get_top_matches(resume["id"], threshold=threshold, limit=20)

    if not matches:
        print("[Pipeline] No matches at all. Nothing to report.")
        return None

    html = generate_weekly_report(
        matches,
        resume["profile"],
        week_label=datetime.now().strftime("Week of %B %d, %Y"),
    )

    report_id = save_report(html, len(matches), matches[0]["score"] if matches else 0)
    mark_matches_reported([m["id"] for m in matches if not m.get("reported")])

    print(f"[Pipeline] Report #{report_id} generated with {len(matches)} matches.")
    return html


def run_full_pipeline(
    location: str = "India",
    threshold: int = 80,
    max_per_role: int = 10,
) -> dict:
    """Run the complete pipeline end-to-end."""
    start = time.time()
    print(f"\n{'='*60}")
    print(f"[Pipeline] Starting full run — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    results = {
        "jobs_scraped": 0,
        "descriptions_fetched": 0,
        "high_matches": 0,
        "report_generated": False,
        "duration_seconds": 0,
    }

    results["jobs_scraped"] = run_scrape_phase(location, max_per_role)
    results["descriptions_fetched"] = run_description_phase(limit=results["jobs_scraped"] + 20)
    results["high_matches"] = run_matching_phase(threshold)
    report_html = run_report_phase(threshold)
    results["report_generated"] = report_html is not None

    results["duration_seconds"] = round(time.time() - start, 1)
    print(f"\n[Pipeline] Done in {results['duration_seconds']}s → {results}")
    return results
