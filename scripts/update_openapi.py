#!/usr/bin/env python3
"""Fetch the partner-service OpenAPI spec and write a Mintlify-safe openapi.json.

The raw export breaks the docs in two ways, so it must never be saved as-is:
- "default" keys render incorrectly in the Mintlify playground
- "marked_for_null_replacement" is an internal marker that must become "example": null

Usage:
    python3 scripts/update_openapi.py            # fetch prod, update openapi.json
    python3 scripts/update_openapi.py --url URL --output FILE
    python3 scripts/update_openapi.py --force    # overwrite even if documented ops vanish
"""
import argparse
import glob
import json
import re
import sys
import urllib.request

DEFAULT_URL = "https://api.explorium.ai/openapi.json"
FRONTMATTER = re.compile(r'^openapi:\s*"?(\w+)\s+(\S+?)"?\s*$', re.M)


def replace_marked_fields(obj):
    """Transformation semantics identical to the original json_replacer.py."""
    if isinstance(obj, dict):
        new_obj = {}
        for key, value in obj.items():
            # Skip "default" fields entirely
            if key == "default":
                continue
            if key == "marked_for_null_replacement" and value is True:
                new_obj["example"] = None
            else:
                new_obj[key] = replace_marked_fields(value)
        return new_obj
    elif isinstance(obj, list):
        return [replace_marked_fields(item) for item in obj]
    return obj


def documented_operations():
    """Every (method, path) referenced by page frontmatter across the docs."""
    ops = set()
    for f in glob.glob("v2/**/*.mdx", recursive=True) + glob.glob("reference/**/*.mdx", recursive=True):
        m = FRONTMATTER.search(open(f, encoding="utf-8").read())
        if m:
            ops.add((m.group(1).lower(), m.group(2), f))
    return ops


def path_summary(spec):
    counts = {}
    for p in spec["paths"]:
        counts[p.split("/")[1]] = counts.get(p.split("/")[1], 0) + 1
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--output", default="openapi.json")
    ap.add_argument("--force", action="store_true",
                    help="write even if operations referenced by doc pages are missing")
    args = ap.parse_args()

    with urllib.request.urlopen(args.url, timeout=60) as r:
        raw = json.load(r)
    new = replace_marked_fields(raw)

    try:
        old = json.load(open(args.output))
    except FileNotFoundError:
        old = {"info": {"version": "none"}, "paths": {}}

    print(f"fetched  : {raw['info']['title']} {raw['info']['version']}  ({args.url})")
    print(f"current  : {old['info']['version']}")
    print(f"paths    : {len(old['paths'])} -> {len(new['paths'])}  {path_summary(new)}")
    added = sorted(set(new["paths"]) - set(old["paths"]))
    removed = sorted(set(old["paths"]) - set(new["paths"]))
    if added:
        print(f"added    : {added}")
        print("           ^ new operations likely need reference pages + nav entries")
    if removed:
        print(f"removed  : {removed}")

    # Guard: never silently break a documented playground.
    # (A v1-only export once clobbered every /v2 operation — this catches that class of mistake.)
    broken = [(m, p, f) for m, p, f in documented_operations()
              if p not in new["paths"] or m not in new["paths"][p]]
    if broken:
        print(f"\nBLOCKED: {len(broken)} documented operation(s) missing from the fetched spec:", file=sys.stderr)
        for m, p, f in sorted(broken)[:15]:
            print(f"  {m.upper()} {p}  <- {f}", file=sys.stderr)
        if not args.force:
            print("\nNothing written. If the removals are intentional, remove/repoint those pages "
                  "or rerun with --force.", file=sys.stderr)
            sys.exit(1)
        print("--force given: writing anyway.", file=sys.stderr)

    leftover_defaults = json.dumps(new).count('"default"')
    leftover_markers = json.dumps(new).count("marked_for_null_replacement")
    assert leftover_markers == 0, "marker survived transformation"

    with open(args.output, "w") as f:
        json.dump(new, f, indent=2)
    print(f"\nwrote {args.output}  (defaults: {leftover_defaults}, markers: {leftover_markers})")


if __name__ == "__main__":
    main()
