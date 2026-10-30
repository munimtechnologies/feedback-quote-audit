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
"""fetch: download the pinned PERSUADE 2.0 training CSV and the pinned GGUF models, hash-checked

Part of feedback-quote-audit groundwork, by MV2 of Munim, Inc. Made with AI agents working in his name.

Every file is checked against its SHA-256 before use; a cached copy with the right hash is reused.
Writes paths.json (where each file ended up) for gen_probe.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request

PERSUADE_ID = "13phHyDzIsb0MHyJr6q-B-qIa9P2tM135"
PERSUADE_SHA = "f61319edd8bf16a982711ea0399fad59c05afaec05cdf0767f16a2c05c467e23"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pick_dir(candidates: list[str]) -> str:
    """The first candidate directory we can create and write to."""
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, ".write-test")
            with open(probe, "w") as fh:
                fh.write("ok")
            os.remove(probe)
            return d
        except OSError:
            continue
    raise SystemExit("no writable data directory among %s" % candidates)


def ensure(path: str, sha: str, getters: list) -> str:
    """Reuse path if its hash is right, else try each (name, get) until one gives the right bytes."""
    if os.path.isfile(path) and sha256_file(path) == sha:
        return "cached"
    part = path + ".part"
    for name, get in getters:
        try:
            get(part)
        except Exception as exc:  # noqa: BLE001 - report and try the next source
            print("fetch %s via %s failed: %s" % (os.path.basename(path), name, exc), file=sys.stderr)
            continue
        if os.path.isfile(part) and sha256_file(part) == sha:
            os.replace(part, path)
            return name
        print("fetch %s via %s: hash mismatch" % (os.path.basename(path), name), file=sys.stderr)
    raise SystemExit("could not fetch %s with sha256 %s" % (path, sha))


def url_getter(url: str):
    def get(dest: str) -> None:
        req = urllib.request.Request(url, headers={"User-Agent": "feedback-quote-audit-probe/0.1"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as fh:
            shutil.copyfileobj(resp, fh, 1 << 20)
    return get


def gdown_getter(file_id: str):
    def get(dest: str) -> None:
        subprocess.run(["gdown", "https://drive.google.com/uc?id=" + file_id, "-O", dest], check=True)
    return get


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--models", default="models.json")
    ap.add_argument("--paths-out", default="paths.json")
    args = ap.parse_args(argv)
    base = pick_dir([args.data_dir, os.path.join(os.getcwd(), "cache")])
    with open(args.models, encoding="utf-8") as fh:
        models = json.load(fh)
    csv_path = os.path.join(base, "persuade_2.0_train.csv")
    how = ensure(csv_path, PERSUADE_SHA, [
        ("gdown", gdown_getter(PERSUADE_ID)),
        ("usercontent", url_getter("https://drive.usercontent.google.com/download?id=%s&export=download&confirm=t"
                                   % PERSUADE_ID)),
    ])
    print("persuade csv:", how)
    paths = {"data_dir": base, "persuade_csv": csv_path, "models": {}}
    os.makedirs(os.path.join(base, "models"), exist_ok=True)
    for m in models:
        dest = os.path.join(base, "models", m["file"])
        url = "https://huggingface.co/%s/resolve/%s/%s" % (m["repo"], m["commit"], m["file"])
        how = ensure(dest, m["sha256"], [("huggingface", url_getter(url))])
        print("model %s: %s" % (m["name"], how))
        paths["models"][m["name"]] = dest
    with open(args.paths_out, "w", encoding="utf-8") as fh:
        json.dump(paths, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
