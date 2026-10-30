#!/bin/sh
# Fetch the pinned checker (feedback-commons tag v0.8.0), audit 1's audit.py (commit 0d1c75a) and
# 1b's explain.py (commit d298ed9) next to speceval.py. Then wait until PLAN-5.md is public in the
# repository and identical to the copy here; if it never is, stop before any data is downloaded.
# Only then download FeedEval's speceval_dataset.json (gdown, pinned by the job) and check its SHA-256.
set -eu
python - <<'EOF'
import hashlib, json, subprocess, sys, time, urllib.request
REPO = "https://raw.githubusercontent.com/munimtechnologies/feedback-quote-audit/"
files = {
    "verbatim_quote_check.py": ("https://raw.githubusercontent.com/munimtechnologies/feedback-commons/v0.8.0/tools/verbatim_quote_check.py",
                                "d53b6b46a65024eca6ba5fa5e97d35c35c7da6d3bbe73f5362cb9e268bf15e04"),
    "audit.py": (REPO + "0d1c75a4aee4305df1dc90325462f8fb4b544ab7/audit.py",
                 "028c0d8d337f6ff07681bc7ee7c5d35b143c7cde645ae658b95f777df864965c"),
    "explain.py": (REPO + "d298ed97db6460842624d13bea82dad8c76f53ae/explain.py",
                   "9f2959daf096d4df4cc9171a9c64d163255291540551f13fb4a8ff26957d14d6"),
}
for name, (url, want) in files.items():
    data = urllib.request.urlopen(url, timeout=60).read()
    got = hashlib.sha256(data).hexdigest()
    if want and got != want:
        sys.exit("%s: SHA-256 %s, expected %s" % (name, got, want))
    open(name, "wb").write(data)
    print(name, len(data), got)

local = open("PLAN-5.md", "rb").read().replace(b"\r\n", b"\n")
for attempt in range(150):
    try:
        remote = urllib.request.urlopen(REPO + "main/PLAN-5.md?t=%d" % attempt, timeout=60).read()
        if remote.replace(b"\r\n", b"\n") == local:
            print("PLAN-5.md is public and identical (attempt %d)" % attempt)
            break
        print("PLAN-5.md is public but differs from this copy; waiting")
    except Exception as exc:
        print("PLAN-5.md not public yet:", exc)
    time.sleep(60)
else:
    sys.exit("PLAN-5.md never appeared publicly; not running")
try:
    api = "https://api.github.com/repos/munimtechnologies/feedback-quote-audit/commits?path=PLAN-5.md&per_page=1"
    c = json.load(urllib.request.urlopen(api, timeout=60))[0]
    print("PLAN-5.md commit", c["sha"][:7], c["commit"]["committer"]["date"])
except Exception as exc:
    print("could not read the PLAN-5.md commit time:", exc)

want = "3d7e88527155194cbf597a9de75ee06d45b79871a68a06bbb6ab04f089bd996b"
subprocess.run(["gdown", "https://drive.google.com/uc?id=1G71f7CFVLVV2cx908Du8jGW6k2Y0OhcF",
                "-O", "speceval_dataset.json"], check=True)
h = hashlib.sha256()
with open("speceval_dataset.json", "rb") as fh:
    for block in iter(lambda: fh.read(1 << 20), b""):
        h.update(block)
if h.hexdigest() != want:
    sys.exit("speceval_dataset.json: SHA-256 %s, expected %s" % (h.hexdigest(), want))
print("speceval_dataset.json SHA-256 as probed")
print("setup done", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
EOF
