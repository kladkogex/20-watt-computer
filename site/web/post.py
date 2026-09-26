"""Turn the TeX4ht output of both editions into the web edition's pages.

    python3 site/web/post.py <html-full> <html-short> <out-dir>

<html-full> and <html-short> are make4ht output directories (jobs "full" and "short", see build.sh).
Every chapter page carries both texts; the reader switches «Коротко / Полностью». Exercises get
their answers from appendix C as collapsible blocks. Appendices and references are full-only pages.
"""
import html, json, pathlib, re, shutil, sys

full_dir, short_dir, out = (pathlib.Path(a) for a in sys.argv[1:4])
HERE = pathlib.Path(__file__).parent

# ---------------------------------------------------------------- pages and their sources
def title_of(path):
    s = path.read_text(encoding="utf-8")
    m = re.search(r"<title>(.*?)</title>", s, re.S)
    return " ".join(html.unescape(m.group(1)).split()) if m else ""

def find_li(d, job, title):
    for p in sorted(d.glob(f"{job}li*.html")):
        if title_of(p) == title:
            return p
    raise SystemExit(f"no page «{title}» in {d}")

def find_ap(d, job, letter):
    for p in sorted(d.glob(f"{job}ap*.html")):
        if title_of(p).startswith(letter + " "):
            return p
    raise SystemExit(f"no appendix {letter} in {d}")

chapters = sorted(int(m.group(1)) for p in full_dir.glob("fullch*.html")
                  if (m := re.fullmatch(r"fullch(\d+)\.html", p.name)))

# page slug -> sources; order is the reading order
pages = [{"slug": "00", "full": find_li(full_dir, "full", "Как читать эту книгу"),
          "short": find_li(short_dir, "short", "Прежде чем начать")}]
for n in chapters:
    sp = short_dir / f"shortch{n}.html"
    pages.append({"slug": f"{n:02d}", "n": n, "full": full_dir / f"fullch{n}.html",
                  "short": sp if sp.exists() else None})
for letter in "ABCD":
    pages.append({"slug": letter.lower(), "full": find_ap(full_dir, "full", letter), "appendix": letter})
pages.append({"slug": "refs", "full": find_li(full_dir, "full", "Литература")})

# where every TeX4ht file ends up, for rewriting links
target = {}
for pg in pages:
    target[pg["full"].name] = (pg["slug"], "")
    if pg.get("short"):
        target[pg["short"].name] = (pg["slug"], "s-")
toc_files = {"full.html", "short.html"} | {p.name for p in full_dir.glob("fullli*.html")
                                            if title_of(p) == "Оглавление"} \
                                        | {p.name for p in short_dir.glob("shortli*.html")
                                           if title_of(p) == "Оглавление"}

