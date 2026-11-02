#!/usr/bin/env python3
"""Resolve a GMGN token link (or a bare CA) to {chain, ca, name, ticker, logoUrl, xUrl, sources}.

Order: GMGN API/HTML (often Cloudflare-blocked) -> DexScreener -> GeckoTerminal -> pump.fun.
Usage: gmgn_ingest.py <gmgn_url|ca> [--logo-out path]   (prints JSON to stdout)
"""
import json, re, sys, urllib.request, urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
EVM = re.compile(r"0x[0-9a-fA-F]{40}")
B58 = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")
DS_CHAIN = {"sol": "solana", "eth": "ethereum", "bsc": "bsc", "base": "base", "tron": "tron",
            "monad": "monad", "blast": "blast", "arb": "arbitrum"}
GT_CHAIN = {"sol": "solana", "eth": "eth", "bsc": "bsc", "base": "base", "tron": "tron",
            "blast": "blast", "arb": "arbitrum"}

def log(*a): print("[ingest]", *a, file=sys.stderr)

def get(url, timeout=12, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        return (data, r.headers.get("Content-Type", "")) if raw else data.decode("utf-8", "replace")

def getjson(url):
    try:
        return json.loads(get(url))
    except Exception as e:
        log("miss", url.split("?")[0], "-", type(e).__name__); return None

def parse(link):
    link = link.strip(); chain = None
    if link.startswith("http"):
        u = urllib.parse.urlparse(link)
        segs = [s for s in u.path.split("/") if s]
        if "token" in segs:
            i = segs.index("token")
            if i > 0: chain = segs[i - 1].lower()
        q = urllib.parse.parse_qs(u.query)
        chain = chain or (q.get("chain", [None])[0])
        tail = segs[-1] if segs else ""
        tail = tail.split("_")[-1]  # gmgn ref links look like /sol/token/<ref>_<CA>
        cand = tail
    else:
        cand = link
    m = EVM.search(cand)
    if m:
        return (chain or "eth"), m.group(0)
    m = B58.fullmatch(cand) or B58.search(cand)
    if m:
        ca = m.group(0)
        if not chain: chain = "tron" if ca.startswith("T") and len(ca) == 34 else "sol"
        return chain, ca
    return chain, None

def xnorm(u):
    if not u: return None
    u = u.strip()
    if re.fullmatch(r"@?\w{1,15}", u): return "https://x.com/" + u.lstrip("@")
    return re.sub(r"^https?://(www\.|mobile\.)?(twitter|x)\.com", "https://x.com", u)

def from_gmgn(chain, ca, out):
    for url in (f"https://gmgn.ai/api/v1/token_info/{chain}/{ca}",
                f"https://gmgn.ai/defi/quotation/v1/tokens/{chain}/{ca}"):
        d = getjson(url)
        if isinstance(d, dict):
            t = (d.get("data") or {}); t = t.get("token", t) if isinstance(t, dict) else {}
            if t.get("symbol"):
                out.setdefault("name", t.get("name")); out.setdefault("ticker", t.get("symbol"))
                if t.get("logo"): out.setdefault("logoUrl", t["logo"])
                tw = t.get("twitter_username") or (t.get("link") or {}).get("twitter_username")
                if tw: out.setdefault("xUrl", xnorm(tw))
                out["sources"].append("gmgn"); return

def from_dexscreener(chain, ca, out):
    d = getjson(f"https://api.dexscreener.com/tokens/v1/{DS_CHAIN.get(chain, chain)}/{ca}")
    if not d:
        s = getjson(f"https://api.dexscreener.com/latest/dex/search?q={ca}") or {}
        d = [p for p in (s.get("pairs") or []) if p.get("baseToken", {}).get("address", "").lower() == ca.lower()]
    if not d: return
    d.sort(key=lambda p: (p.get("liquidity") or {}).get("usd") or 0, reverse=True)
    p = d[0]; bt = p.get("baseToken", {})
    if bt.get("address", "").lower() != ca.lower():
        bt = p.get("quoteToken", {})
    out.setdefault("name", bt.get("name")); out.setdefault("ticker", bt.get("symbol"))
    info = next((x.get("info") for x in d if x.get("info")), None) or {}
    if info.get("imageUrl"): out.setdefault("logoUrl", info["imageUrl"])
    for s in info.get("socials") or []:
        if s.get("type") in ("twitter", "x") and s.get("url"):
            out.setdefault("xUrl", xnorm(s["url"])); break
    out["sources"].append("dexscreener")

def from_gecko(chain, ca, out):
    net = GT_CHAIN.get(chain, chain)
    d = getjson(f"https://api.geckoterminal.com/api/v2/networks/{net}/tokens/{ca}/info")
    a = ((d or {}).get("data") or {}).get("attributes") or {}
    if not a: return
    out.setdefault("name", a.get("name")); out.setdefault("ticker", a.get("symbol"))
    img = a.get("image_url")
    if img and img != "missing.png": out.setdefault("logoUrl", img)
    if a.get("twitter_handle"): out.setdefault("xUrl", xnorm(a["twitter_handle"]))
    out["sources"].append("geckoterminal")

def from_pump(chain, ca, out):
    if chain != "sol": return
    d = getjson(f"https://frontend-api-v3.pump.fun/coins/{ca}")
    if isinstance(d, dict) and d.get("symbol"):
        out.setdefault("name", d.get("name")); out.setdefault("ticker", d.get("symbol"))
        if d.get("image_uri"): out.setdefault("logoUrl", d["image_uri"])
        if d.get("twitter"): out.setdefault("xUrl", xnorm(d["twitter"]))
        out["sources"].append("pump.fun")

def ingest(link):
    chain, ca = parse(link)
    if not ca: raise SystemExit(f"could not find a contract address in: {link}")
    out = {"chain": chain, "ca": ca, "sources": []}
    for fn in (from_gmgn, from_dexscreener, from_gecko, from_pump):
        if all(out.get(k) for k in ("name", "ticker", "logoUrl", "xUrl")): break
        try: fn(chain, ca, out)
        except Exception as e: log(fn.__name__, "error", e)
    xu = out.get("xUrl") or ""
    if xu and not re.fullmatch(r"https://x\.com/(\w{1,15}|i/communities/\d+)/?", xu.split("?")[0]):
        log("listed X link is not a profile/community, ignoring:", xu)
        out["xUrlRaw"] = xu; out.pop("xUrl")
    out = {k: v for k, v in out.items() if v not in (None, "")}
    return out

def download(url, path):
    data, ctype = get(url, timeout=20, raw=True)
    with open(path, "wb") as f: f.write(data)
    return ctype

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__); sys.exit(1)
    res = ingest(args[0])
    if "--logo-out" in args and res.get("logoUrl"):
        p = args[args.index("--logo-out") + 1]
        try: res["logoContentType"] = download(res["logoUrl"], p); res["logoFile"] = p
        except Exception as e: log("logo download failed:", e)
    print(json.dumps(res, indent=2))
