"""Turn the TeX4ht output of one edition (full book + paperback) into the web edition's pages.

    python3 site/web/post.py --lang en --src <tree>/en --full <html-full> --short <html-short> \
                             --out _site/read/en --langs ru,en,es,...

<html-full> and <html-short> are make4ht output directories (jobs "full" and "short", see build.sh); <tree>/en
is the edition's LaTeX source (for the exercise word, the paperback's pointer to the full book and the titles).
Every chapter page carries both texts; the reader switches between the short and the full one. Exercises get
their answers from appendix C as collapsible blocks. Appendices and references are full-only pages.
Pages are recognised by their content, never by their titles, so the same script serves every language.
"""
import argparse, html, json, pathlib, re, shutil

ap = argparse.ArgumentParser()
for a in ("--lang", "--src", "--full", "--short", "--out", "--langs"):
    ap.add_argument(a, required=True)
args = ap.parse_args()
LANG, SRC = args.lang, pathlib.Path(args.src)
full_dir, short_dir, out = pathlib.Path(args.full), pathlib.Path(args.short), pathlib.Path(args.out)
LANGS = [l for l in args.langs.split(",") if l]
HERE = pathlib.Path(__file__).parent
BASE = "https://kladkogex.github.io/20-watt-computer/"

# ---------------------------------------------------------------- per-language interface text
UI = {
 "ru": dict(chapter="Глава {n}", appendix="Приложение {x}", intro="Введение", short="Коротко", short_sub="без формул, с рисунками",
            full="Полностью", full_sub="формулы, модели, задачи", answer="Ответ", prev="Назад", next="Дальше",
            starline="Книга бесплатная и открытая. Если глава была полезной, поставьте книге звезду на GitHub: так её найдут другие.",
            star="Звезда на GitHub", breadboard="Макетная плата", goto="Перейти к главе", edition="Издание"),
 "en": dict(chapter="Chapter {n}", appendix="Appendix {x}", intro="Introduction", short="Short", short_sub="no formulas, with drawings",
            full="Full", full_sub="formulas, models, exercises", answer="Answer", prev="Previous", next="Next",
            starline="The book is free and open. If this chapter was useful, star the book on GitHub so others can find it.",
            star="Star on GitHub", breadboard="Neuron breadboard", goto="Go to chapter", edition="Edition"),
 "es": dict(chapter="Capítulo {n}", appendix="Apéndice {x}", intro="Introducción", short="Breve", short_sub="sin fórmulas, con dibujos",
            full="Completo", full_sub="fórmulas, modelos, ejercicios", answer="Respuesta", prev="Anterior", next="Siguiente",
            starline="El libro es libre y abierto. Si este capítulo te ha sido útil, dale una estrella en GitHub para que otros lo encuentren.",
            star="Estrella en GitHub", breadboard="Protoboard de neuronas", goto="Ir al capítulo", edition="Edición"),
 "pt": dict(chapter="Capítulo {n}", appendix="Apêndice {x}", intro="Introdução", short="Resumo", short_sub="sem fórmulas, com desenhos",
            full="Completo", full_sub="fórmulas, modelos, exercícios", answer="Resposta", prev="Anterior", next="Próximo",
            starline="O livro é livre e aberto. Se este capítulo foi útil, dê uma estrela ao livro no GitHub para que outros o encontrem.",
            star="Estrela no GitHub", breadboard="Protoboard de neurônios", goto="Ir para o capítulo", edition="Edição"),
 "uk": dict(chapter="Розділ {n}", appendix="Додаток {x}", intro="Вступ", short="Коротко", short_sub="без формул, з малюнками",
            full="Повністю", full_sub="формули, моделі, задачі", answer="Відповідь", prev="Назад", next="Далі",
            starline="Книга безкоштовна й відкрита. Якщо розділ був корисним, поставте книзі зірку на GitHub — так її знайдуть інші.",
            star="Зірка на GitHub", breadboard="Макетна плата", goto="Перейти до розділу", edition="Видання"),
 "zh": dict(chapter="第{n}章", appendix="附录 {x}", intro="导读", short="简版", short_sub="无公式，有插图",
            full="完整版", full_sub="公式、模型、习题", answer="答案", prev="上一章", next="下一章",
            starline="本书免费开放。如果这一章对你有用，请在 GitHub 上给本书加星，让更多人发现它。",
            star="在 GitHub 上加星", breadboard="神经元面包板", goto="跳转到章节", edition="版本"),
 "ja": dict(chapter="第{n}章", appendix="付録 {x}", intro="はじめに", short="簡約版", short_sub="数式なし・図入り",
            full="完全版", full_sub="数式・モデル・問題", answer="解答", prev="前へ", next="次へ",
            starline="本書は無料で公開されています。この章が役に立ったら、GitHub で本書にスターを付けてください。ほかの人が見つけやすくなります。",
            star="GitHub でスター", breadboard="ニューロン・ブレッドボード", goto="章へ移動", edition="版"),
 "ko": dict(chapter="제{n}장", appendix="부록 {x}", intro="들어가며", short="간추림", short_sub="수식 없이, 그림과 함께",
            full="완전판", full_sub="수식, 모델, 연습문제", answer="답", prev="이전", next="다음",
            starline="이 책은 무료로 공개되어 있습니다. 이 장이 도움이 되었다면 GitHub에서 책에 별을 눌러 주세요. 다른 사람들이 찾기 쉬워집니다.",
            star="GitHub 별 누르기", breadboard="뉴런 브레드보드", goto="장으로 이동", edition="판"),
 "fr": dict(chapter="Chapitre {n}", appendix="Annexe {x}", intro="Introduction", short="Court", short_sub="sans formules, avec dessins",
            full="Complet", full_sub="formules, modèles, exercices", answer="Réponse", prev="Précédent", next="Suivant",
            starline="Le livre est libre et ouvert. Si ce chapitre vous a été utile, donnez une étoile au livre sur GitHub pour que d’autres le trouvent.",
            star="Étoile sur GitHub", breadboard="Platine à neurones", goto="Aller au chapitre", edition="Édition"),
 "vi": dict(chapter="Chương {n}", appendix="Phụ lục {x}", intro="Giới thiệu", short="Ngắn gọn", short_sub="không công thức, có hình vẽ",
            full="Đầy đủ", full_sub="công thức, mô hình, bài tập", answer="Đáp án", prev="Trước", next="Tiếp",
            starline="Cuốn sách miễn phí và mở. Nếu chương này hữu ích, hãy gắn sao cho sách trên GitHub để người khác tìm thấy.",
            star="Gắn sao trên GitHub", breadboard="Bảng mạch nơ-ron", goto="Đến chương", edition="Ấn bản"),
 "ar": dict(chapter="الفصل {n}", appendix="الملحق {x}", intro="مقدمة", short="مختصر", short_sub="بلا معادلات، مع رسوم",
            full="كامل", full_sub="معادلات، نماذج، تمارين", answer="الجواب", prev="السابق", next="التالي",
            starline="الكتاب مجاني ومفتوح. إن كان هذا الفصل مفيدًا لك، فامنح الكتاب نجمة على GitHub ليجده الآخرون.",
            star="نجمة على GitHub", breadboard="لوحة الخلايا العصبية", goto="انتقل إلى الفصل", edition="الطبعة"),
}
# the switch words must be the ones the paperback preface of each edition uses
UI["ko"].update(short="짧게", full="전체")
EDITION_NAME = {"ru": "Русский", "en": "English", "zh": "中文", "ja": "日本語", "ko": "한국어",
                "es": "Español", "pt": "Português", "uk": "Українська", "fr": "Français", "vi": "Tiếng Việt", "ar": "العربية"}
