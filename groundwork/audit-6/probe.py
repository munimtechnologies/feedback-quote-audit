# Copyright 2026 Munim, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""probe: schema and counts of the PERSUADE 2.0 training CSV, before any audit plan is written

Part of feedback-quote-audit groundwork, by MV2 of Munim, Inc. Made with AI agents working in his name.

Writes only the file hash, column names, row and essay counts, category counts for low-cardinality
columns (counted once per essay) and length quantiles of the longest text column. No essay text,
no ids and no single row are written.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
import zipfile

CSV_FIELD_LIMIT = 1 << 30
MAX_LEVELS = 40  # columns with at most this many distinct values get counts
ID_HINTS = ("essay_id_comp", "essay_id")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def open_text(path: str) -> io.TextIOBase:
    """The CSV itself, or the largest .csv inside a zip."""
    if zipfile.is_zipfile(path):
        zf = zipfile.ZipFile(path)
        names = [i for i in zf.infolist() if i.filename.lower().endswith(".csv")]
        if not names:
            raise ValueError("zip holds no .csv")
        best = max(names, key=lambda i: i.file_size)
        return io.TextIOWrapper(zf.open(best), encoding="utf-8-sig", newline="")
    return open(path, encoding="utf-8-sig", newline="")


def quantiles(values: list[int], qs=(0.05, 0.25, 0.5, 0.75, 0.95)) -> dict:
    if not values:
        return {}
    v = sorted(values)
    return {str(q): v[min(len(v) - 1, int(q * len(v)))] for q in qs}


def profile(fh) -> dict:
    csv.field_size_limit(CSV_FIELD_LIMIT)
    reader = csv.DictReader(fh)
    cols = list(reader.fieldnames or [])
    id_col = next((c for c in ID_HINTS if c in cols), None)
    levels: dict = {c: {} for c in cols}
    too_many: set = set()
    length_sum = dict.fromkeys(cols, 0)
    rows = 0
    first: dict = {}  # essay id -> its first row's low-cardinality values and text lengths
    for row in reader:
        rows += 1
        key = row.get(id_col) if id_col else str(rows)
        for c in cols:
            val = row.get(c) or ""
            length_sum[c] += len(val)
            if c not in too_many:
                levels[c][val] = 0
                if len(levels[c]) > MAX_LEVELS:
                    too_many.add(c)
                    levels[c] = {}
        if key not in first:
            first[key] = {c: (row.get(c) or "") for c in cols}
    text_col = max(cols, key=lambda c: length_sum[c]) if cols and rows else None
    counts: dict = {}
    for c in cols:
        if c in too_many or c == id_col or c == text_col:
            continue
        tally: dict = {}
        for vals in first.values():
            tally[vals[c]] = tally.get(vals[c], 0) + 1
        counts[c] = dict(sorted(tally.items()))
    words = [len(v[text_col].split()) for v in first.values()] if text_col else []
    return {
        "columns": cols,
        "rows": rows,
        "id_column": id_col,
        "essays": len(first),
        "text_column": text_col,
        "text_words_per_essay": quantiles(words),
        "high_cardinality_columns": sorted(too_many - {id_col, text_col}),
        "category_counts_per_essay": counts,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, help="the downloaded training file (CSV or zip)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if not os.path.isfile(args.data):
        print("not found: %s" % args.data, file=sys.stderr)
        return 2
    res = {"file_bytes": os.path.getsize(args.data), "file_sha256": sha256_file(args.data),
           "is_zip": zipfile.is_zipfile(args.data)}
    with open_text(args.data) as fh:
        res.update(profile(fh))
    res["python"] = sys.version.split()[0]
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print(json.dumps({k: res[k] for k in ("file_sha256", "rows", "essays", "id_column", "text_column")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
