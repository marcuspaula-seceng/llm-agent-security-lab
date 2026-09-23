#!/usr/bin/env python3
"""Pre-publication scan. Fails on credential-looking patterns and on any term from a
private disclosure list (employer names, host names, account names, local paths).

The disclosure list is NOT in this repository. Pass it with --terms <file> (one term per
line) or via the PUBLICATION_TERMS env var. Without it, only the credential patterns run.

    python tools/publication_gate.py [--terms private-terms.txt] [path]
Exit 1 on any hit. Standard library only.
"""

import argparse
import os
import pathlib
import re
import sys

CREDENTIAL_PATTERNS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "generic api key": re.compile(r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    "private key block": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    "bearer token": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-_.=]{20,}"),
    "password assignment": re.compile(r"(?i)\bpassword\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
    "windows drive path": re.compile(r"\b[A-Z]:\\(?:Users|data base|EOS)\\", re.IGNORECASE),
    "UNC path": re.compile(r"\\\\[A-Za-z0-9.-]+\\[A-Za-z$]"),
    "private ipv4 (non-doc)": re.compile(r"\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),
}
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
SKIP_FILES = {"publication_gate.py"}


def load_terms(path):
    if not path:
        return []
    return [t.strip() for t in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")]


def scan(root, terms):
    hits = []
    for p in pathlib.Path(root).rglob("*"):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.parts) or p.name in SKIP_FILES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for name, rx in CREDENTIAL_PATTERNS.items():
                if rx.search(line):
                    hits.append((p, i, name, line.strip()[:100]))
            low = line.lower()
            for t in terms:
                if t.lower() in low:
                    hits.append((p, i, f"disclosure term {t!r}", line.strip()[:100]))
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--terms", default=os.environ.get("PUBLICATION_TERMS"))
    a = ap.parse_args()
    hits = scan(a.path, load_terms(a.terms))
    for p, i, name, line in hits:
        print(f"HIT  {name:<28} {p}:{i}  {line}")
    print(f"\n{len(hits)} hit(s); terms loaded: {len(load_terms(a.terms))}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
