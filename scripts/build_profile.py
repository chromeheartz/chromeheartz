"""Renders status.svg and the terminal block in README.md from profile.config.json.

Stats come from the dev-stats gist that coding-rpg-box updates daily, so this needs no extra secret.
Any failure raises, which fails the Action and leaves the committed files untouched.
"""
import base64
import html
import io
import json
import os
import pathlib
import re
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT_URL = "https://cdn.jsdelivr.net/npm/galmuri@2.40.3/dist/{}.woff2"
LANG = {"JavaScript": "JS", "TypeScript": "TS", "Python": "Py"}
PANEL, EDGE, RED, GOLD, SNOW, MUTE, TRACK = "#16202e", "#3d536b", "#b3202a", "#f4c542", "#eaf3fa", "#a9bccd", "#0b1119"


def parse_stats(text):
    def find(pattern):
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"dev-stats gist has no match for {pattern!r}: {text!r}")
        return match

    head = find(r"Lv\.(\d+)\s+([A-Za-z][A-Za-z ]*[A-Za-z])")
    commits = find(r"commits\s+(\d+).*?(\d+)%")
    return {
        "level": int(head[1]),
        "title": head[2],
        "commits": int(commits[1]),
        "exp": int(commits[2]),
        "langs": int(find(r"langs\s+(\d+)")[1]),
        "streak": int(find(r"streak\s+(\d+)d")[1]),
        "best": int(find(r"best\s+(\d+)d")[1]),
    }


def clean_description(text):
    """Repo descriptions can hold emoji, :shortcodes: and em dashes that break the terminal columns."""
    text = re.sub(r":[a-z_]+:", "", text or "")
    text = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️‍]", "", text)
    text = re.sub(r"\s*\u2014\s*", ", ", text)
    return " ".join(text.split())


def terminal_block(repos, conf):
    """Repos arrive sorted by last push. A new repo lands in ~/projects with its GitHub description."""
    shown = [r for r in repos if not r["fork"] and r["name"] not in conf["hide"]]
    width = max(len(r["name"]) for r in shown) + 2

    def row(repo):
        name = repo["name"]
        pad = " " * (width - len(name) - 1)
        lang = LANG.get(repo["language"], repo["language"] or "")
        desc = conf["descriptions"].get(name) or clean_description(repo["description"])
        link = f'<a href="{html.escape(repo["html_url"])}">{html.escape(name)}/</a>'
        return f"{link}{pad}{html.escape(lang):<6}{html.escape(desc)}".rstrip()

    projects = [row(r) for r in shown if r["name"] not in conf["study"]]
    study = [row(r) for r in shown if r["name"] in conf["study"]]
    return "<pre>$ ls ~/projects\n" + "\n".join(projects) + "\n\n$ ls ~/study\n" + "\n".join(study) + "</pre>"


def replace_block(readme, block):
    pattern = r"(<!-- projects:start -->\n).*?(<!-- projects:end -->)"
    if not re.search(pattern, readme, re.S):
        raise ValueError("README.md is missing the projects:start / projects:end markers")
    return re.sub(pattern, lambda m: m[1] + block + "\n" + m[2], readme, flags=re.S)


class Face:
    """A font subset to the card's characters. recalcTimestamp=False keeps the output stable between runs."""

    def __init__(self, raw, text):
        self.source = TTFont(io.BytesIO(raw), recalcTimestamp=False)
        self.cmap, self.hmtx = self.source.getBestCmap(), self.source["hmtx"]
        self.scale = 1 / self.source["head"].unitsPerEm
        missing = sorted({c for c in text if ord(c) not in self.cmap and c != " "})
        if missing:
            raise ValueError(f"Galmuri has no glyph for {missing}, so remove them from profile.config.json")
        font = TTFont(io.BytesIO(raw), recalcTimestamp=False)
        options = subset.Options()
        options.flavor = "woff2"
        subsetter = subset.Subsetter(options)
        subsetter.populate(text=text)
        subsetter.subset(font)
        font.flavor = "woff2"
        out = io.BytesIO()
        font.save(out)
        self.base64 = base64.b64encode(out.getvalue()).decode()

    def fit(self, text, size, room):
        width = sum(self.hmtx[self.cmap[ord(c)]][0] for c in text if ord(c) in self.cmap) * self.scale * size
        if width > room:
            raise ValueError(f"{text!r} is {width:.0f}px wide and the card has room for {room}px, so shorten it")


