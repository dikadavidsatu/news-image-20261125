#!/usr/bin/env python3
"""Draw entry.png — one image summing up the world news of Wednesday
25 November 2026, as a dense newspaper front page at 1024x1024.

Reads headlines.json in this directory and renders it with PIL. The
layout: masthead, lead story with a dateline rail, second story, a
numbers ticker, six sections in a 3x2 grid, a world-in-brief strip, and
a source footer. A seeded newsprint grain gives the paper texture and
pushes the PNG into the dense 400KB+ range of the winning editions.

Deterministic: the grain uses a fixed seed, there is no clock, no
network and no randomness anywhere else. Same input -> same pixels.
Also writes image_manifest.json so main.ts can verify the artifact.
"""
import hashlib
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W = H = 1024
M = 32                      # outer margin
CW = W - 2 * M              # content width
PAPER = (248, 243, 232)
INK = (18, 17, 15)
BODY = (54, 51, 45)
GREY = (99, 94, 84)
RULE = (199, 192, 172)
RED = (178, 24, 24)
NAVY = (21, 36, 61)
TEAL = (8, 94, 68)

DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/noto"]


def font(names, size):
    for n in names:
        for d in DIRS:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def f_title(s):
    return font(["NotoSerifDisplay-Black.ttf", "DejaVuSerif-Bold.ttf"], s)


def f_serif(s):
    return font(["DejaVuSerif-Bold.ttf", "NotoSerif-Bold.ttf"], s)


def f_sans(s):
    return font(["DejaVuSans.ttf", "NotoSans-Regular.ttf"], s)


def f_sansb(s):
    return font(["DejaVuSans-Bold.ttf", "NotoSans-Bold.ttf"], s)


def f_sanso(s):
    return font(["DejaVuSans-Oblique.ttf", "DejaVuSans.ttf"], s)


