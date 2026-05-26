#!/usr/bin/env python3
"""Knowledge graph and confidence scoring over the repo.

Builds a graph from four edge sources:
- wikilinks `[[target]]` in body text → "references" edges (untyped)
- frontmatter `sources:` list items (if they resolve to repo files) → "sourced_from"
- frontmatter `supersedes:` / `superseded_by:` → "supersedes"
- body `> CONTRADICTION:` markers attached to the current file → "has_contradiction"

Also computes a per-page confidence bucket {high, medium, low} from:
- source_count (length of frontmatter `sources:` list)
- recency (days since frontmatter `last_updated`)
- contradiction_count (body markers)
- inbound_count (graph-derived)

Scope: context/, projects/, references/, outputs/. Skips archives/, raw/, daily/, .obsidian/, .git/, node_modules/, .claude/.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import re
from collections import defaultdict
from dataclasses import dataclass, field

SCAN_DIRS = ["context", "projects", "references", "outputs"]
SKIP_DIRS = {"archives", "raw", "daily", ".obsidian", ".git", "node_modules", ".claude"}
INDEX_NAMES = {"README.md", "index.md"}

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
LAST_UPDATED_RE = re.compile(r"^last_updated:\s*(\S+)", re.MULTILINE)
STATUS_RE = re.compile(r"^status:\s*(\S+)", re.MULTILINE)
TYPE_RE = re.compile(r"^type:\s*(\S+)", re.MULTILINE)
SUPERSEDES_RE = re.compile(r"^supersedes:\s*(.+)$", re.MULTILINE)
SUPERSEDED_BY_RE = re.compile(r"^superseded_by:\s*(.+)$", re.MULTILINE)
SOURCES_BLOCK_RE = re.compile(r"^sources:\s*\n((?:\s{2,}-\s*.+\n?)+)", re.MULTILINE)
SOURCES_INLINE_RE = re.compile(r"^sources:\s*\[(.+?)\]", re.MULTILINE)
WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:\|[^\]]+)?\]\]")
CONTRADICTION_RE = re.compile(r"^>\s*CONTRADICTION:", re.MULTILINE)
AT_IMPORT_RE = re.compile(r"(?:^|\s)@([\w/\-.]+\.md)\b")


@dataclass
class Node:
    stem: str
    path: pathlib.Path
    rel: pathlib.Path
    is_index: bool
    last_updated: dt.date | None
    status: str
    type: str
    source_count: int
    contradiction_count: int
    inbound: set[str] = field(default_factory=set)
    outbound: set[str] = field(default_factory=set)
    supersedes: set[str] = field(default_factory=set)
    superseded_by: set[str] = field(default_factory=set)


@dataclass
class Graph:
    nodes: dict[str, Node]
    folder_index: set[str]
    # edges stored as (src_stem, dst_stem, type)
    edges: list[tuple[str, str, str]]
    broken_links: list[tuple[pathlib.Path, str]]


def iter_md_files(root: pathlib.Path):
    for d in SCAN_DIRS:
        base = root / d
        if not base.exists():
            continue
        for p in base.rglob("*.md"):
            if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
                continue
            yield p


def parse_frontmatter(text: str) -> str | None:
    m = FRONTMATTER_RE.match(text)
    return m.group(1) if m else None


def parse_sources(fm: str) -> list[str]:
    block = SOURCES_BLOCK_RE.search(fm)
    if block:
        items = re.findall(r"-\s*(.+)", block.group(1))
        return [i.strip() for i in items if i.strip()]
    inline = SOURCES_INLINE_RE.search(fm)
    if inline:
        raw = inline.group(1)
        return [x.strip().strip('"').strip("'") for x in raw.split(",") if x.strip()]
    return []


def parse_date(s: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(s.strip())
    except ValueError:
        return None


def build(root: pathlib.Path) -> Graph:
    files = list(iter_md_files(root))
    nodes: dict[str, Node] = {}
    folder_index: set[str] = set()
    for p in files:
        if p.name in INDEX_NAMES:
            folder_index.add(p.parent.name)

    # First pass: create nodes.
    for p in files:
        text = p.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        last_updated = None
        status = ""
        ftype = ""
        sources: list[str] = []
        if fm:
            m = LAST_UPDATED_RE.search(fm)
            last_updated = parse_date(m.group(1)) if m else None
            sm = STATUS_RE.search(fm)
            status = sm.group(1).strip().lower() if sm else ""
            tm = TYPE_RE.search(fm)
            ftype = tm.group(1).strip().lower() if tm else ""
            sources = parse_sources(fm)
        contradictions = len(CONTRADICTION_RE.findall(text))
        stem = p.stem
        # Index/README pages are keyed by folder name to align with [[folder]] wikilinks.
        key = p.parent.name if p.name in INDEX_NAMES else stem
        # Avoid collisions: if two files share a key, keep first and alias later collisions by stem path.
        if key in nodes:
            key = f"{key}@{p.parent.name}/{p.stem}"
        nodes[key] = Node(
            stem=key,
            path=p,
            rel=p.relative_to(root),
            is_index=(p.name in INDEX_NAMES),
            last_updated=last_updated,
            status=status,
            type=ftype,
            source_count=len(sources),
            contradiction_count=contradictions,
        )

    edges: list[tuple[str, str, str]] = []
    broken_links: list[tuple[pathlib.Path, str]] = []

    def resolve(target: str) -> str | None:
        t = target.strip()
        if t in nodes:
            return t
        if t in folder_index:
            return t  # folder key matches index node key directly
        return None

    # Second pass: parse links and frontmatter edges.
    for key, node in nodes.items():
        text = node.path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text) or ""

        # wikilinks in body/frontmatter
        for match in WIKILINK_RE.finditer(text):
            target = match.group(1).strip()
            resolved = resolve(target)
            if resolved is None:
                broken_links.append((node.rel, target))
                continue
            if resolved == key:
                continue
            edges.append((key, resolved, "references"))
            node.outbound.add(resolved)
            nodes[resolved].inbound.add(key)

        # supersedes / superseded_by
        m = SUPERSEDES_RE.search(fm)
        if m:
            target = m.group(1).strip().strip('"').strip("'")
            # try to resolve: value may be a path or stem
            target_stem = pathlib.PurePath(target).stem
            resolved = resolve(target_stem)
            if resolved:
                edges.append((key, resolved, "supersedes"))
                node.supersedes.add(resolved)
                nodes[resolved].superseded_by.add(key)
        m = SUPERSEDED_BY_RE.search(fm)
        if m:
            target = m.group(1).strip().strip('"').strip("'")
            target_stem = pathlib.PurePath(target).stem
            resolved = resolve(target_stem)
            if resolved:
                edges.append((key, resolved, "superseded_by"))
                node.superseded_by.add(resolved)
                nodes[resolved].supersedes.add(key)

        # sources list: add edge where source references another repo file
        sources = parse_sources(fm)
        for s in sources:
            s_stem = pathlib.PurePath(s).stem
            resolved = resolve(s_stem)
            if resolved and resolved != key:
                edges.append((key, resolved, "sourced_from"))

    # External inbound sources (CLAUDE.md @imports) counted for orphan/confidence.
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        text = claude_md.read_text(encoding="utf-8", errors="replace")
        for match in WIKILINK_RE.finditer(text):
            resolved = resolve(match.group(1).strip())
            if resolved:
                nodes[resolved].inbound.add("CLAUDE.md")
        for match in AT_IMPORT_RE.finditer(text):
            imp = match.group(1)
            stem = pathlib.PurePath(imp).stem
            resolved = resolve(stem) or resolve(pathlib.PurePath(imp).parent.name)
            if resolved:
                nodes[resolved].inbound.add("CLAUDE.md")

    return Graph(nodes=nodes, folder_index=folder_index, edges=edges, broken_links=broken_links)


def confidence(node: Node, today: dt.date) -> str:
    if node.is_index:
        return "n/a"  # indices aren't claim-bearing pages
    if node.type in ("rhythm-file", "rule", "goal-list"):
        return "n/a"  # structural pages, not claim-bearing
    if node.status == "evergreen":
        return "n/a"  # reference artifacts (problem pages, textbook excerpts); don't decay
    if node.last_updated is None:
        return "low"
    age_days = (today - node.last_updated).days
    if node.contradiction_count > 0:
        return "low"
    if node.source_count == 0 and age_days > 60:
        return "low"
    if node.source_count >= 3 and age_days <= 30:
        return "high"
    if node.source_count >= 1 and age_days <= 90:
        return "medium"
    return "low"


REFRESH_THRESHOLD_DAYS = 180
REFRESH_MIN_INBOUND = 2


def refresh_candidates(graph: Graph, today: dt.date) -> list[tuple[Node, int]]:
    """Return (node, age_days) pairs for load-bearing pages due for refresh.

    Criteria: non-index, under context/ or projects/, inbound >= 2,
    last_updated missing or > 180d, not status=evergreen, and not already
    in the active-stale bucket (>60d AND status=active).
    """
    out = []
    for node in graph.nodes.values():
        if node.is_index:
            continue
        if node.status == "evergreen":
            continue
        top = node.rel.parts[0] if node.rel.parts else ""
        if top not in ("context", "projects"):
            continue
        if len(node.inbound) < REFRESH_MIN_INBOUND:
            continue
        if node.last_updated is None:
            out.append((node, -1))
            continue
        age = (today - node.last_updated).days
        if age <= REFRESH_THRESHOLD_DAYS:
            continue
        # Skip active-stale; already surfaced by the existing lint bucket
        if node.status == "active" and age > 60:
            continue
        out.append((node, age))
    # Sort by inbound count desc, then age desc
    out.sort(key=lambda t: (-len(t[0].inbound), -t[1]))
    return out


def confidence_reasons(node: Node, today: dt.date) -> list[str]:
    reasons = []
    if node.last_updated is None:
        reasons.append("no last_updated")
    else:
        age = (today - node.last_updated).days
        if age > 90:
            reasons.append(f"stale ({age}d)")
    if node.source_count == 0:
        reasons.append("no sources")
    elif node.source_count < 3:
        reasons.append(f"only {node.source_count} source(s)")
    if node.contradiction_count > 0:
        reasons.append(f"{node.contradiction_count} contradiction marker(s)")
    if len(node.inbound) == 0 and not node.is_index:
        reasons.append("no inbound links")
    return reasons
