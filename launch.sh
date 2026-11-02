#!/usr/bin/env bash
# launch.sh - stamp the simple meme template into a ready-to-deploy site in ~1 minute.
set -euo pipefail
TPL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GH="$(command -v gh || echo /usr/local/bin/gh)"

usage() {
cat <<'U'
Usage (GMGN link - fastest):
  ./launch.sh --gmgn "https://gmgn.ai/sol/token/<CA>" [--x "https://x.com/<handle>"] \
              --domain example.com --outdir /workspace/example-site \
              [--repo Lighteros/Example-Meme] [--deploy]

Usage (manual fields):
  ./launch.sh --name "Token Name" --ca "<CA>" --logo /path/to/logo.png \
              [--ticker "TKN"] [--x "https://x.com/<handle>"] \
              --domain example.com --outdir /workspace/example-site \
              [--repo Lighteros/Example-Meme] [--deploy]

Required: --outdir, --domain, and EITHER --gmgn OR (--name + --ca + --logo).
Manual flags always override GMGN-ingested values (e.g. --x, --name, --logo).

Options:
  --gmgn URL       GMGN token link (or bare CA). Pulls CA, name, ticker, logo (+X if listed)
                   via GMGN -> DexScreener -> GeckoTerminal -> pump.fun fallbacks.
  --name STR       Token name shown as the headline
  --ticker STR     Ticker ("$" added if missing). Optional.
  --ca STR         Contract address (Solana mint / 0x...)
  --x URL          X profile URL (https://x.com/...). Optional; button shows greyed until set.
  --logo PATH      Local logo file (png/jpg/webp/gif/svg) or https URL
  --domain HOST    Production domain (used for og:image + Vercel project name)
  --outdir DIR     Where the new site is written (must not exist, or be empty)
  --bg HEX         Background color (default #0a0a0a)
  --accent HEX     Accent color (default #7CFF6B)
  --repo O/NAME    git init + commit + gh repo create (private by default) + push
  --public         Make the --repo public
  --deploy         Run `vercel --prod --yes` and attach --domain
  -h, --help       Show this help
U
}

NAME="" TICKER="" CA="" XURL="" LOGO="" DOMAIN="" OUTDIR="" REPO="" GMGN="" BG="" ACCENT=""
DEPLOY=0 PUBLIC=0
[[ $# -eq 0 ]] && { usage; exit 1; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="${2-}"; shift 2;;
    --ticker) TICKER="${2-}"; shift 2;;
    --ca) CA="${2-}"; shift 2;;
    --x) XURL="${2-}"; shift 2;;
    --logo) LOGO="${2-}"; shift 2;;
    --domain) DOMAIN="${2-}"; shift 2;;
    --outdir) OUTDIR="${2-}"; shift 2;;
    --repo) REPO="${2-}"; shift 2;;
    --gmgn) GMGN="${2-}"; shift 2;;
    --bg) BG="${2-}"; shift 2;;
    --accent) ACCENT="${2-}"; shift 2;;
    --deploy) DEPLOY=1; shift;;
    --public) PUBLIC=1; shift;;
    -h|--help) usage; exit 1;;
    *) echo "Unknown flag: $1" >&2; usage; exit 1;;
  esac
done

missing=()
[[ -z "$OUTDIR" ]] && missing+=(--outdir)
[[ -z "$DOMAIN" ]] && missing+=(--domain)
if [[ -z "$GMGN" ]]; then
  [[ -z "$NAME" ]] && missing+=(--name)
  [[ -z "$CA" ]] && missing+=(--ca)
  [[ -z "$LOGO" ]] && missing+=(--logo)
