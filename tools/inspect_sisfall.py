"""Inspect the downloaded SisFall archive without extracting it.

This is the tool that produced the facts recorded in
`docs/datasets/sisfall.md` — the subject inventory, the ADL/fall codes, the
duration distribution and the per-cohort coverage. Run it after downloading the
archive if you want to re-confirm those claims against the actual file, or if a
different mirror is ever substituted.

It writes nothing and changes nothing: it only reads and reports.

Usage (from the repository root):
    .venv\\Scripts\\python.exe tools\\inspect_sisfall.py
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import zipfile
from collections import Counter, defaultdict

#: The archive this project expects. Size and hash are the ones verified in
#: docs/datasets/sisfall.md; a mismatch is reported rather than ignored.
EXPECTED_SIZE = 232_407_821
EXPECTED_SHA256 = "7f0dd1583e39fee0f402a6855976eb12517f7eaecdacce871d5b3421793ad665"

_NAME_RE = re.compile(r"([DF])(\d{2})_S([AE])(\d{2})_R(\d{2})\.txt$")


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    zip_path = root / "data" / "raw" / "SisFall_dataset.zip"

    if not zip_path.exists():
        print(f"Archive not found: {zip_path}")
        print("Download it first — see docs/datasets/sisfall.md")
        return 1

    size = zip_path.stat().st_size
    print(f"file   : {zip_path}")
    print(f"size   : {size:,} bytes")
    print(f"expected: {EXPECTED_SIZE:,} bytes -> match: {size == EXPECTED_SIZE}")

    digest = hashlib.sha256()
    with zip_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual_sha = digest.hexdigest()
    print(f"sha256 : {actual_sha}")
    print(f"match  : {actual_sha == EXPECTED_SHA256}")

    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
        print(f"integrity: {'OK' if bad is None else f'CORRUPT at {bad}'}")

        names = archive.namelist()
        print(f"members: {len(names):,} (incl. __MACOSX metadata)")

        data_names = [
            n
            for n in names
            if n.startswith("SisFall_dataset/")
            and n.endswith(".txt")
            and "/._" not in n
            and not n.endswith("/Readme.txt")
        ]
        print(f"data files: {len(data_names):,}")

        # Subject inventory and cohort coverage.
        subjects: set[str] = set()
        cohort_codes: dict[str, set[str]] = defaultdict(set)
        runs: Counter[str] = Counter()
        rows_by_kind: dict[str, Counter[int]] = {"D": Counter(), "F": Counter()}

        for name in data_names:
            match = _NAME_RE.search(name)
            if match is None:
                continue
            kind, code, cohort_letter, subject_num, run = match.groups()
            subjects.add(f"S{cohort_letter}{subject_num}")
            cohort_codes[cohort_letter].add(kind + code)
            runs[f"{kind}{code}"] += 1

            with archive.open(name) as handle:
                newlines = 0
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break
                    newlines += chunk.count(b"\n")
            rows_by_kind[kind][newlines] += 1

    adults = sorted(s for s in subjects if s.startswith("SA"))
    elderly = sorted(s for s in subjects if s.startswith("SE"))
    print(f"\nsubjects: {len(subjects)} -> adults={len(adults)} elderly={len(elderly)}")

    for letter, label in (("A", "adults"), ("E", "elderly")):
        adl = sorted(c for c in cohort_codes[letter] if c.startswith("D"))
        fall = sorted(c for c in cohort_codes[letter] if c.startswith("F"))
        print(f"  {label:>7}: {len(adl)} ADL codes, {len(fall)} fall codes")

    # Which subjects produced falls? Decides how the elderly result is reported.
    fall_subjects = sorted(
        {
            f"S{m.group(3)}{m.group(4)}"
            for n in data_names
            for m in [_NAME_RE.search(n)]
            if m is not None and m.group(1) == "F"
        }
    )
    print(f"\nsubjects with falls: {len(fall_subjects)}")
    print(f"  elderly with falls: {sorted(s for s in fall_subjects if s.startswith('SE'))}")

    for kind, label in (("D", "ADL"), ("F", "fall")):
        rows = rows_by_kind[kind]
        if rows:
            lo, hi = min(rows), max(rows)
            print(
                f"\n{label} recordings: {sum(rows.values()):,} files, "
                f"{lo}–{hi} rows ({lo / 200:.1f}–{hi / 200:.1f}s at 200 Hz)"
            )

    print("\nReadme column spec lives inside the archive at SisFall_dataset/Readme.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
