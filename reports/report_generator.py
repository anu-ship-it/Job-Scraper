"""
reports/report_generator.py
Generates a beautiful weekly HTML report of top job matches.
"""

from datetime import datetime


PRIORITY_COLOR = {
    "urgent": "#D85A30",
    "high": "#BA7517",
    "medium": "#185FA5",
    "low": "#5F5E5A",
}

VERDICT_LABEL = {
    "excellent_fit": ("★★★ Excellent Fit", "#1D9E75"),
    "good_fit": ("★★ Good Fit", "#185FA5"),
    "partial_fit": ("★ Partial Fit", "#BA7517"),
    "poor_fit": ("Poor Fit", "#888780"),
    "error": ("Unknown", "#888780"),
}

PRIORITY_LABEL = {
    "urgent": "🔴 Apply Now",
    "high": "🟡 High Priority",
    "medium": "🔵 Worth Considering",
    "low": "⚪ Low Priority",
}


def _score_bar(score: int) -> str:
    color = "#1D9E75" if score >= 80 else "#BA7517" if score >= 60 else "#D85A30"
    return f"""
    <div style="display:flex;align-items:center;gap:10px;margin:8px 0;">
      <div style="flex:1;height:8px;background:#e8e8e8;border-radius:4px;overflow:hidden;">
        <div style="width:{score}%;height:100%;background:{color};border-radius:4px;
                    transition:width 0.6s ease;"></div>
      </div>
      <span style="font-size:14px;font-weight:600;color:{color};min-width:38px">{score}%</span>
    </div>"""


def _skill_tags(skills: list, color: str, bg: str) -> str:
    if not skills:
        return ""
    tags = "".join(
        f'<span style="display:inline-block;padding:3px 10px;margin:3px 4px 3px 0;'
        f'background:{bg};color:{color};border-radius:20px;font-size:12px;">{s}</span>'
        for s in skills[:12]
    )
    return tags


