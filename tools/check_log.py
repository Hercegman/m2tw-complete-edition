#!/usr/bin/env python3
"""Parse the game's trace log after a test run by the maintainer.

Usage:
    python3 tools/check_log.py "/mnt/c/Program Files (x86)/Steam/steamapps/common/Medieval II Total War/logs/complete_edition.log.txt"

Classifies [error]/[warning] lines, prints a summary and the first errors,
and saves a signature snapshot to research/last_log_signature.txt so the next
run can be diffed against it.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SNAP = os.path.join(ROOT, "research", "last_log_signature.txt")

MAX_SHOW = 30


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")

    errors, warnings = [], []
    for i, l in enumerate(lines, 1):
        low = l.lower()
        if "[error]" in low or re.search(r"\berror\b", low) and "trace" not in low[:30]:
            errors.append((i, l.strip()))
        elif "[warning]" in low:
            warnings.append((i, l.strip()))

    print(f"log: {path}")
    print(f"lines: {len(lines)}, errors: {len(errors)}, warnings: {len(warnings)}")

    sig = []
    if errors:
        print(f"\nfirst {min(MAX_SHOW, len(errors))} errors:")
        for i, l in errors[:MAX_SHOW]:
            print(f"  {i}: {l}")
            sig.append(l)

    # diff against previous signature
    if os.path.exists(SNAP):
        prev = set(open(SNAP, encoding="utf-8").read().split("\n"))
        new = [l for l in sig if l not in prev]
        fixed = [l for l in prev if l and l not in set(sig)]
        if new:
            print(f"\nNEW since last run ({len(new)}):")
            for l in new[:MAX_SHOW]:
                print(f"  + {l}")
        if fixed:
            print(f"\nGONE since last run ({len(fixed)}):")
            for l in fixed[:MAX_SHOW]:
                print(f"  - {l}")

    os.makedirs(os.path.dirname(SNAP), exist_ok=True)
    open(SNAP, "w", encoding="utf-8").write("\n".join(sig))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
