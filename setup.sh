#!/bin/sh
# Fetch the pinned checker (feedback-commons tag v0.8.0) next to audit.py.
set -eu
python - <<'EOF'
import hashlib, urllib.request
url = "https://raw.githubusercontent.com/munimtechnologies/feedback-commons/v0.8.0/tools/verbatim_quote_check.py"
data = urllib.request.urlopen(url, timeout=60).read()
open("verbatim_quote_check.py", "wb").write(data)
print("verbatim_quote_check.py", len(data), hashlib.sha256(data).hexdigest())
EOF
