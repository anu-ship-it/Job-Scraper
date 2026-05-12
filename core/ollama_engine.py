"""
core/ollama_engine.py
All Ollama LLM interactions: resume analysis, role suggestion, job scoring.
"""

import json
import re
import requests


OLLAMA_BASE = "http://localhost:11434"
DEFAULT_MODEL = "llama3"  # change to mistral, phi3, etc. as desired


def _chat(prompt: str, system: str = "", model: str = DEFAULT_MODEL) -> str:
    """Send a prompt to Ollama and return the text response."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system} if system else None,
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }
    payload["messages"] = [m for m in payload["messages"] if m]

    try:
        r = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except Exception as e:
        return f"[Ollama error: {e}]"


def analyze_resume(raw_text: str) -> dict:
    """
    Extract structured profile from raw resume text.
    Returns: name, skills, experience_years, roles, education, summary
    """
    system = (
        "You are an expert technical recruiter and career coach. "
        "Respond ONLY with valid JSON, no markdown, no explanation."
    )
    prompt = f"""Analyze this resume and extract a structured profile.
Return a JSON object with these keys:
- name (string)
- email (string or null)
- skills (list of strings, max 30)
- experience_years (integer)
- roles_held (list of strings – job titles held)
- suggested_roles (list of 5-8 role titles this person is best suited for)
- education (list of strings)
- summary (2-sentence professional summary)
- seniority_level (one of: junior, mid, senior, lead, principal, manager)

RESUME TEXT:
{raw_text[:4000]}"""

    raw = _chat(prompt, system)

    # Strip markdown fences if model wraps it
    clean = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(clean)
    except Exception:
        return {
            "name": "Unknown",
            "skills": [],
            "experience_years": 0,
            "roles_held": [],
            "suggested_roles": ["Software Engineer"],
            "education": [],
            "summary": raw[:200],
            "seniority_level": "mid",
        }


def score_job_match(resume_profile: dict, job: dict) -> dict:
    """
    Score how well a job matches the resume.
    Returns: score (0-100), matched_skills, missing_skills, verdict, reasoning
    """
    system = (
        "You are an ATS and career matching specialist. "
        "Respond ONLY with valid JSON, no markdown."
    )
    prompt = f"""Score how well this candidate matches this job posting.

CANDIDATE PROFILE:
- Skills: {', '.join(resume_profile.get('skills', [])[:20])}
- Experience: {resume_profile.get('experience_years', 0)} years
- Seniority: {resume_profile.get('seniority_level', 'mid')}
- Roles held: {', '.join(resume_profile.get('roles_held', [])[:5])}
- Education: {', '.join(resume_profile.get('education', [])[:3])}

JOB POSTING:
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Description: {job.get('description', '')[:2000]}

Return JSON with:
- score (integer 0-100)
- matched_skills (list of skills from candidate that match the job)
- missing_skills (list of skills in job that candidate lacks)
- verdict (one of: excellent_fit, good_fit, partial_fit, poor_fit)
- reasoning (2-3 sentences explaining the score)
- apply_priority (one of: urgent, high, medium, low)"""

    raw = _chat(prompt, system)
    clean = re.sub(r"```json|```", "", raw).strip()
    try:
        result = json.loads(clean)
        result["score"] = int(result.get("score", 0))
        return result
    except Exception:
        return {
            "score": 0,
            "matched_skills": [],
            "missing_skills": [],
            "verdict": "error",
            "reasoning": "Scoring failed.",
            "apply_priority": "low",
        }


def check_ollama_status(model: str = DEFAULT_MODEL) -> dict:
    """Check if Ollama is running and model is available."""
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        available = any(model in m for m in models)
        return {"running": True, "models": models, "target_model_available": available}
    except Exception as e:
        return {"running": False, "error": str(e), "models": [], "target_model_available": False}
