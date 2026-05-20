#!/usr/bin/env python3
"""
deploy-to-github.py — Deploy HTML files to Hermes_VPS and auto-update TOC + index.

Usage:
    python3 deploy-to-github.py <category> <local_file> [description]

Categories: log, guide, artwork
Example:
    python3 deploy-to-github.py artwork /path/to/my-art.html "A poetic fragment"

What it does:
    1. Uploads the file to GitHub: <category>/YYYY-MM-DD_slug.html
    2. Updates the category TOC page
    3. Updates index.html entry counts and date ranges
"""

import base64
import json
import os
import re
import sys
import urllib.request
import urllib.error

# ── Configuration ──
ENV_PATH = '/opt/data/.env'
OWNER = 'tw-riviera'
REPO = 'Hermes_VPS'

# ── Read token ──
TOKEN = None
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, 'r') as f:
        for line in f:
            if line.startswith('GITHUB_TOKEN='):
                TOKEN = line.strip().split('=', 1)[1]
                break

if not TOKEN:
    print("❌ GITHUB_TOKEN not found. Add it to /opt/data/.env")
    sys.exit(1)

# ── GitHub API helper ──
def github_api(method, path, data=None):
    url = f'https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}'
    headers = {
        'Authorization': f'token {TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    req = urllib.request.Request(url, method=method, headers=headers)
    if data is not None:
        req.data = json.dumps(data).encode('utf-8')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        return {'error': True, 'status': e.code, 'body': body}

# ── Get directory info ──
def get_dir_info(dir_path):
    result = github_api('GET', dir_path)
    if isinstance(result, dict) and result.get('error'):
        return {'count': 0, 'oldest': None, 'newest': None}
    files = [item for item in result if isinstance(item, dict) and item.get('type') == 'file']
    count = len(files)
    dates = []
    for f in files:
        match = re.match(r'(\d{4}-\d{2}-\d{2})', f['name'])
        if match:
            dates.append(match.group(1))
    dates = sorted(set(dates))
    if dates:
        return {'count': count, 'oldest': dates[0], 'newest': dates[-1]}
    return {'count': count, 'oldest': None, 'newest': None}

# ── Update category TOC ──
def update_toc(category, filename, date_str, description):
    toc_path = f'{category}-table-of-content.html'
    toc_info = github_api('GET', toc_path)
    if isinstance(toc_info, dict) and toc_info.get('error'):
        print(f"  ⚠️  TOC not found, skipping TOC update")
        return

    sha = toc_info['sha']
    toc = base64.b64decode(toc_info['content']).decode('utf-8')

    # Build new entry
    slug = filename.replace('.html', '')
    new_entry = f'''  <div class="entry">
    <div class="entry-date">{date_str}</div>
    <div class="entry-title"><a href="{category}/{filename}">{filename}</a></div>
    <div class="entry-desc">{description}</div>
  </div>
'''

    # Insert before footer-note
    marker = '  <div class="footer-note">'
    if marker in toc:
        toc = toc.replace(marker, new_entry + marker)
        # Update count
        old_count_match = re.search(r'<span>(\d+) entries</span>', toc)
        if old_count_match:
            old_count = int(old_count_match.group(1))
            toc = toc.replace(f'<span>{old_count} entries</span>', f'<span>{old_count + 1} entries</span>')

        result = github_api('PUT', toc_path, {
            'message': f'Update {category} TOC: add {slug}',
            'content': base64.b64encode(toc.encode('utf-8')).decode('ascii'),
            'sha': sha
        })
        if isinstance(result, dict) and result.get('error'):
            print(f"  ❌  TOC update failed: {result['status']}")
        else:
            print(f"  ✅  TOC updated ({old_count + 1} entries)")
    else:
        print(f"  ⚠️  Could not find footer marker in TOC")

# ── Update index.html ──
def update_index():
    index_info = github_api('GET', 'index.html')
    if isinstance(index_info, dict) and index_info.get('error'):
        print(f"  ❌  index.html fetch failed: {index_info['status']}")
        return

    sha = index_info['sha']
    content = base64.b64decode(index_info['content']).decode('utf-8')

    categories = {
        'log': get_dir_info('log'),
        'guide': get_dir_info('guide'),
        'artwork': get_dir_info('artwork'),
    }

    updated = False
    for cat, info in categories.items():
        if not info['oldest']:
            continue
        new_meta = f'<div class="nav-meta">{info["count"]} entries \u00b7 {info["oldest"]} \u2014 {info["newest"]}</div>'

        # Simple string replacement: find the line after the category link
        old_pattern = rf'(<h2><a href="{cat}-table-of-content\.html">[^<]+</a></h2>\s*<p>[^<]+</p>\s*)<div class="nav-meta">[^<]+</div>'
        new_html = re.sub(old_pattern, rf'\1{new_meta}', content)
        if new_html != content:
            content = new_html
            updated = True
            print(f"  ✅  Index {cat}: {info['count']} entries \u00b7 {info['oldest']} \u2014 {info['newest']}")

    if not updated:
        print(f"  ℹ️  Index already up to date")
        return

    result = github_api('PUT', 'index.html', {
        'message': 'Update index: sync entry counts and date ranges',
        'content': base64.b64encode(content.encode('utf-8')).decode('ascii'),
        'sha': sha
    })
    if isinstance(result, dict) and result.get('error'):
        print(f"  ❌  Index update failed: {result['status']}")
    else:
        print(f"  ✅  Index.html updated")

# ── Main ──
def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    category = sys.argv[1]
    local_path = sys.argv[2]
    description = sys.argv[3] if len(sys.argv) > 3 else ''

    if category not in ('log', 'guide', 'artwork'):
        print(f"❌ Unknown category: {category}. Use: log, guide, artwork")
        sys.exit(1)

    if not os.path.exists(local_path):
        print(f"❌ File not found: {local_path}")
        sys.exit(1)

    # Derive filename from local path
    basename = os.path.basename(local_path)

    # Extract date from filename (YYYY-MM-DD prefix)
    date_match = re.match(r'(\d{4}-\d{2}-\d{2})', basename)
    if date_match:
        date_str = date_match.group(1)
    else:
        from datetime import datetime
        date_str = datetime.now().strftime('%Y-%m-%d')
        basename = f"{date_str}_{basename}"
        print(f"  ℹ️  Prefixed date: {basename}")

    remote_path = f'{category}/{basename}'

    print(f"\n🚀 Deploying to {OWNER}/{REPO}")
    print(f"   Category: {category}")
    print(f"   File: {basename}")
    print(f"   Remote: {remote_path}")

    # 1. Upload file
    with open(local_path, 'rb') as f:
        file_content = f.read()

    result = github_api('PUT', remote_path, {
        'message': f'Add {category}: {basename}',
        'content': base64.b64encode(file_content).decode('ascii')
    })
    if isinstance(result, dict) and result.get('error'):
        print(f"\n  ❌  Upload failed: {result['status']} - {result['body'][:200]}")
        sys.exit(1)
    print(f"\n  ✅  Uploaded: {result.get('content', {}).get('html_url', 'OK')}")

    # 2. Update TOC
    print(f"\n  📋 Updating {category} TOC...")
    update_toc(category, basename, date_str, description)

    # 3. Update index.html
    print(f"\n  📊 Updating index.html...")
    update_index()

    print(f"\n  🎉 Done! Live at: https://{OWNER}.github.io/{REPO}/{category}/{basename}")

if __name__ == '__main__':
    main()
