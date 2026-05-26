#!/usr/bin/env python3
"""UserPromptSubmit hook: grep prompt against wiki slugs/names, inject hits.

Reads the hook JSON on stdin, matches the prompt against:
- filename stems under context/, projects/, references/
- folder names containing README.md or index.md
- title: frontmatter values in context/orgs/*/index.md and context/orgs/*.md

Emits additionalContext listing up to 5 matching paths. Silent on zero hits.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

SCAN_DIRS = ["context", "projects", "references"]
SKIP_DIRS = {"archives", "raw", "daily", ".obsidian", ".git", "node_modules", ".claude"}
INDEX_NAMES = {"README.md", "index.md"}
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had", "will", "would", "can", "could",
    "should", "may", "might", "must", "shall",
    "what", "when", "where", "who", "why", "how", "which", "that", "this",
    "and", "or", "but", "if", "then", "else", "for", "to", "from", "of", "in",
    "on", "at", "by", "with", "about", "as", "into", "out", "up", "down",
    "i", "me", "my", "you", "your", "it", "its", "they", "them", "he", "she",
    "we", "us", "our",
    "not", "no", "yes",
    "get", "got", "tell", "show", "draft", "write", "read", "make", "need",
    "want", "let", "lets", "ok", "okay", "sure", "yeah", "nah",
    # Generic repo words we don't want matching top-level folders
    "context", "projects", "outputs", "people", "orgs", "log", "logs",
    "file", "files", "page", "pages", "note", "notes", "doc", "docs",
    "today", "yesterday", "tomorrow", "week", "month", "year",
    "one", "two", "three", "first", "last", "next", "new", "old",
    "all", "any", "some", "none", "more", "less", "most", "few",
    "also", "just", "only", "really", "very", "too", "so",
    "good", "bad", "right", "wrong", "work", "works", "worked",
}

TITLE_RE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
TOKEN_RE = re.compile(r"[a-z0-9]+")


def build_match_set(root: pathlib.Path):
    """Return (slugs, folder_keys, name_to_path).

    slugs: stem -> rel path
    folder_keys: folder name -> rel path of its index/README
    name_to_path: normalized name token -> rel path (for people/org titles)
    """
    slugs: dict[str, pathlib.Path] = {}
    folder_keys: dict[str, pathlib.Path] = {}
    name_to_path: dict[str, pathlib.Path] = {}

    for d in SCAN_DIRS:
        base = root / d
        if not base.exists():
            continue
        for p in base.rglob("*.md"):
            if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
                continue
            rel = p.relative_to(root)
            if p.name in INDEX_NAMES:
                folder = p.parent.name.lower()
                folder_keys[folder] = rel
                # Also contribute word-splits for multi-word folder names
                for tok in TOKEN_RE.findall(folder):
                    if len(tok) > 3 and tok not in STOPWORDS:
                        folder_keys.setdefault(tok, rel)
            else:
                stem = p.stem.lower()
                slugs.setdefault(stem, rel)
                # Also contribute word-splits so `argocd` hits `argocd-pipeline`
                for tok in TOKEN_RE.findall(stem):
                    if len(tok) > 3 and tok not in STOPWORDS:
                        slugs.setdefault(tok, rel)

    # Pull title: values from people + org index pages
    people_dir = root / "context" / "people"
    if people_dir.exists():
        for p in people_dir.glob("*.md"):
            _collect_titles(p, root, name_to_path)
    orgs_dir = root / "context" / "orgs"
    if orgs_dir.exists():
        for p in orgs_dir.rglob("index.md"):
            _collect_titles(p, root, name_to_path)

    return slugs, folder_keys, name_to_path


def _collect_titles(p: pathlib.Path, root: pathlib.Path, name_to_path: dict):
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    m = FRONTMATTER_RE.match(text)
    if not m:
        return
    t = TITLE_RE.search(m.group(1))
    if not t:
        return
    title = t.group(1).strip().strip('"').strip("'")
    for tok in TOKEN_RE.findall(title.lower()):
        if len(tok) <= 3 or tok in STOPWORDS:
            continue
        name_to_path.setdefault(tok, p.relative_to(root))


def tokenize(prompt: str) -> list[str]:
    toks = TOKEN_RE.findall(prompt.lower())
    return [t for t in toks if len(t) > 3 and t not in STOPWORDS]


def match(prompt: str, root: pathlib.Path, limit: int = 5) -> list[pathlib.Path]:
    slugs, folder_keys, name_to_path = build_match_set(root)
    tokens = tokenize(prompt)
    if not tokens:
        return []
    seen: set[pathlib.Path] = set()
    ranked: list[tuple[int, pathlib.Path]] = []  # (rank, path), lower rank = better
    for tok in tokens:
        if tok in slugs:
            p = slugs[tok]
            if p not in seen:
                ranked.append((0, p))
                seen.add(p)
        if tok in name_to_path:
            p = name_to_path[tok]
            if p not in seen:
                ranked.append((1, p))
                seen.add(p)
        if tok in folder_keys:
            p = folder_keys[tok]
            if p not in seen:
                ranked.append((2, p))
                seen.add(p)
    ranked.sort(key=lambda t: t[0])
    return [p for _, p in ranked[:limit]]


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    prompt = (payload.get("prompt") or "").strip()
    if not prompt or prompt.startswith("/"):
        sys.exit(0)
    if len([t for t in TOKEN_RE.findall(prompt.lower()) if len(t) > 1]) < 3:
        sys.exit(0)

    root = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    hits = match(prompt, root)
    if not hits:
        sys.exit(0)

    paths = ", ".join(f"`{p}`" for p in hits)
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": f"Possibly relevant wiki pages (from retrieval-hint): {paths}",
        }
    }
    json.dump(out, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