def status_svg(stats, card, regular, bold, avatar):
    esc = html.escape
    regular.fit(card["job"], 16, 240)
    regular.fit(card["tagline"], 16, 240)
    regular.fit(stats["title"], 16, 240)
    bold.fit(card["name"], 24, 240)
    for _, value in card["equip"]:
        regular.fit(value, 16, 330)
    grid = [("커밋", f'{stats["commits"]:,}', 24, 226), ("언어", stats["langs"], 222, 226),
            ("연속", f'{stats["streak"]}일', 24, 252), ("최고", f'{stats["best"]}일', 222, 252)]
    cells = "".join(f'<text x="{x}" y="{y}" class="m">{k}</text><text x="{x + 46}" y="{y}">{v}</text>' for k, v, x, y in grid)
    equip = "".join(
        f'<text x="24" y="{296 + i * 26}" class="m">{esc(k)}</text><text x="70" y="{296 + i * 26}">{esc(v)}</text>'
        for i, (k, v) in enumerate(card["equip"][:3])
    )
    label = f'{card["name"]} 상태창: Lv.{stats["level"]} {stats["title"]}, 커밋 {stats["commits"]}, 언어 {stats["langs"]}, 연속 {stats["streak"]}일, 최고 {stats["best"]}일'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="368" viewBox="0 0 420 368" role="img" aria-label="{esc(label)}"><style>@font-face{{font-family:G;src:url(data:font/woff2;base64,{regular.base64})}}@font-face{{font-family:G;font-weight:700;src:url(data:font/woff2;base64,{bold.base64})}}
text{{font:16px G,monospace;fill:{SNOW}}}.b{{font-weight:700}}.g{{fill:{GOLD}}}.m{{fill:{MUTE}}}@keyframes bob{{50%{{transform:translateY(-4px)}}}}.av{{animation:bob 1.2s steps(1) 4}}@keyframes fill{{from{{transform:scaleX(0)}}}}.xp{{transform-origin:206px 0;animation:fill 1.2s steps(12)}}@media(prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>
<path fill="{EDGE}" d="M4 0H416V4H420V364H416V368H4V364H0V4H4Z"/><path fill="{PANEL}" d="M8 4H412V8H416V360H412V364H8V360H4V8H8Z"/><rect x="8" y="8" width="404" height="32" fill="{RED}"/><text x="20" y="30" class="b">STATUS</text><text x="400" y="30" class="b" text-anchor="end">Lv.{stats["level"]}</text>
<image class="av" href="data:image/png;base64,{avatar}" x="36" y="52" width="95" height="132" style="image-rendering:pixelated"/>
<text x="160" y="76" class="b" style="font-size:24px">{esc(card["name"])}</text><text x="160" y="102" class="g">{esc(stats["title"])}</text><text x="160" y="126" class="m">{esc(card["job"])}</text>
<text x="160" y="156">EXP</text><rect x="206" y="144" width="160" height="14" fill="{TRACK}"/><rect class="xp" x="206" y="144" width="{round(160 * stats["exp"] / 100)}" height="14" fill="{GOLD}"/><text x="400" y="156" text-anchor="end" class="m">{stats["exp"]}%</text>
<text x="160" y="180" class="m">{esc(card["tagline"])}</text>
<rect x="20" y="198" width="380" height="4" fill="{EDGE}"/>{cells}<rect x="20" y="268" width="380" height="4" fill="{EDGE}"/>{equip}</svg>
'''


def get(url):
    headers = {"User-Agent": "profile-build"}
    if "api.github.com" in url and os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f'Bearer {os.environ["GH_TOKEN"]}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return response.read()


def main():
    conf = json.loads((ROOT / "profile.config.json").read_text())
    gist = json.loads(get(f'https://api.github.com/gists/{conf["gist"]}'))
    stats = parse_stats(next(iter(gist["files"].values()))["content"])
    repos = json.loads(get(f'https://api.github.com/users/{conf["user"]}/repos?per_page=100&sort=pushed'))

    card = conf["card"]
    labels = "STATUSLv.0123456789,%EXP커밋언어연속최고일" + stats["title"]
    text = labels + card["name"] + card["job"] + card["tagline"] + "".join(k + v for k, v in card["equip"])
    regular = Face(get(FONT_URL.format("Galmuri11")), text)
    bold = Face(get(FONT_URL.format("Galmuri11-Bold")), "STATUSLv.0123456789" + card["name"])
    avatar = base64.b64encode((ROOT / "assets/avatar.png").read_bytes()).decode()

    svg = status_svg(stats, card, regular, bold, avatar)
    readme = replace_block((ROOT / "README.md").read_text(), terminal_block(repos, conf["terminal"]))
    (ROOT / "status.svg").write_text(svg)
    (ROOT / "README.md").write_text(readme)


if __name__ == "__main__":
    main()