RTL = {"ar"}
HTMLLANG = {"zh": "zh-Hans", "pt": "pt-BR"}
HREFLANG = {"zh": "zh-Hans", "pt": "pt-BR"}
OGLOCALE = {"ru": "ru_RU", "en": "en_US", "zh": "zh_CN", "ja": "ja_JP", "ko": "ko_KR", "es": "es_ES", "pt": "pt_BR", "uk": "uk_UA",
            "fr": "fr_FR", "vi": "vi_VN", "ar": "ar_AR"}
# PT Serif covers Latin and Cyrillic; these editions need another face for their script
CJK_FONT = {"zh": "Noto+Serif+SC", "ja": "Noto+Serif+JP", "ko": "Noto+Serif+KR", "vi": "Noto+Serif", "ar": "Noto+Naskh+Arabic"}
CJK_FAMILY = {"zh": "Noto Serif SC", "ja": "Noto Serif JP", "ko": "Noto Serif KR", "vi": "Noto Serif", "ar": "Noto Naskh Arabic"}
T = UI[LANG]

# ---------------------------------------------------------------- facts taken from the edition's own sources
def tex(path):
    return (SRC / path).read_text(encoding="utf-8")

def plain(s):
    """Very small LaTeX → text for titles and the pointer sentence."""
    s = re.sub(r"\\(Huge|Large|large|small|normalsize|itshape|bfseries)\b", "", s)
    s = re.sub(r"\\\\(\[[^\]]*\])?", " ", s)
    s = s.replace("---", "—").replace("--", "–").replace("~", " ")
    s = re.sub(r"\\[a-zA-Z]+\*?", "", s).replace("{", "").replace("}", "")
    return " ".join(s.split())

