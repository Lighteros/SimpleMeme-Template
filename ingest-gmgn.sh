#!/usr/bin/env bash
# ingest-gmgn.sh <gmgn_url|CA> [logo_out]  - print resolved token JSON (CA, name, ticker, logoUrl, xUrl)
set -euo pipefail
[[ $# -lt 1 || "$1" == -h || "$1" == --help ]] && { echo "Usage: ./ingest-gmgn.sh \"https://gmgn.ai/sol/token/<CA>\" [/path/logo_out]"; exit 1; }
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${2-}" ]]; then python3 "$D/tools/gmgn_ingest.py" "$1" --logo-out "$2"; else python3 "$D/tools/gmgn_ingest.py" "$1"; fi
