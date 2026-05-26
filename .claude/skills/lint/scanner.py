#!/usr/bin/env python3
"""Lint scanner for the executive-assistant repo.

Reports four issue classes as markdown to stdout (or a file when --out given):
- stale last_updated (>60 days, active pages)
- broken wikilinks
- orphan pages
- missing frontmatter

Scope: context/, projects/. Skips archives/, raw/, daily/, .obsidian/, .git/, node_modules/, outputs/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import pathlib
import re
import sys
from collections import defaultdict

H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

# Let us import the graph module alongside.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "graph"))
try:
    from graph import build as build_graph, confidence as conf_bucket, confidence_reasons, refresh_candidates  # type: ignore
    HAS_GRAPH = True
except ImportError:
    HAS_GRAPH = False

SCAN_DIRS = ["context", "projects"]
SKIP_DIRS = {"archives", "raw", "daily", ".obsidian", ".git", "node_modules", ".claude"}
STALE_DAYS = 60
INDEX_NAMES = {"README.md", "index.md"}

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
LAST_UPDATED_RE = re.compile(r"^last_updated:\s*(\S+)", re.MULTILINE)
STATUS_RE = re.compile(r"^status:\s*(\S+)", re.MULTILINE)
WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:\|[^\]]+)?\]\]")
AT_IMPORT_RE = re.compile(r"(?:^|\s)@([\w/\-.]+\.md)\b")


def iter_md_files(root: pathlib.Path, scan_dirs):
    for d in scan_dirs:
        base = root / d
        if not base.exists():
            continue
        for p in base.rglob("*.md"):
            if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
                continue
            yield p


def parse_frontmatter(text: str):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    return m.group(1)


def scan(root: pathlib.Path, today: dt.date):
    files = list(iter_md_files(root, SCAN_DIRS))
    # Index by filename stem AND by folder name (when folder contains README.md or index.md).
    filename_index: dict[str, list[pathlib.Path]] = defaultdict(list)
    for p in files:
        filename_index[p.stem].append(p)
    folder_index: set[str] = set()
    for p in files:
        if p.name in INDEX_NAMES:
            folder_index.add(p.parent.name)

    stale = []  # (path, last_updated, age_days)
    broken = []  # (path, wikilink_target)
    missing_fm = []  # path
    link_targets: set[str] = set()

    # Additional link sources outside SCAN_DIRS: CLAUDE.md @imports and wikilinks.
    extra_sources = [root / "CLAUDE.md"]

    for p in files:
        text = p.read_text(encoding="utf-8", errors="replace")
        rel = p.relative_to(root)
        fm = parse_frontmatter(text)

        if fm is None:
            if p.name not in INDEX_NAMES:
                missing_fm.append(rel)
        else:
            m = LAST_UPDATED_RE.search(fm)
            sm = STATUS_RE.search(fm)
            status = sm.group(1).strip().lower() if sm else ""
            if m and status in ("", "active"):
                try:
                    d = dt.date.fromisoformat(m.group(1).strip())
                    age = (today - d).days
                    if age > STALE_DAYS:
                        stale.append((rel, m.group(1).strip(), age))
                except ValueError:
                    pass

        for match in WIKILINK_RE.finditer(text):
            target = match.group(1).strip()
            link_targets.add(target)
            if target not in filename_index and target not in folder_index:
                broken.append((rel, target))

    # Pull @imports and wikilinks from extra sources too (for orphan accounting only).
    for extra in extra_sources:
        if not extra.exists():
            continue
        text = extra.read_text(encoding="utf-8", errors="replace")
        for match in WIKILINK_RE.finditer(text):
            link_targets.add(match.group(1).strip())
        for match in AT_IMPORT_RE.finditer(text):
            imp = match.group(1)
            stem = pathlib.PurePath(imp).stem
            link_targets.add(stem)

    # orphans: files in context/ or projects/ never referenced, excluding indices.
    orphans = []
    for p in files:
        rel = p.relative_to(root)
        if rel.parts[0] not in ("context", "projects"):
            continue
        if p.name in INDEX_NAMES:
            continue
        if p.stem in link_targets:
            continue
        # Folder-named references count too: if this file is the README/index of a folder
        # and another file links [[folder-name]], we've already handled that via folder_index.
        orphans.append(rel)

    # Build known-keys universe for broken-link suggestions (slugs + folder names).
    known_keys = sorted(set(filename_index.keys()) | folder_index)

    # Suggestions: broken-link "did you mean", orphan "link from", missing-fm stubs.
    broken_with_suggestion = []
    seen_broken = set()
    for src_rel, target in broken:
        if (src_rel, target) in seen_broken:
            continue
        seen_broken.add((src_rel, target))
        matches = difflib.get_close_matches(target, known_keys, n=1, cutoff=0.75)
        suggestion = matches[0] if matches else None
        broken_with_suggestion.append((src_rel, target, suggestion))

    orphan_with_suggestion = []
    for rel in orphans:
        parent = rel.parent
        # Look for index/README in parent folder
        candidates = []
        for name in ("index.md", "README.md"):
            cand = parent / name
            if (root / cand).exists():
                candidates.append(cand)
        orphan_with_suggestion.append((rel, candidates))

    missing_fm_with_stub = []
    for rel in missing_fm:
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        m = H1_RE.search(text)
        title = m.group(1).strip() if m else rel.stem.replace("-", " ").title()
        stub = (
            "---\n"
            f"title: {title}\n"
            "type: TODO\n"
            f"last_updated: {today.isoformat()}\n"
            "sources: []\n"
            "---"
        )
        missing_fm_with_stub.append((rel, stub))

    low_conf = []
    refresh = []
    if HAS_GRAPH:
        g = build_graph(root)
        for key, n in g.nodes.items():
            if n.is_index:
                continue
            if n.rel.parts and n.rel.parts[0] not in SCAN_DIRS:
                continue  # mirror lint scope: skip outputs/ etc.
            b = conf_bucket(n, today)
            if b == "low":
                low_conf.append((n.rel, "; ".join(confidence_reasons(n, today)) or "(rule match)"))
        for n, age in refresh_candidates(g, today):
            age_str = f"{age}d" if age >= 0 else "never"
            refresh.append((n.rel, len(n.inbound), age_str))

    return {
        "stale": sorted(stale, key=lambda t: -t[2]),
        "broken": sorted(broken_with_suggestion),
        "orphans": sorted(orphan_with_suggestion),
        "missing_fm": sorted(missing_fm_with_stub),
        "low_conf": sorted(low_conf),
        "refresh": refresh,
        "scanned": len(files),
    }


def render(report, today: dt.date) -> str:
    out = [f"# Lint report {today.isoformat()}", ""]
    out.append(f"Scanned {report['scanned']} markdown files under `context/`, `projects/`.")
    out.append("")

    def section(title: str, items, fmt):
        out.append(f"## {title} ({len(items)})")
        out.append("")
        if not items:
            out.append("_None._")
        else:
            for item in items:
                out.append(f"- {fmt(item)}")
        out.append("")

    section(
        f"Stale `last_updated` (>{STALE_DAYS}d, status=active)",
        report["stale"],
        lambda t: f"`{t[0]}` — {t[1]} ({t[2]}d)",
    )
    def fmt_broken(t):
        src, target, suggestion = t
        base = f"`{src}` → [[{target}]]"
        if suggestion:
            base += f" — did you mean `[[{suggestion}]]`?"
        return base

    def fmt_orphan(t):
        rel, candidates = t
        base = f"`{rel}`"
        if candidates:
            cand_str = " or ".join(f"`{c}`" for c in candidates)
            base += f" — suggest linking from {cand_str}"
        return base

    def fmt_missing_fm(t):
        rel, stub = t
        indented = "\n".join("      " + line for line in stub.splitlines())
        return f"`{rel}`\n\n    ```yaml\n{indented}\n    ```"

    section("Broken wikilinks", report["broken"], fmt_broken)
    section("Orphan pages (no inbound wikilinks)", report["orphans"], fmt_orphan)
    section("Missing frontmatter", report["missing_fm"], fmt_missing_fm)
    section(
        "Low-confidence pages",
        report.get("low_conf", []),
        lambda t: f"`{t[0]}` — {t[1]}",
    )
    section(
        "Pages due for refresh (load-bearing, >180d)",
        report.get("refresh", []),
        lambda t: f"`{t[0]}` — inbound={t[1]}, last_updated={t[2]}",
    )
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", help="write report to this path instead of stdout")
    ap.add_argument("--today", help="override today (YYYY-MM-DD) for testing")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    report = scan(root, today)
    text = render(report, today)
    if args.out:
        pathlib.Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
