#!/usr/bin/env python3
"""Package hygiene: no build or cache debris, no local paths, no credentials.

Fails on cache and build files (__pycache__, .pyc, LaTeX intermediates, virtual
environments, .DS_Store), on absolute paths of a personal machine (/Users/, /home/,
/private/, Desktop/) and on strings shaped like API tokens. deon/results/ladder.log is
an approved log file. If a run left deon/__pycache__ behind, delete it or set
PYTHONDONTWRITEBYTECODE=1 before running Python in deon/.
"""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
bad_dirs = {'.git', '.hg', '.svn', '__pycache__', '.pytest_cache', '.mypy_cache', '.gocache',
            '.venv', '.venv_ad', 'venv', 'node_modules'}
bad_suffixes = ('.aux', '.bbl', '.bcf', '.blg', '.fdb_latexmk', '.fls', '.glob', '.log', '.out',
                '.run.xml', '.synctex.gz', '.toc', '.vo', '.vok', '.vos', '.pyc', '.bak')
bad_names = {'.DS_Store'}
local_markers = ('/Users/', '/home/', '/private/', 'Desktop/')
token = re.compile(r'(hf_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}'
                   r'|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})')
bad, local, secret = [], [], []
for p in root.rglob('*'):
    rel = p.relative_to(root)
    if rel.parts and rel.parts[0] == '.git':
        continue
    approved_log = rel.as_posix() == 'deon/results/ladder.log'
    if any(part in bad_dirs for part in rel.parts) or p.name in bad_names or (
            p.is_file() and p.name.endswith(bad_suffixes) and not approved_log):
        bad.append(str(rel))
    if p.is_file() and rel.as_posix() != 'scripts/check-hygiene.py' and p.stat().st_size <= 10_000_000:
        try:
            text = p.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        if any(m in text for m in local_markers):
            local.append(str(rel))
        if token.search(text):
            secret.append(str(rel))
if bad or local or secret:
    for x in bad: print('FORBIDDEN:', x)
    for x in local: print('LOCAL PATH:', x)
    for x in secret: print('POSSIBLE TOKEN:', x)
    sys.exit(1)
print('PASS: package hygiene, local-path and token checks')
