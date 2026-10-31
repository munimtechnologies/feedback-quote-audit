#!/bin/sh
# Fetch what probe7 re-runs: audit6.py exactly as audit 6 ran it (checked against the SHA-256 its runs
# recorded), fetch.py and models.json from the audit-6 groundwork commit (80a5cdf), and audit 6's published
# Qwen counts (audit6-qwen.json). fetch.py then downloads and hash-checks PERSUADE 2.0 and the models (cached
# under the persuade-2 data key) in a separate setup step.
set -eu
python - <<'EOF'
import hashlib, json, sys, urllib.request
REPO = "https://raw.githubusercontent.com/munimtechnologies/feedback-quote-audit/"
PIN = "80a5cdf8b7fbcd816dbe552d799b89a6259d4f21"
AUDIT6_SHA_LF = "bb582d88a058c02a30ff06fedbea4b0b97ea48a51b279f9328d9fd23379f63fb"


def get(url):
    return urllib.request.urlopen(url, timeout=60).read()


for name in ("fetch.py", "models.json"):
    data = get(REPO + PIN + "/groundwork/audit-6/" + name)
    open(name, "wb").write(data)
    print(name, len(data), hashlib.sha256(data).hexdigest(), "(groundwork commit %s)" % PIN[:7])

data = get(REPO + "main/audit6.py")
sha = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
if sha != AUDIT6_SHA_LF:
    sys.exit("audit6.py on main is not the one audit 6 ran (sha256 %s)" % sha)
open("audit6.py", "wb").write(data)
print("audit6.py sha256 (LF)", sha)

data = get(REPO + "main/audit6-qwen.json")
old = json.loads(data)
if old.get("audit6_sha256_lf") != AUDIT6_SHA_LF or len(old.get("records", [])) != 146:
    sys.exit("audit6-qwen.json on main is not audit 6's Qwen run")
open("audit6-qwen.json", "wb").write(data)
print("audit6-qwen.json", len(data), hashlib.sha256(data).hexdigest(), "records", len(old["records"]))
EOF
