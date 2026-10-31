#!/bin/sh
# Fetch what audit7 runs on: audit6.py exactly as audit 6 ran it (checked against the SHA-256 its runs
# recorded), and fetch.py and models.json from the audit-6 groundwork commit (80a5cdf). Then wait until
# PLAN-7.md and audit7.py are public in the repository and identical to the copies here; if they never are,
# stop before any data or model is touched. fetch.py then downloads and hash-checks PERSUADE 2.0 and the
# models (cached under the persuade-2 data key) in a separate setup step.
set -eu
python - <<'EOF'
import hashlib, json, sys, time, urllib.request
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

names = ("PLAN-7.md", "audit7.py")
local = {n: open(n, "rb").read().replace(b"\r\n", b"\n") for n in names}
for attempt in range(180):
    waiting = []
    for n in names:
        try:
            remote = get(REPO + "main/%s?t=%d" % (n, attempt))
            if remote.replace(b"\r\n", b"\n") != local[n]:
                waiting.append(n + " differs")
        except Exception as exc:
            waiting.append("%s not public (%s)" % (n, exc))
    if not waiting:
        print("PLAN-7.md and audit7.py are public and identical (attempt %d)" % attempt)
        break
    print("waiting:", "; ".join(waiting))
    time.sleep(60)
else:
    sys.exit("PLAN-7.md / audit7.py never appeared publicly as here; not running")
for n in names:
    print(n, "sha256 (LF)", hashlib.sha256(local[n]).hexdigest())
try:
    api = "https://api.github.com/repos/munimtechnologies/feedback-quote-audit/commits?path=PLAN-7.md&per_page=1"
    c = json.load(urllib.request.urlopen(api, timeout=60))[0]
    print("PLAN-7.md commit", c["sha"][:7], c["commit"]["committer"]["date"])
except Exception as exc:
    print("could not read the PLAN-7.md commit time:", exc)
print("setup done", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
EOF
