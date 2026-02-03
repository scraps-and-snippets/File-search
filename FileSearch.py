import argparse
import os
import re
from pathlib import Path

DEFAULT_EXTS = {".cpp", ".h", ".hpp", ".cxx", ".cc", ".inl"}

def iter_files(root: Path, exts: set[str]):
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p

def read_text_lines(path: Path) -> list[str] | None:
    # Try utf-8 first; fall back to Windows-1252-like decoding if needed.
    try:
        return path.read_text(encoding="utf-8", errors="strict").splitlines()
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            return None

def find_matches(lines: list[str], pattern: str, use_regex: bool, ignore_case: bool):
    flags = re.MULTILINE
    if ignore_case:
        flags |= re.IGNORECASE

    if use_regex:
        rx = re.compile(pattern, flags)
        for i, line in enumerate(lines):
            if rx.search(line):
                yield i
    else:
        needle = pattern.lower() if ignore_case else pattern
        for i, line in enumerate(lines):
            hay = line.lower() if ignore_case else line
            if needle in hay:
                yield i

def merge_ranges(ranges: list[tuple[int,int]]) -> list[tuple[int,int]]:
    if not ranges:
        return []
    ranges.sort()
    merged = [ranges[0]]
    for s, e in ranges[1:]:
        ps, pe = merged[-1]
        if s <= pe + 1:
            merged[-1] = (ps, max(pe, e))
        else:
            merged.append((s, e))
    return merged

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="Root directory to search (e.g. repo root)")
    ap.add_argument("pattern", help="Search string or regex (see --regex)")
    ap.add_argument("-n", "--context", type=int, default=5, help="Lines of context before/after")
    ap.add_argument("-o", "--out", default="results.txt", help="Output file")
    ap.add_argument("--regex", action="store_true", help="Treat pattern as regex")
    ap.add_argument("-i", "--ignore-case", action="store_true", help="Case-insensitive search")
    ap.add_argument("--no-merge", action="store_true", help="Do not merge overlapping context blocks")
    ap.add_argument("--max-matches", type=int, default=0, help="Stop after this many matches (0 = no limit)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    exts = DEFAULT_EXTS

    total_matches = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for path in iter_files(root, exts):
            lines = read_text_lines(path)
            if lines is None:
                continue

            hit_idxs = list(find_matches(lines, args.pattern, args.regex, args.ignore_case))
            if not hit_idxs:
                continue

            # Build context ranges per hit
            ranges = []
            for idx in hit_idxs:
                s = max(0, idx - args.context)
                e = min(len(lines) - 1, idx + args.context)
                ranges.append((s, e))

            if not args.no_merge:
                ranges = merge_ranges(ranges)

            for (s, e) in ranges:
                # Identify which lines in this block are actual matches (for marking)
                match_set = set(i for i in hit_idxs if s <= i <= e)

                f.write(f"FILE: {path}\n")
                # If the block contains multiple hits, note them all
                match_lines_1based = [i + 1 for i in sorted(match_set)]
                f.write(f"MATCH_LINES: {match_lines_1based}\n")

                for i in range(s, e + 1):
                    prefix = ">> " if i in match_set else "   "
                    # 1-based line number
                    f.write(f"{prefix}{i+1:7d}: {lines[i]}\n")
                f.write("\n" + "-" * 80 + "\n\n")

                total_matches += len(match_set)
                if args.max_matches and total_matches >= args.max_matches:
                    f.write(f"Stopped early: reached --max-matches={args.max_matches}\n")
                    return

    print(f"Wrote results to {args.out}")

if __name__ == "__main__":
    main()