def wrap(d, text, f, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def track(text):
    return " ".join(list(text))


def grain(img, seed=20261125, amp=7, block=3):
    """Seeded block noise: reads as newsprint without blowing up the PNG
    the way per-pixel noise would."""
    rng = np.random.default_rng(seed)
    small = rng.integers(-amp, amp + 1, (H // block + 1, W // block + 1, 1))
    noise = np.repeat(np.repeat(small, block, axis=0), block, axis=1)[:H, :W]
    arr = np.clip(np.asarray(img).astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def dots(d, x0, y0, x1, y1, color, gap=11):
    """Halftone dot field, density growing left to right — the picture
    panel beside the lead story."""
    row = 0
    y = y0 + gap // 2
    while y < y1:
        x = x0 + gap // 2
        while x < x1:
            t = (x - x0) / max(1, x1 - x0)
            r = 0.5 + t * 4.4 * (0.7 + 0.3 * ((row % 3) / 2))
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)
            x += gap
        y += gap
        row += 1


def rule(d, y, weight=2):
    d.rectangle([M, y, W - M, y + weight], fill=INK)


def headline_block(d, x, y, width, story, head_size=13, deck_size=11):
    for ln in wrap(d, story["h"], f_sansb(head_size), width)[:2]:
        d.text((x, y), ln, font=f_sansb(head_size), fill=INK)
        y += head_size + 3
    for ln in wrap(d, story["d"], f_sans(deck_size), width)[:2]:
        d.text((x, y), ln, font=f_sans(deck_size), fill=BODY)
        y += deck_size + 3
    d.text((x, y), story["s"].upper(), font=f_sansb(8.5), fill=GREY)
    return y + 12


def short_item(d, x, y, width, text):
    f = f_sansb(11)
    d.text((x, y + 1), "▸", font=f, fill=RED)
    for ln in wrap(d, text, f, width - 14)[:2]:
        d.text((x + 14, y), ln, font=f, fill=INK)
        y += 13
    return y + 2


def section_block(d, x, y, width, sec):
    d.rectangle([x, y, x + width, y + 20], fill=sec["color"])
    d.text((x + 8, y + 4), sec["name"], font=f_sansb(12), fill=(255, 255, 255))
    y += 26
    y = headline_block(d, x, y, width, sec["stories"][0])
    for st in sec["stories"][1:3]:
        y = short_item(d, x, y, width, st["h"])
    return y


def main():
    data = json.load(open(os.path.join(HERE, "headlines.json")))
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    rendered = []

    # ---- masthead ----
    d.text((M, 10), "ONE IMAGE · ALL THE NEWS THAT FITS", font=f_sansb(11), fill=RED)
    title = "THE WORLD TODAY"
    tf = f_title(66)
    tw = d.textlength(title, font=tf)
    d.text(((W - tw) / 2, 20), title, font=tf, fill=INK)
    rule(d, 98, 4)
    d.text((M, 108), data["date_line"].upper(), font=f_sansb(12), fill=INK)
    mid = "ONE-IMAGE EDITION"
    mw = d.textlength(mid, font=f_sansb(12))
    d.text(((W - mw) / 2, 108), mid, font=f_sansb(12), fill=INK)
    right = "WIRE REPORTS 24–25 NOV · 05:00 UTC"
    rw = d.textlength(right, font=f_sans(10.5))
    d.text((W - M - rw, 109), right, font=f_sans(10.5), fill=GREY)
    rule(d, 128, 2)

    # ---- lead story (left) + dateline rail (right) ----
    y = 140
    lead = data["lead"]
    lw = 592
    d.text((M, y), track(lead["kicker"]), font=f_sansb(12), fill=RED)
    y += 21
    for ln in wrap(d, lead["headline"], f_serif(33), lw):
        d.text((M, y), ln, font=f_serif(33), fill=INK)
        y += 38
    y += 3
    for ln in wrap(d, lead["deck"], f_sans(13), lw):
        d.text((M, y), ln, font=f_sans(13), fill=BODY)
        y += 16.5
    d.text((M, y + 2), lead["source"].upper(), font=f_sansb(9.5), fill=GREY)
    rendered.append(lead["headline"])
    lead_bottom = y + 16

    rx0, ry0, rx1 = 660, 140, W - M
    d.rectangle([rx0, ry0, rx1, ry0 + 23], fill=NAVY)
    d.text((rx0 + 9, ry0 + 5), "THE DAY'S DATELINES", font=f_sansb(11.5), fill=(255, 255, 255))
    dy = ry0 + 32
    for city, note in data["datelines"]:
        d.ellipse([rx0 + 2, dy + 4, rx0 + 9, dy + 11], fill=RED)
        d.text((rx0 + 16, dy), city, font=f_sansb(11.5), fill=INK)
        cw2 = d.textlength(city, font=f_sansb(11.5))
        d.text((rx0 + 21 + cw2, dy + 1), "— " + note, font=f_sans(10.5), fill=BODY)
        dy += 18.5
    dots(d, rx0, dy + 6, rx1, dy + 44, NAVY)

    # ---- second story ----
    y2 = max(lead_bottom, dy + 52) + 12
    rule(d, y2 - 8, 2)
    s2 = data["second"]
    d.text((M, y2), track(s2["kicker"]), font=f_sansb(11.5), fill=RED)
    yy = y2 + 19
    for ln in wrap(d, s2["headline"], f_serif(24), CW):
        d.text((M, yy), ln, font=f_serif(24), fill=INK)
        yy += 30
    for ln in wrap(d, s2["deck"], f_sans(13), CW)[:2]:
        d.text((M, yy), ln, font=f_sans(13), fill=BODY)
        yy += 16.5
    d.text((M, yy + 1), s2["source"].upper(), font=f_sansb(9), fill=GREY)
    rendered.append(s2["headline"])
    yy += 10

    # ---- numbers ticker ----
    ny = yy + 6
    rule(d, ny, 2)
    nums = "  ·  ".join(f"{a} {b}" for a, b in data["numbers"])
    ty = ny + 7
    for ln in wrap(d, "THE DAY IN NUMBERS — " + nums, f_sansb(11.5), CW)[:2]:
        d.text((M, ty), ln, font=f_sansb(11.5), fill=NAVY)
        ty += 14
    rule(d, ty + 2, 2)

    # ---- sections grid, 3 columns x 2 rows ----
    gy = ty + 15
    col_w = (CW - 28) // 3
    xs = [M, M + col_w + 14, M + 2 * (col_w + 14)]
    rows = [["WORLD", "US & POLITICS", "BUSINESS & TECH"],
            ["SCIENCE & HEALTH", "SPORT", "CULTURE & ODDS"]]
    secs = {s["name"]: s for s in data["sections"]}
    for r, row in enumerate(rows):
        ends = []
        for i, name in enumerate(row):
            ends.append(section_block(d, xs[i], gy, col_w, secs[name]))
            rendered.extend(st["h"] for st in secs[name]["stories"][:3])
        gy = max(ends) + (8 if r == 0 else 6)
        if r == 0:
            d.rectangle([M, gy - 8, W - M, gy - 7], fill=RULE)

    # ---- world in brief ----
    by = gy + 2
    d.text((M, by), track("AROUND THE WORLD IN BRIEF"), font=f_sansb(11), fill=RED)
    by += 17
    briefs = data["briefs"][:8]
    bw = (CW - 3 * 12) // 4
    for i, (tag, text) in enumerate(briefs):
        bx = M + (i % 4) * (bw + 12)
        byy = by + (i // 4) * 40
        d.text((bx, byy), tag, font=f_sansb(10), fill=NAVY)
        for j, ln in enumerate(wrap(d, text, f_sans(10), bw)[:2]):
            d.text((bx, byy + 13 + j * 12.5), ln, font=f_sans(10), fill=BODY)
        rendered.append(f"{tag}: {text}")
    bottom = by + 2 * 40

    # ---- footer ----
    fy = max(bottom + 8, 950)
    rule(d, fy, 2)
    for j, ln in enumerate(wrap(d, "SOURCES: " + data["sources"], f_sans(9.5), CW)[:2]):
        d.text((M, fy + 7 + j * 12), ln, font=f_sans(9.5), fill=GREY)
    foot2 = "One image, drawn by an AI agent from the day's wire reports · Wednesday 25 November 2026 · Headlines as reported by the outlets named"
    d.text((M, fy + 33), foot2, font=f_sanso(9.5), fill=GREY)

    img = grain(img)
    out = os.path.join(HERE, "entry.png")
    img.save(out, optimize=True)
    digest = hashlib.sha256(open(out, "rb").read()).hexdigest()
    manifest = {
        "file": "entry.png",
        "width": W,
        "height": H,
        "bytes": os.path.getsize(out),
        "sha256": digest,
        "date": "2026-11-25",
        "items_rendered": len(rendered),
        "headlines": rendered,
    }
    with open(os.path.join(HERE, "image_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    print("wrote", out, manifest["bytes"], "bytes; items:", len(rendered),
          "; briefs bottom:", bottom, "; footer:", fy)


if __name__ == "__main__":
    main()
