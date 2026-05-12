"""
app.py
Flask web application — UI + REST API for the AI Job Scraper.
"""

import os
import json
import threading
from pathlib import Path
from datetime import datetime
from flask import (
    Flask, request, jsonify, render_template_string,
    redirect, url_for, send_from_directory, send_file
)

from core.database import (
    init_db, save_resume, get_latest_resume, get_stats,
    get_top_matches, get_all_reports, get_report_html
)
from core.resume_parser import parse_resume
from core.ollama_engine import analyze_resume, check_ollama_status
from scheduler.scheduler import start_scheduler, get_next_run

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ─── HTML Template ────────────────────────────────────────────────────────────

MAIN_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Job Scraper — Powered by Ollama</title>
<style>
:root {
  --bg: #0f1117;
  --surface: #1a1d2e;
  --surface2: #22263a;
  --border: rgba(255,255,255,0.08);
  --accent: #7c6af7;
  --accent2: #56cfb2;
  --danger: #f05252;
  --warn: #f0a435;
  --text: #e8e8f0;
  --muted: #888aaa;
  --radius: 14px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  min-height: 100vh;
}
.topbar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 16px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
}
.brand {
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.ollama-badge {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 20px;
  background: var(--surface2);
  border: 1px solid var(--border);
}
.ollama-badge.ok { border-color: var(--accent2); color: var(--accent2); }
.ollama-badge.err { border-color: var(--danger); color: var(--danger); }
.container { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
@media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 28px;
}
.card h2 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
}
.upload-zone {
  border: 2px dashed var(--border);
  border-radius: 10px;
  padding: 40px 24px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.upload-zone:hover { border-color: var(--accent); background: rgba(124,106,247,0.05); }
.upload-zone p { color: var(--muted); font-size: 14px; margin-top: 10px; }
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.2s, transform 0.1s;
  text-decoration: none;
}
.btn:active { transform: scale(0.97); }
.btn-primary { background: var(--accent); color: #fff; }
.btn-success { background: var(--accent2); color: #0a2e25; }
.btn-danger { background: var(--danger); color: #fff; }
.btn-ghost {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}
.stat {
  background: var(--surface2);
  border-radius: 10px;
  padding: 18px;
  text-align: center;
  border: 1px solid var(--border);
}
.stat .val { font-size: 28px; font-weight: 700; }
.stat .lbl { font-size: 12px; color: var(--muted); margin-top: 4px; }
.score-bar-wrap { display: flex; align-items: center; gap: 10px; }
.score-bar-bg {
  flex: 1;
  height: 6px;
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
  overflow: hidden;
}
.score-bar-fill { height: 100%; border-radius: 3px; }
.job-card {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 12px;
  position: relative;
}
.job-card:hover { border-color: rgba(124,106,247,0.3); }
.verdict-excellent { border-left: 3px solid var(--accent2); }
.verdict-good { border-left: 3px solid var(--accent); }
.verdict-partial { border-left: 3px solid var(--warn); }
.tag {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  margin: 2px;
}
.tag-green { background: rgba(86,207,178,0.15); color: var(--accent2); }
.tag-red { background: rgba(240,82,82,0.15); color: var(--danger); }
.section-title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.log-box {
  background: #0a0c14;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: var(--accent2);
  height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
}
.tab-bar { display: flex; gap: 4px; margin-bottom: 28px; }
.tab {
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--muted);
  background: transparent;
  border: none;
  transition: all 0.2s;
}
.tab.active { background: var(--surface); color: var(--text); }
.tab-content { display: none; }
.tab-content.active { display: block; }
.profile-pill {
  display: inline-block;
  padding: 5px 14px;
  border-radius: 20px;
  font-size: 13px;
  background: var(--surface2);
  border: 1px solid var(--border);
  margin: 3px;
}
.spinner {
  display: inline-block;
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }
select, input[type=text], input[type=number] {
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  width: 100%;
  margin-bottom: 12px;
}
label { font-size: 13px; color: var(--muted); margin-bottom: 6px; display: block; }
.alert {
  padding: 14px 18px;
  border-radius: 10px;
  font-size: 14px;
  margin-bottom: 16px;
}
.alert-info { background: rgba(124,106,247,0.12); border: 1px solid rgba(124,106,247,0.3); }
.alert-success { background: rgba(86,207,178,0.12); border: 1px solid rgba(86,207,178,0.3); color: var(--accent2); }
.alert-warn { background: rgba(240,164,53,0.12); border: 1px solid rgba(240,164,53,0.3); color: var(--warn); }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
</style>
</head>
<body>

<div class="topbar">
  <div class="brand">⚡ AI Job Scraper</div>
  <div>
    <span id="ollama-status" class="ollama-badge">Checking Ollama...</span>
  </div>
</div>

<div class="container">

  <!-- Tabs -->
  <div class="tab-bar">
    <button class="tab active" onclick="switchTab('dashboard')">Dashboard</button>
    <button class="tab" onclick="switchTab('resume')">Resume</button>
    <button class="tab" onclick="switchTab('matches')">Matches</button>
    <button class="tab" onclick="switchTab('reports')">Reports</button>
    <button class="tab" onclick="switchTab('settings')">Settings</button>
  </div>

  <!-- DASHBOARD TAB -->
  <div id="tab-dashboard" class="tab-content active">
    <div class="stat-grid" id="stats-grid">
      <div class="stat"><div class="val" id="stat-jobs">—</div><div class="lbl">Jobs Scraped</div></div>
      <div class="stat"><div class="val" id="stat-matches">—</div><div class="lbl">Matches Scored</div></div>
      <div class="stat"><div class="val" id="stat-high" style="color:#56cfb2">—</div><div class="lbl">≥80% Matches</div></div>
      <div class="stat"><div class="val" id="stat-avg">—</div><div class="lbl">Avg Score</div></div>
      <div class="stat"><div class="val" id="stat-reports">—</div><div class="lbl">Reports Made</div></div>
    </div>

    <div class="alert alert-info">
      <strong>Next scheduled run:</strong> <span id="next-run">Loading...</span>
    </div>

    <div class="grid-2">
      <div class="card">
        <h2>Quick Actions</h2>
        <div style="display:flex;flex-direction:column;gap:12px;">
          <button class="btn btn-primary" onclick="runPipeline('full')">
            🚀 Run Full Pipeline Now
          </button>
          <button class="btn btn-ghost" onclick="runPipeline('scrape')">
            🔍 Scrape Jobs Only
          </button>
          <button class="btn btn-ghost" onclick="runPipeline('match')">
            🤖 Score Unmatched Jobs
          </button>
          <button class="btn btn-success" onclick="runPipeline('report')">
            📊 Generate Report
          </button>
        </div>
      </div>

      <div class="card">
        <h2>Pipeline Log</h2>
        <div class="log-box" id="pipeline-log">Ready. Click an action above to begin...\n</div>
      </div>
    </div>
  </div>

  <!-- RESUME TAB -->
  <div id="tab-resume" class="tab-content">
    <div class="card" style="margin-bottom:24px">
      <h2>Upload Your Resume</h2>
      <div class="upload-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
        <div style="font-size:40px">📄</div>
        <p>Click to upload or drag & drop</p>
        <p>Supports PDF, DOCX, TXT</p>
      </div>
      <input type="file" id="file-input" accept=".pdf,.docx,.doc,.txt" style="display:none"
             onchange="uploadResume(this)">
      <div id="upload-status" style="margin-top:14px"></div>
    </div>

    <div class="card" id="profile-card" style="display:none">
      <h2>Current Resume Profile</h2>
      <div id="profile-content"></div>
    </div>
  </div>

  <!-- MATCHES TAB -->
  <div id="tab-matches" class="tab-content">
    <div class="section-title">
      🎯 Job Matches
      <span style="font-size:14px;color:var(--muted);font-weight:400">Score ≥ 80%</span>
    </div>
    <div id="matches-list"><p style="color:var(--muted)">Loading matches...</p></div>
  </div>

  <!-- REPORTS TAB -->
  <div id="tab-reports" class="tab-content">
    <div class="section-title">📋 Weekly Reports</div>
    <div id="reports-list"><p style="color:var(--muted)">Loading reports...</p></div>
  </div>

  <!-- SETTINGS TAB -->
  <div id="tab-settings" class="tab-content">
    <div class="card">
      <h2>Configuration</h2>
      <label>Job Search Location</label>
      <input type="text" id="cfg-location" value="India" placeholder="e.g. Bangalore, India">
      <label>Match Score Threshold (%)</label>
      <input type="number" id="cfg-threshold" value="80" min="50" max="100">
      <label>Jobs per Role per Source</label>
      <input type="number" id="cfg-max-per-role" value="10" min="3" max="30">
      <label>Ollama Model</label>
      <input type="text" id="cfg-model" value="llama3" placeholder="llama3, mistral, phi3...">
      <label>Schedule Day</label>
      <select id="cfg-day">
        <option value="sun" selected>Sunday</option>
        <option value="mon">Monday</option>
        <option value="sat">Saturday</option>
      </select>
      <label>Schedule Hour (24h, IST)</label>
      <input type="number" id="cfg-hour" value="8" min="0" max="23">
      <br>
      <button class="btn btn-primary" onclick="saveConfig()">Save Configuration</button>
      <div id="cfg-status" style="margin-top:10px"></div>
    </div>
  </div>

</div>

<script>
// ─── Tab switching
function switchTab(name) {
  document.querySelectorAll('.tab, .tab-content').forEach(el => el.classList.remove('active'));
  document.querySelector(`[onclick="switchTab('${name}')"]`).classList.add('active');
  document.getElementById(`tab-${name}`).classList.add('active');
  if (name === 'matches') loadMatches();
  if (name === 'reports') loadReports();
  if (name === 'resume') loadProfile();
}

// ─── Ollama status
async function checkOllama() {
  const el = document.getElementById('ollama-status');
  try {
    const r = await fetch('/api/ollama-status');
    const d = await r.json();
    if (d.running) {
      el.textContent = d.target_model_available
        ? `✓ Ollama: ${d.models[0] || 'running'}`
        : '⚠ Ollama: model not found';
      el.className = 'ollama-badge ok';
    } else {
      el.textContent = '✗ Ollama offline';
      el.className = 'ollama-badge err';
    }
  } catch { el.textContent = '✗ Ollama offline'; el.className = 'ollama-badge err'; }
}

// ─── Stats
async function loadStats() {
  try {
    const r = await fetch('/api/stats');
    const d = await r.json();
    document.getElementById('stat-jobs').textContent = d.total_jobs;
    document.getElementById('stat-matches').textContent = d.total_matches;
    document.getElementById('stat-high').textContent = d.high_matches;
    document.getElementById('stat-avg').textContent = d.avg_score + '%';
    document.getElementById('stat-reports').textContent = d.total_reports;
    document.getElementById('next-run').textContent = d.next_run || 'Not scheduled';
  } catch (e) {}
}

// ─── Pipeline runner
const pipelineRunning = { v: false };
async function runPipeline(phase) {
  if (pipelineRunning.v) { alert('Pipeline already running!'); return; }
  pipelineRunning.v = true;
  const log = document.getElementById('pipeline-log');

  const threshold = parseInt(document.getElementById('cfg-threshold')?.value || 80);
  const location = document.getElementById('cfg-location')?.value || 'India';
  const maxPerRole = parseInt(document.getElementById('cfg-max-per-role')?.value || 10);

  log.textContent = `[${new Date().toLocaleTimeString()}] Starting ${phase} pipeline...\n`;
  switchTab('dashboard');

  try {
    const r = await fetch(`/api/pipeline/${phase}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ threshold, location, max_per_role: maxPerRole }),
    });
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      log.textContent += decoder.decode(value);
      log.scrollTop = log.scrollHeight;
    }
  } catch (e) {
    log.textContent += `\nError: ${e.message}\n`;
  }

  pipelineRunning.v = false;
  loadStats();
}

// ─── Resume upload
async function uploadResume(input) {
  const file = input.files[0];
  if (!file) return;
  const status = document.getElementById('upload-status');
  status.innerHTML = '<span class="spinner"></span> Uploading and analyzing with Ollama...';

  const fd = new FormData();
  fd.append('resume', file);
  try {
    const r = await fetch('/api/upload-resume', { method: 'POST', body: fd });
    const d = await r.json();
    if (d.success) {
      status.innerHTML = '<div class="alert alert-success">✓ Resume analyzed successfully!</div>';
      loadProfile();
    } else {
      status.innerHTML = `<div class="alert alert-warn">Error: ${d.error}</div>`;
    }
  } catch (e) {
    status.innerHTML = `<div class="alert alert-warn">Upload failed: ${e.message}</div>`;
  }
}

async function loadProfile() {
  try {
    const r = await fetch('/api/resume-profile');
    const d = await r.json();
    if (!d.profile) return;
    const p = d.profile;
    const card = document.getElementById('profile-card');
    const content = document.getElementById('profile-content');
    card.style.display = 'block';

    const skillTags = (p.skills || []).map(s =>
      `<span class="profile-pill">${s}</span>`).join('');
    const roleTags = (p.suggested_roles || []).map(r =>
      `<span class="profile-pill" style="border-color:rgba(124,106,247,0.4);color:#a89ff8">${r}</span>`).join('');

    content.innerHTML = `
      <div style="margin-bottom:16px">
        <div style="font-size:20px;font-weight:700">${p.name || 'Your Name'}</div>
        <div style="color:var(--muted);font-size:14px;margin-top:4px">${p.email || ''}</div>
      </div>
      <p style="font-size:14px;color:var(--muted);margin-bottom:16px;line-height:1.6">${p.summary || ''}</p>
      <div style="margin-bottom:12px">
        <div style="font-size:12px;color:var(--muted);margin-bottom:6px">EXPERIENCE · SENIORITY</div>
        <span class="profile-pill">${p.experience_years || 0} years</span>
        <span class="profile-pill">${p.seniority_level || 'mid'}</span>
      </div>
      <div style="margin-bottom:12px">
        <div style="font-size:12px;color:var(--muted);margin-bottom:6px">SKILLS</div>
        ${skillTags}
      </div>
      <div>
        <div style="font-size:12px;color:var(--muted);margin-bottom:6px">AI-SUGGESTED ROLES</div>
        ${roleTags}
      </div>`;
  } catch (e) {}
}

// ─── Matches
async function loadMatches() {
  const container = document.getElementById('matches-list');
  const threshold = parseInt(document.getElementById('cfg-threshold')?.value || 80);
  try {
    const r = await fetch(`/api/matches?threshold=${threshold}`);
    const matches = await r.json();
    if (!matches.length) {
      container.innerHTML = '<p style="color:var(--muted)">No matches yet. Run the pipeline first.</p>';
      return;
    }

    const verdictClass = { excellent_fit: 'verdict-excellent', good_fit: 'verdict-good',
                           partial_fit: 'verdict-partial', poor_fit: '' };
    container.innerHTML = matches.map((m, i) => {
      const scoreColor = m.score >= 80 ? '#56cfb2' : m.score >= 60 ? '#f0a435' : '#f05252';
      const matchedTags = (m.matched_skills || []).slice(0,8)
        .map(s => `<span class="tag tag-green">${s}</span>`).join('');
      const missingTags = (m.missing_skills || []).slice(0,5)
        .map(s => `<span class="tag tag-red">${s}</span>`).join('');

      return `<div class="job-card ${verdictClass[m.verdict] || ''}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
          <div>
            <div style="font-size:11px;color:var(--muted);text-transform:uppercase;
                        letter-spacing:0.8px">#${i+1} · ${m.source}</div>
            <div style="font-size:17px;font-weight:600;margin:6px 0 3px">${m.title}</div>
            <div style="font-size:14px;color:var(--muted)">${m.company} · ${m.location}</div>
          </div>
          <div style="text-align:right;min-width:60px">
            <div style="font-size:26px;font-weight:700;color:${scoreColor}">${m.score}%</div>
          </div>
        </div>
        <div class="score-bar-wrap" style="margin:12px 0">
          <div class="score-bar-bg">
            <div class="score-bar-fill" style="width:${m.score}%;background:${scoreColor}"></div>
          </div>
        </div>
        <p style="font-size:13px;color:var(--muted);margin-bottom:10px;line-height:1.5">${m.reasoning || ''}</p>
        ${matchedTags ? `<div style="margin-bottom:6px">${matchedTags}</div>` : ''}
        ${missingTags ? `<div>${missingTags}</div>` : ''}
        <div style="margin-top:14px">
          <a href="${m.url}" target="_blank" class="btn btn-ghost" style="padding:8px 16px;font-size:13px">
            View Job →
          </a>
          <span style="margin-left:12px;font-size:12px;color:var(--muted)">${m.posted_date || ''}</span>
        </div>
      </div>`;
    }).join('');
  } catch (e) {
    container.innerHTML = `<p style="color:var(--muted)">Error loading matches: ${e.message}</p>`;
  }
}

// ─── Reports
async function loadReports() {
  const container = document.getElementById('reports-list');
  try {
    const r = await fetch('/api/reports');
    const reports = await r.json();
    if (!reports.length) {
      container.innerHTML = '<p style="color:var(--muted)">No reports generated yet.</p>';
      return;
    }
    container.innerHTML = reports.map(r => `
      <div class="job-card" style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <div style="font-size:16px;font-weight:600">Report #${r.id}</div>
          <div style="font-size:13px;color:var(--muted);margin-top:4px">
            ${r.created_at} · ${r.match_count} matches · Top score: ${r.top_score}%
          </div>
        </div>
        <a href="/report/${r.id}" target="_blank" class="btn btn-ghost"
           style="padding:8px 18px;font-size:13px">View →</a>
      </div>`).join('');
  } catch (e) {}
}

// ─── Settings
async function saveConfig() {
  const el = document.getElementById('cfg-status');
  el.innerHTML = '<span class="spinner"></span>';
  try {
    const r = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        location: document.getElementById('cfg-location').value,
        threshold: parseInt(document.getElementById('cfg-threshold').value),
        max_per_role: parseInt(document.getElementById('cfg-max-per-role').value),
        model: document.getElementById('cfg-model').value,
        schedule_day: document.getElementById('cfg-day').value,
        schedule_hour: parseInt(document.getElementById('cfg-hour').value),
      }),
    });
    const d = await r.json();
    el.innerHTML = `<div class="alert alert-success">✓ ${d.message}</div>`;
    loadStats();
  } catch (e) {
    el.innerHTML = `<div class="alert alert-warn">Error: ${e.message}</div>`;
  }
}

// Drag & drop
const dz = document.getElementById('drop-zone');
dz.addEventListener('dragover', e => { e.preventDefault(); dz.style.borderColor='var(--accent)'; });
dz.addEventListener('dragleave', () => { dz.style.borderColor=''; });
dz.addEventListener('drop', e => {
  e.preventDefault();
  dz.style.borderColor='';
  const file = e.dataTransfer.files[0];
  if (file) {
    const fi = document.getElementById('file-input');
    const dt = new DataTransfer();
    dt.items.add(file);
    fi.files = dt.files;
    uploadResume(fi);
  }
});

// Init
checkOllama();
loadStats();
setInterval(checkOllama, 30000);
setInterval(loadStats, 15000);
</script>
</body>
</html>"""


# ─── Flask Routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(MAIN_TEMPLATE)


@app.route("/api/ollama-status")
def api_ollama_status():
    status = check_ollama_status()
    return jsonify(status)


@app.route("/api/stats")
def api_stats():
    stats = get_stats()
    stats["next_run"] = get_next_run()
    return jsonify(stats)


@app.route("/api/upload-resume", methods=["POST"])
def api_upload_resume():
    if "resume" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"})

    f = request.files["resume"]
    if not f.filename:
        return jsonify({"success": False, "error": "Empty filename"})

    save_path = os.path.join(app.config["UPLOAD_FOLDER"], f.filename)
    f.save(save_path)

    try:
        parsed = parse_resume(save_path)
        raw_text = parsed["raw_text"]
        if not raw_text or len(raw_text) < 50:
            return jsonify({"success": False, "error": "Could not extract text from file"})

        profile = analyze_resume(raw_text)
        resume_id = save_resume(save_path, raw_text, profile)
        return jsonify({"success": True, "resume_id": resume_id, "profile": profile})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/resume-profile")
def api_resume_profile():
    resume = get_latest_resume()
    if not resume:
        return jsonify({"profile": None})
    return jsonify({"profile": resume["profile"]})


@app.route("/api/pipeline/<phase>", methods=["POST"])
def api_pipeline(phase):
    """Streaming pipeline endpoint."""
    from flask import Response
    import sys

    data = request.get_json(silent=True) or {}
    location = data.get("location", "India")
    threshold = int(data.get("threshold", 80))
    max_per_role = int(data.get("max_per_role", 10))

    def generate():
        import io
        from contextlib import redirect_stdout

        from core.pipeline import (
            run_scrape_phase, run_description_phase,
            run_matching_phase, run_report_phase, run_full_pipeline
        )

        buffer = io.StringIO()
        try:
            if phase == "full":
                result = run_full_pipeline(location, threshold, max_per_role)
                yield f"Pipeline complete!\n{json.dumps(result, indent=2)}\n"
            elif phase == "scrape":
                n = run_scrape_phase(location, max_per_role)
                yield f"Scraped {n} new jobs.\n"
            elif phase == "match":
                n = run_matching_phase(threshold)
                yield f"Scored jobs. High matches (≥{threshold}%): {n}\n"
            elif phase == "report":
                html = run_report_phase(threshold)
                yield f"Report generated: {bool(html)}\n"
                if html:
                    yield "→ Go to Reports tab to view.\n"
            else:
                yield f"Unknown phase: {phase}\n"
        except Exception as e:
            yield f"Error: {e}\n"

    return Response(generate(), mimetype="text/plain")


@app.route("/api/matches")
def api_matches():
    resume = get_latest_resume()
    if not resume:
        return jsonify([])
    threshold = int(request.args.get("threshold", 80))
    matches = get_top_matches(resume["id"], threshold=threshold, limit=50)
    return jsonify(matches)


@app.route("/api/reports")
def api_reports():
    return jsonify(get_all_reports())


@app.route("/report/<int:report_id>")
def view_report(report_id):
    html = get_report_html(report_id)
    if not html:
        return "Report not found", 404
    return html


@app.route("/api/config", methods=["POST"])
def api_config():
    from scheduler.scheduler import start_scheduler
    data = request.get_json()
    # Re-start scheduler with new params
    start_scheduler(
        hour=data.get("schedule_hour", 8),
        day_of_week=data.get("schedule_day", "sun")
    )
    # Update Ollama model env var
    os.environ["OLLAMA_MODEL"] = data.get("model", "llama3")
    return jsonify({"message": "Configuration saved. Scheduler updated."})


# ─── Startup ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    start_scheduler()
    print("\n" + "="*60)
    print("  AI Job Scraper — Powered by Ollama")
    print("  Open: http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