main_tex = tex("main.tex")
EXERCISE = re.search(r"\\newtheorem\{exercise\}\{([^}]*)\}", main_tex).group(1)
PROPOSITION = re.search(r"\\newtheorem\{proposition\}\{([^}]*)\}", main_tex).group(1)
m = re.search(r"\\title\{\\Huge (.*?)\\\\\[", main_tex, re.S)
BOOKTITLE = plain(m.group(1)) if m else "The 20-Watt Computer"
m = re.search(r"\\title\{.*?\\\\\[\d+pt\]\s*\\Large (.*?)\}\n", main_tex, re.S)
SUBTITLE = plain(m.group(1)) if m else ""
m = re.search(r"\\author\{\\Large (.*?)\}", main_tex)
AUTHOR = plain(m.group(1)) if m else "Konstantin Kladko"
m = re.search(r"\\newcommand\{\\fullversion\}\[1\]\{.*?\\emph\{(.*?)#1", tex("paperback/main.tex"), re.S)
POINTER = plain(m.group(1))[:8] if m else None

# ---------------------------------------------------------------- pages and their sources
def read(path):
    return path.read_text(encoding="utf-8")

def li_pages(d, job):
    return sorted(d.glob(f"{job}li*.html"), key=lambda p: int(re.search(r"(\d+)", p.name).group(1)))

def is_toc(p):
    return "chapterToc" in read(p)

def is_bib(p):
    return "thebibliography" in read(p)

full_li = [p for p in li_pages(full_dir, "full") if not is_toc(p)]
short_li = [p for p in li_pages(short_dir, "short") if not is_toc(p)]
refs_page = next(p for p in full_li if is_bib(p))
roadmap_page = next(p for p in full_li if p is not refs_page)
preface_page = short_li[0] if short_li else None
appendices = sorted(full_dir.glob("fullap*.html"), key=lambda p: int(re.search(r"(\d+)", p.name).group(1)))
if len(appendices) != 4:
    raise SystemExit(f"{LANG}: expected 4 appendices, found {len(appendices)}")

chapters = sorted(int(m.group(1)) for p in full_dir.glob("fullch*.html")
                  if (m := re.fullmatch(r"fullch(\d+)\.html", p.name)))

# page slug -> sources; order is the reading order
pages = [{"slug": "00", "full": roadmap_page, "short": preface_page}]
for n in chapters:
    sp = short_dir / f"shortch{n}.html"
    pages.append({"slug": f"{n:02d}", "n": n, "full": full_dir / f"fullch{n}.html",
                  "short": sp if sp.exists() else None})
for letter, p in zip("abcd", appendices):
    pages.append({"slug": letter, "full": p, "appendix": letter.upper()})
pages.append({"slug": "refs", "full": refs_page})

# where every TeX4ht file ends up, for rewriting links
target = {}
for pg in pages:
    target[pg["full"].name] = (pg["slug"], "")
    if pg.get("short"):
        target[pg["short"].name] = (pg["slug"], "s-")
toc_files = {"full.html", "short.html"} | {p.name for p in li_pages(full_dir, "full") if is_toc(p)} \
                                        | {p.name for p in li_pages(short_dir, "short") if is_toc(p)}

# ---------------------------------------------------------------- cleaning TeX4ht markup
def body_of(path):
    s = read(path)
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
    # xelatex output writes some CJK text one character per <span>: merge neighbours of the same class
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'(<span class="([^"]+)">[^<]*)</span>(<span class="\2">)', r'\1', s)
    return s

