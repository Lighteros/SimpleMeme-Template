#!/usr/bin/env python3
"""mkfavicon.py <site_dir> [logo_raster]  -> favicon.ico, img/favicon-32.png, img/apple-touch-icon.png
Without a raster logo it draws the placeholder geometric mark."""
import sys, os
from PIL import Image, ImageDraw
site = sys.argv[1]; src = sys.argv[2] if len(sys.argv) > 2 else None
def mark(n=512):
    im = Image.new("RGBA", (n, n), "#141414"); d = ImageDraw.Draw(im); s = n / 200
    d.ellipse([38*s, 38*s, 162*s, 162*s], outline="#7CFF6B", width=int(14*s))
    d.polygon([(100*s, 52*s), (142*s, 124*s), (58*s, 124*s)], fill="#7CFF6B")
    d.ellipse([90*s, 94*s, 110*s, 114*s], fill="#141414"); return im
if src:
    im = Image.open(src); im.seek(0); im = im.convert("RGBA")
    w, h = im.size; m = min(w, h); im = im.crop(((w-m)//2, (h-m)//2, (w-m)//2+m, (h-m)//2+m))
else:
    im = mark()
os.makedirs(os.path.join(site, "img"), exist_ok=True)
im.resize((180, 180), Image.LANCZOS).save(os.path.join(site, "img/apple-touch-icon.png"))
im.resize((32, 32), Image.LANCZOS).save(os.path.join(site, "img/favicon-32.png"))
im.resize((64, 64), Image.LANCZOS).save(os.path.join(site, "favicon.ico"), sizes=[(16,16),(32,32),(48,48)])
print("favicons written")