fi
if (( ${#missing[@]} )); then echo "Missing: ${missing[*]}" >&2; usage; exit 1; fi
if [[ -e "$OUTDIR" && -n "$(ls -A "$OUTDIR" 2>/dev/null)" ]]; then echo "outdir not empty: $OUTDIR" >&2; exit 1; fi

T0=$(date +%s)
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

# 1) GMGN ingest (manual flags win)
if [[ -n "$GMGN" ]]; then
  echo "==> Ingesting $GMGN"
  python3 "$TPL/tools/gmgn_ingest.py" "$GMGN" --logo-out "$WORK/ingest_logo" > "$WORK/ingest.json"
  get() { python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2],""))' "$WORK/ingest.json" "$1"; }
  [[ -z "$CA" ]] && CA="$(get ca)"
  [[ -z "$NAME" ]] && NAME="$(get name)"
  [[ -z "$TICKER" ]] && TICKER="$(get ticker)"
  [[ -z "$XURL" ]] && XURL="$(get xUrl)"
  [[ -z "$LOGO" && -s "$WORK/ingest_logo" ]] && LOGO="$WORK/ingest_logo"
  echo "    sources: $(get sources)"
  XR="$(get xUrlRaw)"; [[ -n "$XR" ]] && echo "    note: listed X link was not a profile, ignored: $XR (pass --x)"
  [[ -z "$NAME" ]] && { echo "Could not resolve token name from GMGN link; pass --name" >&2; exit 1; }
  [[ -z "$LOGO" ]] && echo "    WARN: no logo found; placeholder logo kept (pass --logo to set one)" >&2
fi

# remote logo URL -> download
if [[ "$LOGO" =~ ^https?:// ]]; then
  curl -fsSL -A "Mozilla/5.0" "$LOGO" -o "$WORK/remote_logo"; LOGO="$WORK/remote_logo"
fi
[[ -n "$LOGO" && ! -f "$LOGO" ]] && { echo "logo not found: $LOGO" >&2; exit 1; }

# 2) copy template (site files only)
mkdir -p "$OUTDIR"
for f in index.html config.js css js img favicon.ico robots.txt site.webmanifest vercel.json; do
  cp -R "$TPL/$f" "$OUTDIR/"
done

# 3) write config.js + patch meta + logo + favicons (values JSON-escaped in python)
export L_NAME="$NAME" L_TICKER="$TICKER" L_CA="$CA" L_X="$XURL" L_LOGO="$LOGO" L_DOMAIN="$DOMAIN" L_BG="$BG" L_ACCENT="$ACCENT"
python3 - "$WORK/fields.json" <<'PY2'
import json, os, sys
e = os.environ.get
json.dump({k: v for k, v in {
  "name": e("L_NAME"), "ticker": e("L_TICKER"), "ca": e("L_CA"), "xUrl": e("L_X") or "#",
  "logoSrc": e("L_LOGO"), "domain": e("L_DOMAIN"), "bg": e("L_BG"), "accent": e("L_ACCENT")}.items() if v},
  open(sys.argv[1], "w"))
PY2
echo "==> Writing config"
python3 "$TPL/tools/apply_config.py" "$OUTDIR" "$WORK/fields.json" > "$WORK/cfg.out"

SLUG="$(echo "${DOMAIN:-$TICKER}" | tr '[:upper:]' '[:lower:]' | sed -E 's/^www\.//; s/[^a-z0-9]+/-/g; s/^-+|-+$//g' | cut -c1-52)"
[[ -z "$SLUG" ]] && SLUG="meme-site-$(date +%s)"

# 4) git + GitHub
REPO_URL=""
if [[ -n "$REPO" ]]; then
  echo "==> git + GitHub ($REPO)"
  printf '.vercel\n.DS_Store\n' > "$OUTDIR/.gitignore"
  ( cd "$OUTDIR"
    git init -q -b main
    git add -A
    git -c user.name="Lighteros" -c user.email="leodev722@gmail.com" \
        commit -q -m "feat: launch ${NAME}${TICKER:+ (${TICKER})} site" --author="Lighteros <leodev722@gmail.com>"
    "$GH" auth setup-git >/dev/null 2>&1 || true
    VIS="--private"; (( PUBLIC )) && VIS="--public"
    "$GH" repo create "$REPO" $VIS --source . --remote origin --push ) 
  REPO_URL="https://github.com/$REPO"
fi

# 5) Vercel
LIVE=""
if (( DEPLOY )); then
  echo "==> Vercel deploy (project: $SLUG)"
  ( cd "$OUTDIR"
    vercel link --yes --project "$SLUG" >/dev/null
    vercel --prod --yes | tee "$WORK/vercel.out"
    [[ -n "$DOMAIN" ]] && vercel domains add "$DOMAIN" "$SLUG" || true )
  LIVE="$(grep -Eo 'https://[^ ]+\.vercel\.app' "$WORK/vercel.out" | tail -1 || true)"
fi

# 6) summary
echo
echo "================ DONE in $(( $(date +%s) - T0 ))s ================"
echo "outdir : $OUTDIR"
echo "config :"; sed 's/^/  /' "$WORK/cfg.out"
[[ -n "$REPO_URL" ]] && echo "repo   : $REPO_URL"
[[ -n "$LIVE" ]] && echo "vercel : $LIVE"
echo "domain : ${DOMAIN}"
echo
echo "Next steps:"
echo "  - Preview: cd \"$OUTDIR\" && python3 -m http.server 8080  ->  http://localhost:8080"
[[ -z "$XURL" || "$XURL" == "#" ]] && echo "  - X link not set: edit xUrl in $OUTDIR/config.js (button is greyed until then)"
(( DEPLOY )) || echo "  - Deploy: cd \"$OUTDIR\" && vercel link --yes --project $SLUG && vercel --prod --yes && vercel domains add $DOMAIN $SLUG"
echo "  - DNS for $DOMAIN: A @ 76.76.21.21 and CNAME www cname.vercel-dns.com (or Vercel nameservers)"