def generate_weekly_report(matches: list, profile: dict, week_label: str = None) -> str:
    if not week_label:
        week_label = datetime.now().strftime("Week of %B %d, %Y")

    name = profile.get("name", "Candidate")
    summary = profile.get("summary", "")
    suggested_roles = profile.get("suggested_roles", [])

    cards_html = ""
    for i, m in enumerate(matches, 1):
        verdict_text, verdict_color = VERDICT_LABEL.get(
            m.get("verdict", "error"), ("Unknown", "#888780")
        )
        priority_text = PRIORITY_LABEL.get(m.get("apply_priority", "low"), "")
        matched = _skill_tags(m.get("matched_skills", []), "#085041", "#E1F5EE")
        missing = _skill_tags(m.get("missing_skills", []), "#4A1B0C", "#FAECE7")

        cards_html += f"""
        <div style="background:#fff;border-radius:16px;padding:28px;margin-bottom:20px;
                    box-shadow:0 2px 12px rgba(0,0,0,0.07);border-left:4px solid {verdict_color};">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
            <div>
              <span style="font-size:12px;font-weight:600;color:#888;text-transform:uppercase;
                           letter-spacing:1px;">#{i} &nbsp;|&nbsp; {m.get('source','').upper()}</span>
              <h3 style="margin:6px 0 4px;font-size:20px;color:#1a1a1a;">{m.get('title','')}</h3>
              <p style="margin:0;font-size:15px;color:#555;">
                {m.get('company','')} &nbsp;•&nbsp; {m.get('location','')}
              </p>
            </div>
            <div style="text-align:right;">
              <div style="font-size:13px;font-weight:600;color:{verdict_color};">{verdict_text}</div>
              <div style="font-size:12px;color:#888;margin-top:4px;">{priority_text}</div>
            </div>
          </div>

          {_score_bar(m.get('score', 0))}

          <p style="font-size:14px;color:#444;margin:12px 0 8px;line-height:1.6;">
            {m.get('reasoning','')}</p>

          {'<div style="margin:12px 0 4px"><span style="font-size:12px;font-weight:600;color:#085041;">✓ Matched Skills</span><br>' + matched + '</div>' if matched else ''}
          {'<div style="margin:8px 0 4px"><span style="font-size:12px;font-weight:600;color:#993C1D;">⚠ Skill Gaps</span><br>' + missing + '</div>' if missing else ''}

          <div style="margin-top:16px;">
            <a href="{m.get('url','#')}" target="_blank"
               style="display:inline-block;padding:10px 24px;background:#1a1a2e;color:#fff;
                      text-decoration:none;border-radius:8px;font-size:14px;font-weight:500;">
              View & Apply →
            </a>
            <span style="margin-left:12px;font-size:12px;color:#aaa;">
              Posted: {m.get('posted_date','N/A')}
            </span>
          </div>
        </div>"""

    roles_html = "".join(
        f'<span style="display:inline-block;padding:5px 14px;margin:4px;background:#f0f0f0;'
        f'border-radius:20px;font-size:13px;color:#333;">{r}</span>'
        for r in suggested_roles[:6]
    )

    stats_html = f"""
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px;
                margin:24px 0;">
      <div style="background:#E1F5EE;border-radius:12px;padding:20px;text-align:center;">
        <div style="font-size:32px;font-weight:700;color:#085041;">{len(matches)}</div>
        <div style="font-size:13px;color:#0F6E56;">Jobs ≥ 80%</div>
      </div>
      <div style="background:#E6F1FB;border-radius:12px;padding:20px;text-align:center;">
        <div style="font-size:32px;font-weight:700;color:#042C53;">
          {matches[0]['score'] if matches else 0}%
        </div>
        <div style="font-size:13px;color:#185FA5;">Top Score</div>
      </div>
      <div style="background:#FAEEDA;border-radius:12px;padding:20px;text-align:center;">
        <div style="font-size:32px;font-weight:700;color:#412402;">
          {round(sum(m['score'] for m in matches)/len(matches)) if matches else 0}%
        </div>
        <div style="font-size:13px;color:#854F0B;">Avg Score</div>
      </div>
    </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Match Report — {week_label}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f4f6f9;
    color: #1a1a1a;
    padding: 24px;
  }}
  @media print {{
    body {{ background: #fff; padding: 0; }}
  }}
</style>
</head>
<body>
<div style="max-width:800px;margin:0 auto;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 60%,#0f3460 100%);
              border-radius:20px;padding:40px;margin-bottom:24px;color:#fff;">
    <div style="font-size:13px;opacity:0.7;letter-spacing:1px;text-transform:uppercase;">
      AI Job Match Report
    </div>
    <h1 style="font-size:28px;margin:10px 0 6px;">{week_label}</h1>
    <p style="font-size:16px;opacity:0.85;">Personalized for <strong>{name}</strong></p>
    <p style="font-size:14px;opacity:0.65;margin-top:8px;line-height:1.5;">{summary}</p>
    <div style="margin-top:20px;">
      <div style="font-size:12px;opacity:0.6;margin-bottom:8px;">AI-Suggested Roles for You:</div>
      {roles_html}
    </div>
  </div>

  <!-- Stats -->
  {stats_html}

  <!-- Job Cards -->
  <h2 style="font-size:18px;margin:8px 0 16px;color:#333;">
    Your Top Matches This Week
  </h2>
  {cards_html if cards_html else '<p style="color:#888;text-align:center;padding:40px;">No matches above threshold this week. Try uploading an updated resume.</p>'}

  <!-- Footer -->
  <div style="text-align:center;padding:32px 0;color:#aaa;font-size:13px;">
    Generated by your local AI Job Scraper • Powered by Ollama<br>
    Runs every Sunday at 8:00 AM
  </div>
</div>
</body>
</html>"""

    return html
