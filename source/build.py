#!/usr/bin/env python3
"""Build index.html, README.md and assets/og.png from themes.json."""
import html
import json
import pathlib

from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
OWNER = "joshsaintjacque"
URL = f"https://{OWNER}.github.io/t3code-themes/"
MOODS = {"energetic": "Energetic", "calm": "Calm", "creative": "Creative"}
e = lambda value: html.escape(str(value), quote=True)


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def tag(theme):
    return f"{MOODS[theme['mood']]} · {theme['appearance']}"


def strip(theme):
    return "".join(f'<i style="background-color:{e(c)}"></i>' for c in theme["swatches"])


def row(theme, active):
    current = ' aria-current="true"' if active else ""
    return (
        f'        <li><a href="{e(theme["site"])}" data-slug="{e(theme["slug"])}"{current}>'
        f'<span class="chip" style="--c:{e(theme["canvas"])};--a:{e(theme["accent"])}"></span>'
        f'<span class="nm">{e(theme["name"])}</span><span class="md">{e(MOODS[theme["mood"]])}</span>'
        '<span class="bar"></span></a></li>'
    )


def card(theme):
    name = e(theme["name"])
    return f'''    <article class="card" data-slug="{e(theme["slug"])}">
      <a class="shot" href="{e(theme["site"])}" aria-label="Preview {name}"><img src="assets/posters/{e(theme["slug"])}.webp" width="960" height="490" loading="lazy" decoding="async" alt="{name} theme in T3 Code"></a>
      <div class="tiles" aria-hidden="true">{strip(theme)}</div>
      <div class="card-top"><h3><a href="{e(theme["site"])}">{name}</a></h3><span class="tag">{e(tag(theme))}</span></div>
      <p>{e(theme["line"])}</p>
      <div class="links"><a href="{e(theme["site"])}">Theme page</a><a href="{e(theme["repo"])}">Repository</a></div>
    </article>'''


def build_page(themes):
    first = themes[0]
    description = f"{len(themes)} living themes for T3 Code. Preview each one, then open its page or repository."
    data = json.dumps(
        [{k: t[k] for k in ("slug", "name", "appearance", "mood", "line", "description", "site", "repo", "swatches", "accent", "accentForeground")} for t in themes],
        ensure_ascii=False, separators=(",", ":"),
    ).replace("<", "\\u003c")
    values = {
        "DESCRIPTION": e(description), "URL": URL, "OWNER": OWNER, "COUNT": str(len(themes)),
        "FIRST_ACCENT": first["accent"], "FIRST_ACCENT_FG": first["accentForeground"],
        "FIRST_SLUG": e(first["slug"]), "FIRST_NAME": e(first["name"]), "FIRST_LINE": e(first["line"]), "FIRST_DESC": e(first["description"]),
        "FIRST_META": e(tag(first)), "FIRST_SITE": e(first["site"]), "FIRST_REPO": e(first["repo"]),
        "FIRST_STRIP": strip(first),
        "ROWS": "\n".join(row(t, i == 0) for i, t in enumerate(themes)),
        "CARDS": "\n".join(card(t) for t in themes),
        "DATA": data,
    }
    page = (ROOT / "source/template.html").read_text()
    for key, value in values.items():
        page = page.replace("{{" + key + "}}", value)
    assert "{{" not in page, "unfilled template value"
    (ROOT / "index.html").write_text(page)


def build_readme(themes):
    lines = [
        "# Themes for T3 Code", "",
        f"{len(themes)} living themes for [T3 Code](https://github.com/pingdotgg/t3code). Each one moves while your agent works and settles when the turn ends.", "",
        f"**[Browse and preview them all]({URL})**", "",
        f"[![The full set of themes](assets/og.png)]({URL})", "",
        "| Theme | Mood | Mode | While your agent works | Links |",
        "|---|---|---|---|---|",
    ]
    for t in themes:
        lines.append(f"| **{t['name']}** | {MOODS[t['mood']]} | {t['appearance'].title()} | {t['line']} | [Page]({t['site']}) · [Repo]({t['repo']}) |")
    lines += [
        "", "## Install a theme", "",
        "Open a theme's page or repository, download its JSON file, then run:", "",
        "```sh", "~/.t3/bin/t3 theme set <theme>.json", "```", "",
        "This sets it as the theme for your T3 environment.", "",
        "## Update this gallery", "",
        "`themes.json` drives the page and this README. To refresh it from local theme checkouts:", "",
        "```sh", "python3 source/collect.py <dir-with-checkouts>", "python3 source/build.py", "```", "",
        "Independent themes, not affiliated with T3 Code. MIT licensed.", "",
    ]
    (ROOT / "README.md").write_text("\n".join(lines))


def build_og(themes):
    columns, rows = 7, 3
    width, height = 1200, 630
    sheet = Image.new("RGB", (width, height), "#141416")
    for i, theme in enumerate(themes[:columns * rows]):
        x0, x1 = (i % columns) * width // columns, (i % columns + 1) * width // columns
        y0, y1 = (i // columns) * height // rows, (i // columns + 1) * height // rows
        with Image.open(ROOT / f"assets/posters/{theme['slug']}.webp") as poster:
            tile = ImageOps.fit(poster.convert("RGB"), (x1 - x0 - 2, y1 - y0 - 2), Image.LANCZOS, centering=(0.2, 0.42))
        sheet.paste(tile, (x0 + 1, y0 + 1))
    sheet.save(ROOT / "assets/og.png", optimize=True)


def main():
    themes = json.loads((ROOT / "themes.json").read_text())
    assert len({t["slug"] for t in themes}) == len(themes)
    for theme in themes:
        for name in (f"assets/posters/{theme['slug']}.webp", f"assets/loops/{theme['slug']}.mp4"):
            assert (ROOT / name).exists(), f"missing {name}"
        ratio = contrast(theme["accent"], theme["accentForeground"])
        assert ratio >= 4.5, f"{theme['slug']}: accent button contrast {ratio:.2f}"
    build_page(themes)
    build_readme(themes)
    build_og(themes)
    print(f"built {len(themes)} themes")


if __name__ == "__main__":
    main()