# Ukrainian appendices are lettered А, Б, В, Г; the web build numbers them A–D for TeX4ht (see prep.py)
UK_LETTER = {"A": "А", "B": "Б", "C": "В", "D": "Г"}
def uk_letters(s):
    if LANG != "uk":
        return s
    sub = lambda m: m.group(1) + UK_LETTER[m.group(2)] + m.group(3)
    s = re.sub(r'(<span class="titlemark">)([A-D])((?:\.\d+)*)', sub, s)       # headings A.1
    s = re.sub(r'(<a href="[^"]*">)([A-D])((?:\.\d+)*</a>)', sub, s)          # references A, A.1
    s = re.sub(r'(<td class="eq-no">\()([A-D])(\.\d+)', sub, s)               # equation numbers (A.1)
    s = re.sub(r'(<span class="id">[^<]*?\s)([A-D])(\.\d+)', sub, s)          # captions: Таблиця A.1
    return s

def name_heads(s):
    """CJK conversions (xelatex) drop the theorem name from its head; put it back. Exercise heads carry the
    difficulty stars (⋆), proposition heads a title; the book uses no other theorem-like environments."""
    def fix(m):
        head = m.group(0)
        text = re.sub(r"<[^>]+>", "", head)
        if EXERCISE in text or PROPOSITION in text:
            return head
        name = EXERCISE if "⋆" in head else PROPOSITION
        return re.sub(r'(<span class="[^"]*">)(\d+\.\d+ )', r'\1' + name + r' \2', head, count=1)
    return re.sub(r'<span class="head">.*?</span>\s*</span>', fix, s, flags=re.S)

def split_heading(s):
    """Remove the chapter heading (the page template prints its own) but keep its anchors.
    Returns (body, title, titlemark)."""
    m = re.search(r'<h2 class="(?:like)?(?:chapter|appendix)Head"[^>]*>(.*?)</h2>', s, re.S)
    if not m:
        return s, "", ""
    anchors = "".join(re.findall(r'<a id="[^"]*"></a>', m.group(1)))
    mark = re.search(r'<span class="titlemark">(.*?)</span>', m.group(1), re.S)
    mark = " ".join(re.sub(r"<[^>]+>", "", mark.group(1)).split()) if mark else ""
    inner = re.sub(r'<span class="titlemark">.*?</span>', "", m.group(1), flags=re.S)
    inner = re.sub(r"<br\s*/?>|<a id=\"[^\"]*\"></a>", "", inner).strip()
    return s[:m.start()] + anchors + s[m.end():], inner, mark

def relink(s, prefix):
    """Point links at the new pages; ids of the short text get the prefix "s-"."""
    def href(m):
        f, frag = m.group(1), m.group(2) or ""
        if not f:
            return f'href="#{prefix}{frag[1:]}"' if frag else m.group(0)
        if f in toc_files:
            return 'href="../../#toc"'
        if f in target:
            slug, pre = target[f]
            return f'href="{slug}.html' + (f"#{pre}{frag[1:]}" if frag else "") + '"'
        return m.group(0)
    s = re.sub(r'href="((?:full|short)[a-z]*\d*\.html)?(#[^"]*)?"', href, s)
    if prefix:
        s = re.sub(r'\bid="', f'id="{prefix}', s)
    s = re.sub(r'src="((?:full|short)\d+x\.svg)"', r'src="img/\1" loading="lazy"', s)
    # ctex prints chapter numbers as Chinese numerals (十六), and TeX4ht drops them from the reference text,
    # leaving an empty link; the source writes 第\ref{…}章 around it, so fill in the chapter's number
    s = re.sub(r'<a href="(\d\d|[a-d])\.html(#[^"]*)?"></a>',
               lambda m: f'<a href="{m.group(1)}.html{m.group(2) or ""}">'
                         f'{int(m.group(1)) if m.group(1).isdigit() else m.group(1).upper()}</a>', s)
    return s

# ---------------------------------------------------------------- answers under exercises
answers = {}  # exercise anchor id -> answer html
ans = body_of(appendices[2])
starts = list(re.finditer(r'<p class="noindent"\s*>(?:<strong>)?<a href="fullch\d+\.html#([^"]+)">.*?</a>'
                          r'(?:<span class="[^"]*">\.</span>|\.)?(?:</strong>)?\s*(?:\xa0|&#x00A0;|&nbsp;)?', ans, re.S))
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
        if start == -1:
            continue
        depth, i = 0, start
        while True:  # find the matching </div>
            o, c = s.find("<div", i), s.find("</div>", i)
            if c == -1:
                break
            if o != -1 and o < c:
                depth, i = depth + 1, o + 4
            else:
                depth, i = depth - 1, c + 6
                if depth == 0:
                    break
        block = (f'<details class="answer"><summary>{T["answer"]}</summary>'
                 f'<div class="answer-body">{a}</div></details>')
        s = s[:i] + block + s[i:]
        count += 1
    return s, count