# ---------------------------------------------------------------- cleaning TeX4ht markup
def body_of(path):
    s = path.read_text(encoding="utf-8")
    s = s[s.index(">", s.index("<body")) + 1: s.rindex("</body>")]
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r'<div class="crosslinks">.*?</div>', "", s, flags=re.S)
    # tags are written with line breaks inside them; normalise whitespace
    s = re.sub(r"<([a-zA-Z][^<>]*)>", lambda m: "<" + " ".join(m.group(1).split()) + ">", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    # key formulas: TeX4ht opens and closes the block inside paragraphs
    s = re.sub(r'<p class="(?:no)?indent"\s*>\s*<div class="keyformula"></p>', '<div class="keyformula">', s)
    s = re.sub(r'<p class="(?:no)?indent"\s*>\s*</div>', '</div><p class="noindent">', s)
    s = re.sub(r'<p class="[^"]*"\s*>\s*</p>', "", s)
    return s

def split_heading(s):
    """Remove the chapter heading (the page template prints its own) but keep its anchors."""
    m = re.search(r'<h2 class="(?:like)?(?:chapter|appendix)Head"[^>]*>(.*?)</h2>', s, re.S)
    if not m:
        return s, ""
    anchors = "".join(re.findall(r'<a id="[^"]*"></a>', m.group(1)))
    inner = re.sub(r'<span class="titlemark">.*?</span>', "", m.group(1), flags=re.S)
    inner = re.sub(r"<br\s*/?>|<a id=\"[^\"]*\"></a>", "", inner).strip()
    return s[:m.start()] + anchors + s[m.end():], inner

def relink(s, prefix):
    """Point links at the new pages; ids of the short text get the prefix "s-"."""
    def href(m):
        f, frag = m.group(1), m.group(2) or ""
        if not f:
            return f'href="#{prefix}{frag[1:]}"' if frag else m.group(0)
        if f in toc_files:
            return 'href="../#toc"'
        if f in target:
            slug, pre = target[f]
            return f'href="{slug}.html' + (f"#{pre}{frag[1:]}" if frag else "") + '"'
        return m.group(0)
    s = re.sub(r'href="((?:full|short)[a-z]*\d*\.html)?(#[^"]*)?"', href, s)
    if prefix:
        s = re.sub(r'\bid="', f'id="{prefix}', s)
    s = re.sub(r'src="((?:full|short)\d+x\.svg)"', r'src="img/\1" loading="lazy"', s)
    return s

# ---------------------------------------------------------------- answers under exercises
answers_page = find_ap(full_dir, "full", "C")
answers = {}  # exercise anchor id -> answer html
ans = body_of(answers_page)
starts = list(re.finditer(r'<p class="noindent"\s*><a href="fullch\d+\.html#([^"]+)">.*?</a>'
                          r'(?:<span class="[^"]*">\.</span>)?\s*(?:\xa0|&#x00A0;|&nbsp;)?', ans, re.S))
for i, m in enumerate(starts):
    end = starts[i + 1].start() if i + 1 < len(starts) else len(ans)
    h = ans.find("<h3", m.end(), end)
    body = ans[m.end(): h if h != -1 else end]
    answers[m.group(1)] = '<p class="noindent">' + body.strip()

def add_answers(s):
    count = 0
    for aid, a in answers.items():
        pos = s.find(f'<a id="{aid}"></a>')
        if pos == -1:
            continue
        start = s.rfind('<div class="newtheorem">', 0, pos)
        depth, i = 0, start
        while True:  # find the matching </div>
            o, c = s.find("<div", i), s.find("</div>", i)
            if o != -1 and o < c:
                depth, i = depth + 1, o + 4
            else:
                depth, i = depth - 1, c + 6
                if depth == 0:
                    break
        block = ('<details class="answer"><summary data-ru="Ответ" data-en="Answer">Ответ</summary>'
                 f'<div class="answer-body">{a}</div></details>')
        s = s[:i] + block + s[i:]
        count += 1
    return s, count

# ---------------------------------------------------------------- the short text's pointer to the full one
def link_full(s):
    return re.sub(r'<p class="noindent"\s*><span class="[^"]*">(Формулы, модели, задачи и источники[^<]*)</span>\s*</p>',
                  r'<p class="tofull"><a href="#full" data-mode="full">\1 →</a></p>', s)

# ---------------------------------------------------------------- CSS from TeX4ht
def tex4ht_css(path, prefix):
    keep = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.search(r"\bbody\b|invert\(|Canvas|tcolobox-|crosslinks", line):
            continue
        line = line.replace("solid black", "solid var(--rule)").replace("solid #000", "solid var(--rule)")
        if prefix and "{" in line:
            sel, rest = line.split("{", 1)
            line = re.sub(r"#(?=[A-Za-z])", "#" + prefix, sel) + "{" + rest
        keep.append(line)
    return "\n".join(keep)

# ---------------------------------------------------------------- write
if out.exists():
    shutil.rmtree(out)
(out / "img").mkdir(parents=True)
for d in (full_dir, short_dir):
    for svg in d.glob("*.svg"):
        shutil.copy(svg, out / "img" / svg.name)
css = (HERE / "book.css").read_text(encoding="utf-8")
(out / "book.css").write_text(tex4ht_css(full_dir / "full.css", "") + "\n" +
                              tex4ht_css(short_dir / "short.css", "s-") + "\n" + css, encoding="utf-8")
template = (HERE / "page.html").read_text(encoding="utf-8")

APPX = {"A": ("Приложение A", "Appendix A"), "B": ("Приложение B", "Appendix B"),
        "C": ("Приложение C", "Appendix C"), "D": ("Приложение D", "Appendix D")}
nav = []
report = []
for pg in pages:
    full, ftitle = split_heading(relink(body_of(pg["full"]), ""))
    full, nans = add_answers(full) if "n" in pg else (full, 0)
    nex = len(re.findall(r'<span class="[^"]*">Задача \d+\.\d+ </span>', full))
    stitle, short = "", ""
    if pg.get("short"):
        short, stitle = split_heading(relink(body_of(pg["short"]), "s-"))
        short = link_full(short)
    if "n" in pg:
        kicker = (f"Глава {pg['n']}", f"Chapter {pg['n']}")
    elif "appendix" in pg:
        kicker = APPX[pg["appendix"]]
    elif pg["slug"] == "00":
        kicker = ("Введение", "Introduction")
    else:
        kicker = ("", "")
    pg.update(ftitle=ftitle, stitle=stitle, kicker=kicker, fullhtml=full, shorthtml=short)
    nav.append({"slug": pg["slug"], "title": re.sub(r"<[^>]+>", "", ftitle).strip(), "kicker": kicker[0]})
    report.append(f"{pg['slug']:>4}  exercises {nex:2d}  answers {nans:2d}  "
                  f"figures {full.count('<img')}+{short.count('<img')}  short {'yes' if short else '—'}")

BASE = "https://kladkogex.github.io/20-watt-computer/"
BOOK = {"@type": "Book", "name": "Компьютер на 20 ваттах. Как вычисляет мозг: количественный подход для инженеров",
        "alternateName": "The 20-Watt Computer: How the Brain Computes. A Quantitative Approach for Engineers",
        "author": {"@type": "Person", "name": "Константин Кладько", "alternateName": "Konstantin Kladko"},
        "url": BASE, "inLanguage": "ru", "isAccessibleForFree": True,
        "license": "https://creativecommons.org/licenses/by-nc-sa/4.0/"}

def description(body):
    """The first sentences of the text, for search results and link previews."""
    t = re.sub(r"<math.*?</math>", " … ", body, flags=re.S)
    t = re.sub(r"<(h3|figcaption|table|details)[^>]*>.*?</\1>", " ", t, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = " ".join(t.split())
    if len(t) > 180:
        t = t[:180].rsplit(" ", 1)[0] + " …"
    return html.escape(t, quote=True)

for i, pg in enumerate(pages):
    prev = pages[i - 1] if i > 0 else None
    nxt = pages[i + 1] if i + 1 < len(pages) else None
    plain = re.sub(r"<[^>]+>", "", pg["ftitle"]).strip()
    fill = {
        "TITLE": html.escape((pg["kicker"][0] + ". " if pg["kicker"][0] else "") + plain),
        "KICKER_RU": pg["kicker"][0], "KICKER_EN": pg["kicker"][1],
        "FTITLE": pg["ftitle"], "STITLE": pg["stitle"] or pg["ftitle"],
        "HASSHORT": "true" if pg["shorthtml"] else "false",
        "FULL": pg["fullhtml"], "SHORT": pg["shorthtml"],
        "PREV": f'{prev["slug"]}.html' if prev else "../#toc",
        "PREV_TITLE": html.escape(re.sub(r"<[^>]+>", "", prev["ftitle"]).strip()) if prev else "",
        "NEXT": f'{nxt["slug"]}.html' if nxt else "../#toc",
        "NEXT_TITLE": html.escape(re.sub(r"<[^>]+>", "", nxt["ftitle"]).strip()) if nxt else "",
        "SLUG": pg["slug"], "NAV": json.dumps(nav, ensure_ascii=False),
        "DESC": description(pg["fullhtml"]), "CANON": f"{BASE}read/{pg['slug']}.html",
        "JSONLD": json.dumps({"@context": "https://schema.org", "@type": "Chapter",
                              "name": plain, "url": f"{BASE}read/{pg['slug']}.html",
                              **({"position": pg["n"]} if "n" in pg else {}),
                              "inLanguage": "ru", "isAccessibleForFree": True,
                              "license": BOOK["license"], "author": BOOK["author"],
                              "isPartOf": BOOK}, ensure_ascii=False).replace("</", "<\\/"),
    }
    page = template
    for k, v in fill.items():
        page = page.replace("{{" + k + "}}", v)
    (out / f"{pg['slug']}.html").write_text(page, encoding="utf-8")

print("\n".join(report))
print(f"web edition: {len(pages)} pages, {len(list((out / 'img').glob('*.svg')))} figures -> {out}")
