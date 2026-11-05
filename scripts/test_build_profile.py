from build_profile import clean_description, parse_stats, replace_block, terminal_block

GIST = "🎮 Lv.35  Polyglot Sage 🧙\n⚔️ commits   2138  █████████░░░ 75%\n✨ langs       14  ████████████\n🔥 streak     27d  ███████████░\n🏆 best       49d  ██████████░░"
assert parse_stats(GIST) == {"level": 35, "title": "Polyglot Sage", "commits": 2138, "exp": 75, "langs": 14, "streak": 27, "best": 49}
try:
    parse_stats("no stats")
    raise SystemExit("parse_stats accepted a broken gist")
except ValueError:
    pass

assert clean_description("🎄 트리 \u2014 Action :bathtub:") == "트리, Action"

repo = lambda name, fork=False, desc="d": {"name": name, "fork": fork, "language": "TypeScript", "description": desc, "html_url": f"https://x/{name}"}
conf = {"hide": ["hidden"], "study": ["s"], "descriptions": {"p": "설명"}}
block = terminal_block([repo("p"), repo("s"), repo("hidden"), repo("f", fork=True), repo("new", desc="<b>")], conf)
assert '<a href="https://x/p">p/</a>' in block and "설명" in block
assert block.index("~/study") > block.index("new/") > block.index("p/") and block.index("s/") > block.index("~/study")
assert "hidden" not in block and "f/" not in block and "&lt;b&gt;" in block

assert replace_block("a\n<!-- projects:start -->\nold\n<!-- projects:end -->\nb", "new") == "a\n<!-- projects:start -->\nnew\n<!-- projects:end -->\nb"
assert replace_block("<!-- projects:start -->\n<!-- projects:end -->", "new") == "<!-- projects:start -->\nnew\n<!-- projects:end -->"
try:
    replace_block("no markers", "x")
    raise SystemExit("replace_block accepted a README without markers")
except ValueError:
    pass
print("ok")
