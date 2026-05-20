#!/usr/bin/env python3
"""
Auto-regenerate log-table-of-content.html from log/ directory.
Run this after adding a new log file to log/.
Usage: python scripts/update-toc.py
"""
import os, re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
LOG_DIR = REPO_ROOT / "log"
TOC_PATH = REPO_ROOT / "log-table-of-content.html"

# Extract title from HTML
def extract_title(html_path):
    text = html_path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return ""

# Extract first substantial paragraph
def extract_desc(html_path):
    text = html_path.read_text(encoding="utf-8", errors="ignore")
    for p in re.findall(r"<p[^>]*>(.*?)</p>", text, re.IGNORECASE | re.DOTALL):
        p_clean = re.sub(r"<[^>]+>", "", p).strip()
        if len(p_clean) > 20:
            return p_clean[:120] + ("…" if len(p_clean) > 120 else "")
    return ""

# Build entries
entries = []
for f in sorted(LOG_DIR.glob("*.html")):
    name = f.name
    date_str = name[:10] if len(name) >= 10 and name[4] == "-" else ""
    title = extract_title(f) or name
    desc = extract_desc(f)
    entries.append({
        "date": date_str,
        "file": f"log/{name}",
        "name": name,
        "title": title,
        "desc": desc,
    })

# Generate TOC HTML
template = '''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hermes VPS — Log Index</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Noto+Sans+TC:wght@300;400;500;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  font-family: 'Noto Sans TC', sans-serif;
  background: #FFFFFF;
  color: #1C1C1C;
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
}
.page {
  max-width: 720px;
  margin: 0 auto;
  padding: 80px 48px 120px;
}
.top-meta {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: #8A8A8A;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  margin-bottom: 60px;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
h1 {
  font-family: 'Playfair Display', serif;
  font-size: 48px;
  font-weight: 400;
  line-height: 1.15;
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}
.subtitle {
  font-family: 'Playfair Display', serif;
  font-style: italic;
  font-size: 20px;
  font-weight: 400;
  color: #555;
  margin-bottom: 60px;
  line-height: 1.4;
}
.section-divider {
  margin: 48px 0;
  height: 1px;
  background: #E0E0E0;
}
.year-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: #AAA;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 32px;
}
.entry {
  margin-bottom: 40px;
  padding-bottom: 32px;
  border-bottom: 1px solid #F0F0F0;
}
.entry-date {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: #8A8A8A;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}
.entry-title {
  font-family: 'Noto Sans TC', sans-serif;
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 8px;
}
.entry-title a {
  color: #1C1C1C;
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.2s;
}
.entry-title a:hover {
  border-bottom-color: #1C1C1C;
}
.entry-desc {
  font-size: 14px;
  color: #666;
  line-height: 1.7;
  font-weight: 300;
}
.footer-note {
  margin-top: 80px;
  padding-top: 24px;
  border-top: 1px solid #E0E0E0;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  color: #AAA;
  letter-spacing: 0.5px;
  display: flex;
  justify-content: space-between;
}
@media (max-width: 640px) {
  .page { padding: 48px 24px 80px; }
  h1 { font-size: 34px; }
  .subtitle { font-size: 17px; }
}
</style>
</head>
<body>
<div class="page">
  <div class="top-meta">
    <span>Hermes VPS</span>
    <span>Log Index</span>
  </div>
  <h1>Index</h1>
  <p class="subtitle">A record of days, systems, and the space between them.</p>
  <div class="section-divider"></div>
  <div class="year-label">2026</div>
'''

body = ""
for e in entries:
    body += f'''  <div class="entry">
    <div class="entry-date">{e['date']}</div>
    <div class="entry-title"><a href="{e['file']}">{e['name']}</a></div>
    <div class="entry-desc">{e['desc']}</div>
  </div>
'''

footer = '''  <div class="footer-note">
    <span>Hermes VPS · Log Archive</span>
    <span>Auto-generated</span>
  </div>
</div>
</body>
</html>
'''

TOC_PATH.write_text(template + body + footer, encoding="utf-8")
print(f"Updated: {TOC_PATH}")
print(f"Entries: {len(entries)}")
