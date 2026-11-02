#!/usr/bin/env python3
"""apply_config.py <site_dir> <fields.json>
fields: name, ticker, ca, xUrl, bg, accent, logoSrc (local file to install), domain
Writes config.js (JSON-escaped), installs logo, patches <title>/meta/manifest, rebuilds favicons."""
import json, os, re, shutil, subprocess, sys, html
site, fields = sys.argv[1], json.load(open(sys.argv[2]))
here = os.path.dirname(os.path.abspath(__file__))

name = (fields.get("name") or "TOKEN").strip()
ticker = (fields.get("ticker") or "").strip()
if ticker and not ticker.startswith("$"): ticker = "$" + ticker
ca = (fields.get("ca") or "TBA").strip()
x = (fields.get("xUrl") or "#").strip()
if x != "#" and not re.match(r"^https://", x): raise SystemExit(f"--x must be an https:// URL, got {x!r}")
bg = fields.get("bg") or "#0a0a0a"; accent = fields.get("accent") or "#7CFF6B"
for c in (bg, accent):
    if not re.fullmatch(r"#[0-9a-fA-F]{3,8}", c): raise SystemExit(f"bad color {c!r}")

logo_rel = "img/logo.svg"; raster = None
src = fields.get("logoSrc")
if src:
    img = os.path.join(site, "img")
    if src.lower().endswith(".svg") or open(src, "rb").read(256).lstrip().startswith((b"<svg", b"<?xml")):
        shutil.copyfile(src, os.path.join(img, "logo.svg")); logo_rel = "img/logo.svg"
    else:
        from PIL import Image
        im = Image.open(src)
        if getattr(im, "is_animated", False) and im.format == "GIF":
            shutil.copyfile(src, os.path.join(img, "logo.gif")); logo_rel = "img/logo.gif"
        else:
            im.convert("RGBA").save(os.path.join(img, "logo.png"), optimize=True); logo_rel = "img/logo.png"
        raster = os.path.join(site, logo_rel)

cfg = {"name": name, "ticker": ticker, "ca": ca, "xUrl": x, "logo": logo_rel, "bg": bg, "accent": accent}
body = ",\n".join(f"  {k}: {json.dumps(v, ensure_ascii=False)}" for k, v in cfg.items())
body = body.replace("</", "<\\/")
open(os.path.join(site, "config.js"), "w").write(
    "/* ==== THE ONLY FILE YOU EDIT FOR A LAUNCH ==== */\nwindow.SITE = {\n" + body + "\n};\n")

title = f"{name} ({ticker})" if ticker else name
p = os.path.join(site, "index.html"); h = open(p).read()
e = lambda s: html.escape(s, quote=True)
domain = (fields.get("domain") or "").strip()
og_img = f"https://{domain}/{logo_rel}" if domain else logo_rel
h = re.sub(r"<title>.*?</title>", lambda m: f"<title>{e(title)}</title>", h, count=1)
h = re.sub(r'(<meta name="description" content=")[^"]*', lambda m: m.group(1) + e(f"{title} - CA: {ca}"), h, count=1)
h = re.sub(r'(<meta property="og:title" content=")[^"]*', lambda m: m.group(1) + e(title), h, count=1)
h = re.sub(r'(<meta property="og:image" content=")[^"]*', lambda m: m.group(1) + e(og_img), h, count=1)
h = re.sub(r'(<meta name="theme-color" content=")[^"]*', lambda m: m.group(1) + bg, h, count=1)
h = re.sub(r'(<img id="logo"[^>]*?src=")[^"]*', lambda m: m.group(1) + logo_rel, h, count=1)
h = re.sub(r'(<img id="logo"[^>]*?alt=")[^"]*', lambda m: m.group(1) + e(name + " logo"), h, count=1)
h = re.sub(r'(<h1 id="name" class="name">)[^<]*', lambda m: m.group(1) + e(name), h, count=1)
h = re.sub(r'(<p id="ticker" class="ticker">)[^<]*', lambda m: m.group(1) + e(ticker), h, count=1)
h = re.sub(r'(<code id="ca-text" class="ca-text">)[^<]*', lambda m: m.group(1) + e(ca), h, count=1)
open(p, "w").write(h)

mp = os.path.join(site, "site.webmanifest"); m = json.load(open(mp))
m.update(name=title, short_name=name[:12], theme_color=bg, background_color=bg)
json.dump(m, open(mp, "w"))

subprocess.run([sys.executable, os.path.join(here, "mkfavicon.py"), site] + ([raster] if raster else []), check=False, stdout=sys.stderr)
print(json.dumps(cfg, indent=2, ensure_ascii=False))
