#!/bin/sh
# Fetch the groundwork fetch.py and models.json from the commit that published them (80a5cdf). Then wait
# until PLAN-6.md and audit6.py are public in the repository and identical to the copies here; if they never
# are, stop before any data or model is touched. fetch.py then downloads and hash-checks the PERSUADE 2.0
# CSV and both GGUF models (a separate setup step in the job).
set -eu
python - <<'EOF'
import hashlib, json, sys, time, urllib.request
REPO = "https://raw.githubusercontent.com/munimtechnologies/feedback-quote-audit/"
PIN = "80a5cdf8b7fbcd816dbe552d799b89a6259d4f21"
for name in ("fetch.py", "models.json"):
    data = urllib.request.urlopen(REPO + PIN + "/groundwork/audit-6/" + name, timeout=60).read()
    open(name, "wb").write(data)
    print(name, len(data), hashlib.sha256(data).hexdigest(), "(groundwork commit %s)" % PIN[:7])

names = ("PLAN-6.md", "audit6.py")
local = {n: open(n, "rb").read().replace(b"\r\n", b"\n") for n in names}
for attempt in range(150):
    waiting = []
    for n in names:
        try:
            remote = urllib.request.urlopen(REPO + "main/%s?t=%d" % (n, attempt), timeout=60).read()
            if remote.replace(b"\r\n", b"\n") != local[n]:
                waiting.append(n + " differs")
        except Exception as exc:
            waiting.append("%s not public (%s)" % (n, exc))
    if not waiting:
        print("PLAN-6.md and audit6.py are public and identical (attempt %d)" % attempt)
        break
    print("waiting:", "; ".join(waiting))
    time.sleep(60)
else:
    sys.exit("PLAN-6.md / audit6.py never appeared publicly as here; not running")
for n in names:
    print(n, "sha256 (LF)", hashlib.sha256(local[n]).hexdigest())
try:
    api = "https://api.github.com/repos/munimtechnologies/feedback-quote-audit/commits?path=PLAN-6.md&per_page=1"
    c = json.load(urllib.request.urlopen(api, timeout=60))[0]
    print("PLAN-6.md commit", c["sha"][:7], c["commit"]["committer"]["date"])
except Exception as exc:
    print("could not read the PLAN-6.md commit time:", exc)
print("setup done", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
EOF