# ---------------------------------------------------------------- the short text's pointer to the full one
def link_full(s):
    if not POINTER:
        return s
    return re.sub(r'<p class="noindent"\s*><span class="[^"]*">(' + re.escape(POINTER) + r'[^<]*)</span>\s*</p>',
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
out.mkdir(parents=True, exist_ok=True)
(out / "img").mkdir(exist_ok=True)
for d in (full_dir, short_dir):
    for svg in d.glob("*.svg"):
        shutil.copy(svg, out / "img" / svg.name)
css = (HERE / "book.css").read_text(encoding="utf-8")
if LANG in CJK_FAMILY:  # PT Serif lacks these scripts
    first = f'"{CJK_FAMILY[LANG]}","PT Serif"' if LANG in ("vi", "ar") else f'"PT Serif","{CJK_FAMILY[LANG]}"'
    css += f'\n:root{{--serif:{first},serif}}\n'
    if LANG in ("zh", "ja", "ko"):
        css += '.text{hyphens:manual;line-break:strict}\n'
if LANG in RTL:  # right-to-left: formulas and figures stay left-to-right
    css += 'math,table.equation,figure.figure img,.text pre{direction:ltr}\n.pager .next{text-align:left}.pager .prev{text-align:right}\n'
(out / "book.css").write_text(tex4ht_css(full_dir / "full.css", "") + "\n" +
                              tex4ht_css(short_dir / "short.css", "s-") + "\n" + css, encoding="utf-8")
template = (HERE / "page.html").read_text(encoding="utf-8")

ex_re = re.compile(re.escape(EXERCISE) + r"\s*\d+\.\d+")
nav, report = [], []
for pg in pages:
    full, ftitle, fmark = split_heading(relink(body_of(pg["full"]), ""))
    full = uk_letters(name_heads(full))
    full, nans = add_answers(full) if "n" in pg else (full, 0)
    nex = len(ex_re.findall(re.sub(r"<[^>]+>", "", full)))
    stitle, short = "", ""
    if pg.get("short"):
        short, stitle, _ = split_heading(relink(body_of(pg["short"]), "s-"))
        short = link_full(short)
    if "n" in pg:
        kicker = T["chapter"].format(n=pg["n"])
    elif "appendix" in pg:
        # the edition's own appendix letter (Cyrillic in uk) comes from the heading's titlemark
        letter = fmark.split()[-1] if fmark else pg["appendix"]
        letter = UK_LETTER.get(letter, letter) if LANG == "uk" else letter
        kicker = T["appendix"].format(x=letter)
    elif pg["slug"] == "00":
        kicker = T["intro"]
    else:
        kicker = ""
    pg.update(ftitle=ftitle, stitle=stitle, kicker=kicker, fullhtml=full, shorthtml=short)
    nav.append({"slug": pg["slug"], "title": re.sub(r"<[^>]+>", "", html.unescape(ftitle)).strip(), "kicker": kicker})
    report.append(f"{pg['slug']:>4}  exercises {nex:2d}  answers {nans:2d}  "
                  f"figures {full.count('<img')}+{short.count('<img')}  short {'yes' if short else '—'}")
(out / "nav.json").write_text(json.dumps(nav, ensure_ascii=False), encoding="utf-8")

BOOK = {"@type": "Book", "name": f"{BOOKTITLE}. {SUBTITLE}".strip(". "),
        "author": {"@type": "Person", "name": "Konstantin Kladko", "alternateName": ["Stan Kladko", AUTHOR],
                   "url": BASE + "author/"},
        "url": BASE, "inLanguage": HTMLLANG.get(LANG, LANG), "isAccessibleForFree": True,
        "identifier": "https://doi.org/10.5281/zenodo.22984941",
        "license": "https://creativecommons.org/licenses/by-nc-sa/4.0/"}

def description(body):
    """The first sentences of the text, for search results and link previews."""
    t = re.sub(r"<math.*?</math>", " … ", body, flags=re.S)
    t = re.sub(r"<(h3|figcaption|table|details)[^>]*>.*?</\1>", " ", t, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = " ".join(t.split())
    if len(t) > 180:
        cut = t[:180]
        t = (cut.rsplit(" ", 1)[0] if " " in cut[100:] else cut) + " …"
    return html.escape(t, quote=True)

fonts = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@600;700"
         "&family=IBM+Plex+Sans:wght@400;500;600&family=PT+Serif:ital,wght@0,400;0,700;1,400;1,700"
         + (f"&family={CJK_FONT[LANG]}:wght@400;700" if LANG in CJK_FONT else "") + "&display=swap")

for i, pg in enumerate(pages):
    prev = pages[i - 1] if i > 0 else None
    nxt = pages[i + 1] if i + 1 < len(pages) else None
    plain_title = re.sub(r"<[^>]+>", "", html.unescape(pg["ftitle"])).strip()
    url = f"{BASE}read/{LANG}/{pg['slug']}.html"
    alternates = "\n".join(f'<link rel="alternate" hreflang="{HREFLANG.get(l, l)}" href="{BASE}read/{l}/{pg["slug"]}.html">'
                           for l in LANGS)
    if "en" in LANGS:
        alternates += f'\n<link rel="alternate" hreflang="x-default" href="{BASE}read/en/{pg["slug"]}.html">'
    editions = "".join(f'<option value="{l}"{" selected" if l == LANG else ""}>{EDITION_NAME[l]}</option>' for l in LANGS)
    fill = {
        "HTMLLANG": HTMLLANG.get(LANG, LANG), "LANG": LANG, "DIR": "rtl" if LANG in RTL else "ltr",
        "ARROW_PREV": "→" if LANG in RTL else "←", "ARROW_NEXT": "←" if LANG in RTL else "→", "OGLOCALE": OGLOCALE[LANG], "FONTS": html.escape(fonts),
        "BOOKTITLE": html.escape(BOOKTITLE), "AUTHOR": html.escape(AUTHOR),
        "TITLE": html.escape((pg["kicker"] + ". " if pg["kicker"] else "") + plain_title),
        "KICKER": html.escape(pg["kicker"]),
        "FTITLE": pg["ftitle"], "STITLE": pg["stitle"] or pg["ftitle"],
        "HASSHORT": "true" if pg["shorthtml"] else "false",
        "PREV": f'{prev["slug"]}.html' if prev else "../../#toc",
        "PREV_TITLE": html.escape(re.sub(r"<[^>]+>", "", html.unescape(prev["ftitle"])).strip()) if prev else "",
        "NEXT": f'{nxt["slug"]}.html' if nxt else "../../#toc",
        "NEXT_TITLE": html.escape(re.sub(r"<[^>]+>", "", html.unescape(nxt["ftitle"])).strip()) if nxt else "",
        "SLUG": pg["slug"], "NAV": json.dumps(nav, ensure_ascii=False).replace("</", "<\\/"),
        "DESC": description(pg["fullhtml"]), "CANON": url, "ALTERNATES": alternates, "EDITIONS": editions,
        "JSONLD": json.dumps({"@context": "https://schema.org", "@type": "Chapter",
                              "name": plain_title, "url": url,
                              **({"position": pg["n"]} if "n" in pg else {}),
                              "inLanguage": HTMLLANG.get(LANG, LANG), "isAccessibleForFree": True,
                              "license": BOOK["license"], "author": BOOK["author"],
                              "isPartOf": BOOK}, ensure_ascii=False).replace("</", "<\\/"),
        **{"UI_" + k.upper(): html.escape(v) for k, v in T.items()},
    }
    page = template
    # the text goes in last, so that nothing inside it is mistaken for a placeholder
    for k, v in fill.items():
        page = page.replace("{{" + k + "}}", v)
    page = page.replace("{{FULL}}", pg["fullhtml"]).replace("{{SHORT}}", pg["shorthtml"])
    if pg["slug"].isdigit():  # an empty same-page chapter reference (see relink): this chapter's number
        page = re.sub(r'<a href="(#[^"]*)"></a>', lambda m: f'<a href="{m.group(1)}">{int(pg["slug"])}</a>', page)
    (out / f"{pg['slug']}.html").write_text(page, encoding="utf-8")

print("\n".join(report))
print(f"{LANG}: {len(pages)} pages, {len(list((out / 'img').glob('*.svg')))} figures -> {out}")
