#!/usr/bin/env python3
"""Collect theme data and preview media from local theme checkouts.

Usage: python3 source/collect.py <dir-with-checkouts> [<dir> ...]

Each directory is searched for <slug>/repo/<slug>.json or
t3code-theme-<slug>/<slug>.json. Writes themes.json, assets/posters/<slug>.webp
and assets/loops/<slug>.mp4. Existing loops are kept; delete one to re-encode.
"""
import html
import json
import pathlib
import re
import subprocess
import sys

from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
OWNER = "joshsaintjacque"

# slug, mood, what happens while the agent works
ROSTER = [
    ("blueprint", "creative", "A pen plotter inks a part in the margin"),
    ("misprint", "energetic", "Two ink plates slip out of register"),
    ("departures", "energetic", "A split-flap board rattles to BOARDING"),
    ("reel-to-reel", "energetic", "VU needles bounce and the reels turn"),
    ("squiggle", "energetic", "Memphis confetti bobs and tumbles"),
    ("molten", "energetic", "Wax lamps heat up and rise"),
    ("marquee", "energetic", "House lights dim and the bulbs chase"),
    ("tilt", "energetic", "Pinball lights run and the score counts up"),
    ("observatory", "calm", "Star plates draw while a reticle tracks"),
    ("washi", "calm", "Ink blooms, and a seal stamps at the end"),
    ("sandgarden", "calm", "A rake draws furrows around the stones"),
    ("aurora", "calm", "Curtains of light swell overhead"),
    ("folio", "calm", "E-paper dots fill in whole steps"),
    ("fogbank", "calm", "A lighthouse beam sweeps through mist"),
    ("rainglass", "calm", "Rain thickens on a night window"),
    ("darkroom", "creative", "A print develops under the safelight"),
    ("agar", "creative", "Colonies grow on culture plates"),
    ("clerestory", "creative", "Stained glass kindles and light shafts cross"),
    ("primary", "creative", "Bauhaus shapes recompose"),
    ("phosphor", "creative", "An oscilloscope traces Lissajous figures"),
    ("contour", "creative", "Map contours shift, and a pin drops at the end"),
]


# Blueprint's recording has extra mock projects in its sidebar. Cover them with
# a clean strip of the same sidebar: (x, y, width, height, source_y) at 1600px.
SIDEBAR_COVER = {"blueprint": (2, 222, 250, 205, 440)}


def find_repo(slug, roots):
    for root in roots:
        for candidate in (root / slug / "repo", root / f"t3code-theme-{slug}"):
            if (candidate / f"{slug}.json").exists():
                return candidate
    sys.exit(f"no checkout found for {slug}")


def first(repo, *names):
    for name in names:
        if (repo / "assets" / name).exists():
            return repo / "assets" / name
    sys.exit(f"{repo.name}: none of {names}")


def run(*args):
    subprocess.run(args, check=True, stdin=subprocess.DEVNULL)


def main():
    roots = [pathlib.Path(p).resolve() for p in sys.argv[1:]]
    if not roots:
        sys.exit(__doc__)
    (ROOT / "assets/posters").mkdir(parents=True, exist_ok=True)
    (ROOT / "assets/loops").mkdir(parents=True, exist_ok=True)

    themes = []
    for slug, mood, line in ROSTER:
        repo = find_repo(slug, roots)
        theme = json.loads((repo / f"{slug}.json").read_text())
        colors = theme["colors"]
        page = (repo / "index.html").read_text()
        description = re.search(r'<meta name="description" content="([^"]*)"', page)
        themes.append({
            "slug": slug,
            "name": theme["name"],
            "appearance": theme["appearance"],
            "mood": mood,
            "line": line,
            "description": html.unescape(description.group(1)),
            "site": f"https://{OWNER}.github.io/t3code-theme-{slug}/",
            "repo": f"https://github.com/{OWNER}/t3code-theme-{slug}",
            "swatches": [colors[k] for k in ("canvas", "sidebar", "messageSurface", "accent", "text")],
            "accent": colors["accent"],
            "accentForeground": colors["accentForeground"],
            "canvas": colors["canvas"],
        })

        poster = first(repo, "hero.jpg", "hero-poster.jpg")
        still = Image.open(poster).convert("RGB")
        cover = SIDEBAR_COVER.get(slug)
        if cover:
            x, y, w, h, source_y = cover
            still.paste(still.crop((x, source_y, x + w, source_y + h)), (x, y))
        ImageOps.fit(still, (960, 490), Image.LANCZOS).save(
            ROOT / f"assets/posters/{slug}.webp", "WEBP", quality=76, method=6)

        loop = ROOT / f"assets/loops/{slug}.mp4"
        if not loop.exists():
            source = first(repo, "hero.mp4", f"{slug}-hero.mp4")
            scale = "scale=960:490:force_original_aspect_ratio=increase,crop=960:490,fps=24,format=yuv420p"
            if cover:
                x, y, w, h, source_y = cover
                scale = f"split[a][b];[b]crop={w}:{h}:{x}:{source_y}[p];[a][p]overlay={x}:{y},{scale}"
            run("ffmpeg", "-y", "-v", "error", "-i", str(source), "-an",
                "-filter_complex" if cover else "-vf", scale,
                "-c:v", "libx264", "-preset", "slow", "-crf", "29",
                "-color_range", "tv", "-movflags", "+faststart", str(loop))
        print(slug, loop.stat().st_size // 1024, "KB", flush=True)

    (ROOT / "themes.json").write_text(json.dumps(themes, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
