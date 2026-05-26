#!/usr/bin/env python3
"""CLI for the /graph skill. Query the knowledge graph."""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from graph import Graph, build, confidence, confidence_reasons, refresh_candidates  # noqa: E402


def fmt_node_line(g: Graph, key: str) -> str:
    n = g.nodes.get(key)
    if n is None:
        return f"{key} (external)"
    return f"{key} — {n.rel}"


def cmd_list(g: Graph, args):
    for key in sorted(g.nodes):
        n = g.nodes[key]
        tag = "[index]" if n.is_index else ""
        print(f"{key:40s} {tag:8s} {n.rel}")


def cmd_inbound(g: Graph, args):
    n = g.nodes.get(args.target)
    if not n:
        print(f"unknown: {args.target}", file=sys.stderr)
        sys.exit(1)
    if not n.inbound:
        print(f"{args.target}: no inbound links")
        return
    print(f"Inbound to {args.target}:")
    for src in sorted(n.inbound):
        print(f"  ← {fmt_node_line(g, src)}")


def cmd_outbound(g: Graph, args):
    n = g.nodes.get(args.target)
    if not n:
        print(f"unknown: {args.target}", file=sys.stderr)
        sys.exit(1)
    if not n.outbound:
        print(f"{args.target}: no outbound links")
        return
    print(f"Outbound from {args.target}:")
    for dst in sorted(n.outbound):
        print(f"  → {fmt_node_line(g, dst)}")


def cmd_around(g: Graph, args):
    n = g.nodes.get(args.target)
    if not n:
        print(f"unknown: {args.target}", file=sys.stderr)
        sys.exit(1)
    print(f"Subgraph around {args.target} ({n.rel}):")
    if n.inbound:
        print("  inbound:")
        for src in sorted(n.inbound):
            print(f"    ← {fmt_node_line(g, src)}")
    if n.outbound:
        print("  outbound:")
        for dst in sorted(n.outbound):
            print(f"    → {fmt_node_line(g, dst)}")
    if n.supersedes:
        print("  supersedes:")
        for s in sorted(n.supersedes):
            print(f"    ⇢ {fmt_node_line(g, s)}")
    if n.superseded_by:
        print("  superseded_by:")
        for s in sorted(n.superseded_by):
            print(f"    ⇠ {fmt_node_line(g, s)}")


def cmd_node(g: Graph, args):
    n = g.nodes.get(args.target)
    if not n:
        print(f"unknown: {args.target}", file=sys.stderr)
        sys.exit(1)
    today = dt.date.today()
    bucket = confidence(n, today)
    reasons = confidence_reasons(n, today)
    print(f"Node: {args.target}")
    print(f"  path: {n.rel}")
    print(f"  is_index: {n.is_index}")
    print(f"  status: {n.status or '(unset)'}")
    print(f"  last_updated: {n.last_updated or '(unset)'}")
    print(f"  sources: {n.source_count}")
    print(f"  contradictions: {n.contradiction_count}")
    print(f"  inbound: {len(n.inbound)} / outbound: {len(n.outbound)}")
    print(f"  confidence: {bucket}" + (f" ({'; '.join(reasons)})" if reasons else ""))


def cmd_low_confidence(g: Graph, args):
    today = dt.date.today()
    buckets = {"low": [], "medium": []}
    for key, n in g.nodes.items():
        if n.is_index:
            continue
        b = confidence(n, today)
        if b in buckets:
            buckets[b].append((key, n, confidence_reasons(n, today)))
    for bucket in ("low", "medium") if not args.low_only else ("low",):
        items = sorted(buckets[bucket], key=lambda t: str(t[1].rel))
        print(f"## {bucket.upper()} confidence ({len(items)})")
        for key, n, reasons in items:
            print(f"  {n.rel} — {'; '.join(reasons) or '(rule match)'}")
        print()


def cmd_refresh_queue(g: Graph, args):
    today = dt.date.today()
    items = refresh_candidates(g, today)
    if not items:
        print("No pages due for refresh.")
        return
    print(f"Pages due for refresh ({len(items)}):")
    for node, age in items:
        age_str = f"{age}d" if age >= 0 else "never"
        print(f"  {node.rel} — inbound={len(node.inbound)}, last_updated={age_str}")


def cmd_broken(g: Graph, args):
    if not g.broken_links:
        print("No broken wikilinks.")
        return
    for src, target in sorted(set(g.broken_links)):
        print(f"  {src} → [[{target}]]")


def cmd_export(g: Graph, args):
    # Simple edge list as TSV: src\tdst\ttype
    for s, d, t in g.edges:
        print(f"{s}\t{d}\t{t}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")

    p = sub.add_parser("inbound")
    p.add_argument("target")

    p = sub.add_parser("outbound")
    p.add_argument("target")

    p = sub.add_parser("around")
    p.add_argument("target")

    p = sub.add_parser("node")
    p.add_argument("target")

    p = sub.add_parser("low-confidence")
    p.add_argument("--low-only", action="store_true")

    sub.add_parser("broken")
    sub.add_parser("export")
    sub.add_parser("refresh-queue")

    args = ap.parse_args()
    root = pathlib.Path(args.root).resolve()
    g = build(root)

    dispatch = {
        "list": cmd_list,
        "inbound": cmd_inbound,
        "outbound": cmd_outbound,
        "around": cmd_around,
        "node": cmd_node,
        "low-confidence": cmd_low_confidence,
        "broken": cmd_broken,
        "export": cmd_export,
        "refresh-queue": cmd_refresh_queue,
    }
    dispatch[args.cmd](g, args)


if __name__ == "__main__":
    main()
