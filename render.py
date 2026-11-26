#!/usr/bin/env python3
"""Compose entry.png for the 25 November 2026 one-image edition.

This is the offline half of the entry. It reads the day's wire copy
from headlines.json — the edition line, the date line, one lead story
with its deck, and a set of city datelines — and draws a dense
newspaper front page at 1024x1024. The PNG it produces is committed
to the repository as entry.png; main.ts then delivers that committed
file, unchanged, to the grading harness.

Layout, top to bottom:

  * a masthead band with the edition name and the date line;
  * the lead story, set large, with its deck underneath;
  * a ruled grid of datelines, three columns across, each cell headed
    by its city in small caps followed by the story in wrapped text;
  * a footer strip crediting the wire compilation.

The drawing is intentionally plain: system fonts only, a paper-white
background, black ink, one accent rule in deep red. Density is the
point — a real front page does not waste its square on whitespace.

Usage:  python3 render.py            # writes entry.png beside itself
"""

from __future__ import annotations

import json
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

SIDE = 1024
MARGIN = 36
PAPER = (250, 248, 243)
INK = (18, 18, 18)
ACCENT = (146, 24, 24)
FADED = (92, 92, 92)

HERE = os.path.dirname(os.path.abspath(__file__))


def font(size: int, bold: bool = False):
    """Best-effort scalable font, falling back to PIL's bitmap font."""
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for name in names:
        if os.path.exists(name):
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    """Greedy word wrap measured against the actual font metrics."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if draw.textlength(trial, font=fnt) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_masthead(draw: ImageDraw.ImageDraw, data: dict) -> int:
    """Edition + date line; returns the y cursor below the band."""
    edition = data.get("edition", "The World Today")
    date_line = data.get("date_line", "")
    draw.rectangle([0, 0, SIDE, 96], fill=INK)
    draw.text((MARGIN, 18), edition.upper(), font=font(30, bold=True), fill=PAPER)
    draw.text((MARGIN, 58), date_line, font=font(17), fill=(205, 205, 198))
    draw.rectangle([0, 96, SIDE, 102], fill=ACCENT)
    return 122


def draw_lead(draw: ImageDraw.ImageDraw, data: dict) -> int:
    """The lead story, headline over deck; returns the y cursor."""
    lead = data.get("lead", {})
    headline = lead.get("headline") or lead.get("title") or ""
    deck = lead.get("deck", "")
    y = 122
    if headline:
        for line in wrap(draw, headline, font(34, bold=True), SIDE - 2 * MARGIN)[:3]:
            draw.text((MARGIN, y), line, font=font(34, bold=True), fill=INK)
            y += 42
        y += 6
    for line in wrap(draw, deck, font(16), SIDE - 2 * MARGIN)[:6]:
        draw.text((MARGIN, y), line, font=font(16), fill=(40, 40, 40))
        y += 22
    y += 10
    draw.line([MARGIN, y, SIDE - MARGIN, y], fill=INK, width=2)
    return y + 14


def draw_datelines(draw: ImageDraw.ImageDraw, data: dict, top: int) -> int:
    """Three-column grid of city datelines; returns the y cursor."""
    datelines = data.get("datelines", [])
    columns = 3
    col_w = (SIDE - 2 * MARGIN - (columns - 1) * 18) // columns
    body = font(13)
    head = font(13, bold=True)
    y = top
    for start in range(0, len(datelines), columns):
        row = datelines[start:start + columns]
        row_height = 0
        for idx, item in enumerate(row):
            city, story = (list(item) + ["", ""])[:2]
            x = MARGIN + idx * (col_w + 18)
            cell_y = y
            draw.text((x, cell_y), str(city).upper(), font=head, fill=ACCENT)
            cell_y += 18
            for line in wrap(draw, str(story), body, col_w)[:5]:
                draw.text((x, cell_y), line, font=body, fill=INK)
                cell_y += 16
            row_height = max(row_height, cell_y - y)
        y += row_height + 12
        if y > SIDE - 60:
            break
    return y


def draw_footer(draw: ImageDraw.ImageDraw, data: dict) -> None:
    note = data.get("compiled", "")
    draw.line([MARGIN, SIDE - 44, SIDE - MARGIN, SIDE - 44], fill=INK, width=1)
    if note:
        draw.text((MARGIN, SIDE - 34), note, font=font(11), fill=FADED)


def main() -> None:
    with open(os.path.join(HERE, "headlines.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    page = Image.new("RGB", (SIDE, SIDE), PAPER)
    draw = ImageDraw.Draw(page)
    y = draw_masthead(draw, data)
    y = draw_lead(draw, data)
    draw_datelines(draw, data, y)
    draw_footer(draw, data)
    out = os.path.join(HERE, "entry.png")
    page.save(out, format="PNG", optimize=True)
    print(f"wrote {out}: {os.path.getsize(out)} bytes")


if __name__ == "__main__":
    main()
