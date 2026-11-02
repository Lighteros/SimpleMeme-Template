# SimpleMeme-Template

Bare-minimum memecoin site for ~1-minute go-lives. The page shows **only**:

1. Logo (centered)
2. Token name (+ optional ticker)
3. CA pill: one tap copies it, with "Copied!" feedback (`aria-live`)
4. X (Twitter) button

Local path: `/workspace/simple-meme-template`

## Files

| File | Purpose |
|---|---|
| `config.js` | **The only file to swap**: `window.SITE = { name, ticker, ca, xUrl, logo, bg, accent }` |
| `index.html` | Thin shell (SEO/og tags are patched by `launch.sh`) |
| `js/main.js` | Fills name, ticker, logo, CA, and X from config and wires up the copy button |
| `css/style.css` | Dark solid background, one accent color, system fonts (no web fonts) |
| `img/logo.svg` | Placeholder geometric mark |
| `favicon.ico`, `img/favicon-32.png`, `img/apple-touch-icon.png` | Favicons (rebuilt from the logo on launch) |
| `vercel.json`, `robots.txt`, `site.webmanifest` | Static deploy files |
| `launch.sh` | One-shot launcher |
| `ingest-gmgn.sh`, `tools/gmgn_ingest.py` | Turns a GMGN link into CA, name, ticker, and logo |

If `xUrl` is `"#"`, the X button shows greyed out and can't be clicked until a real URL is set.

## What Lightning/Kaede sends for a 1-minute launch

**Option A: GMGN link (fastest)**
- GMGN token URL, e.g. `https://gmgn.ai/sol/token/<CA>` (or `/eth/token/0x...`, `/bsc/...`, `/base/...`)
- Domain
- X URL (optional, but recommended: the listed X link is only used if it is a profile or community URL)

From that link, the CA is parsed. Name, ticker, and logo are resolved in this order:
GMGN API → DexScreener → GeckoTerminal → pump.fun.
The GMGN API is usually Cloudflare-blocked from servers, so DexScreener does most of the work.
A very fresh token that isn't indexed anywhere yet needs `--name`/`--logo` passed by hand.

**Option B: manual fields**
- Logo path (png/jpg/webp/gif/svg) or image URL
- Token name
- Ticker (optional)
- CA
- X URL
- Domain

Manual flags always override GMGN values.

## Run

```bash
cd /workspace/simple-meme-template

# GMGN flow
./launch.sh --gmgn "https://gmgn.ai/sol/token/<CA>" --x "https://x.com/<handle>" \
  --domain example.com --outdir /workspace/example-site --repo Lighteros/Example-Meme --deploy

# Manual flow
./launch.sh --name "Token Name" --ticker "TKN" --ca "<CA>" --x "https://x.com/<handle>" \
  --logo /path/to/logo.png --domain example.com --outdir /workspace/example-site \
  --repo Lighteros/Example-Meme --deploy

# Just inspect what a GMGN link resolves to
./ingest-gmgn.sh "https://gmgn.ai/sol/token/<CA>"
```

What `launch.sh` does:
1. Copies the site files to `--outdir`.
2. Writes `config.js`. Values are JSON-escaped, and the HTML meta is escaped too.
3. Installs the logo:
   - raster images become `img/logo.png`
   - SVGs stay `img/logo.svg`
   - animated GIFs stay `img/logo.gif`
4. Rebuilds the favicons.
5. With `--repo`, runs `git init` and commits as `Lighteros <leodev722@gmail.com>`, then `gh repo create` (private by default; add `--public` for a public repo) and pushes `main`.
6. With `--deploy`, runs `vercel link` (project name comes from the domain), `vercel --prod --yes`, and `vercel domains add <domain>`.
7. Prints the outdir, a config summary, and next steps (preview, deploy, DNS).

Running it with no flags, or with required flags missing, prints usage and exits 1.

Quick preview: `cd <outdir> && python3 -m http.server 8080`.
