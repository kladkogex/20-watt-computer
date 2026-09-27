"""Figures for the web edition from the real PDF engine (used for zh, ja, ko, ar).

TeX4ht draws the TikZ figures through DVI and dvisvgm, which loses the CJK and Arabic OpenType text in their
labels. For those editions build.sh instead typesets the edition itself with its own engine and preamble
(xelatex + ctex/xeCJK/kotex, lualatex + babel bidi) and the `preview` package, which ships one tight page per
tikzpicture, in execution order. TeX4ht places each figure's image where the picture is in the text (its file
numbers need not follow that order), so PDF page N becomes, with pdftocairo (glyphs as paths, so no web fonts are
needed), the SVG of the N-th figure image in reading order. If the counts differ, the TeX4ht figures are kept and a
warning is printed.

    python3 figs.py prepare <src-dir>          # writes figs-full.tex and figs-short.tex next to main.tex
    python3 figs.py replace <pdf> <html-dir> <job>
"""
import pathlib, re, subprocess, sys

# The yellow key boxes are tcolorboxes, which draw with a tikzpicture of their own: make them plain paragraphs
# here so that only the book's figures become pages.
PREVIEW = ("\\usepackage[active,tightpage]{preview}\n\\PreviewEnvironment{tikzpicture}\n\\setlength\\PreviewBorder{2pt}\n"
           "\\makeatletter\\@ifundefined{keyblock}{}{\\renewenvironment{keyblock}{\\par}{\\par}}\\makeatother\n")


def prepare(src):
    src = pathlib.Path(src)
    for main, out in ((src / "main.tex", src / "figs-full-main.tex"),
                      (src / "paperback" / "main.tex", src / "paperback" / "figs-short-main.tex")):
        s = main.read_text(encoding="utf-8")
        # the covers are print artwork (the web reader keeps the plain title): not figures of the web pages
        s = re.sub(r"^\\input\{(?:paperback/cover|figures/bookcover)\}.*$", "", s, flags=re.M)
        i = s.index("\\begin{document}")
        out.write_text(s[:i] + PREVIEW + s[i:], encoding="utf-8")
    (src / "figs-full.tex").write_text("\\input{figs-full-main}\n", encoding="utf-8")
    (src / "figs-short.tex").write_text("\\input{paperback/figs-short-main}\n", encoding="utf-8")


def html_order(html, job):
    """TeX4ht's HTML files in reading order: anchors are numbered x<file>-..., <file> growing through the book."""
    def key(f):
        m = re.search(r"id=[\"']x(\d+)-", f.read_text(encoding="utf-8", errors="ignore"))
        return int(m.group(1)) if m else (0 if f.name == f"{job}.html" else 10 ** 9)
    return sorted(html.glob(f"{job}*.html"), key=key)


def replace(pdf, html, job):
    """PDF page N (the N-th tikzpicture typeset) replaces the SVG of the N-th figure image in reading order."""
    html = pathlib.Path(html)
    info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
    pages = int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1))
    imgs = []
    for f in html_order(html, job):
        for m in re.finditer(r"src=[\"']((?:full|short)\d+x\.svg)[\"']", f.read_text(encoding="utf-8", errors="ignore")):
            if m.group(1) not in imgs:
                imgs.append(m.group(1))
    if len(imgs) != pages:
        print(f"WARNING figures {job}: {pages} PDF pages but {len(imgs)} figures in the HTML; keeping TeX4ht figures")
        return 1
    for k, name in enumerate(imgs, start=1):
        svg = html / name
        subprocess.run(["pdftocairo", "-svg", "-f", str(k), "-l", str(k), pdf, str(svg)], check=True)
        # pdftocairo writes unitless sizes (read as px); TeX4ht's figures are sized in pt: keep the same scale
        t = svg.read_text(encoding="utf-8")
        t = re.sub(r'(<svg\b[^>]*?\bwidth=")([\d.]+)(")', r"\1\2pt\3", t, count=1)
        t = re.sub(r'(<svg\b[^>]*?\bheight=")([\d.]+)(")', r"\1\2pt\3", t, count=1)
        svg.write_text(t, encoding="utf-8")
    print(f"figures {job}: {pages} figures from the PDF engine")
    return 0


if __name__ == "__main__":
    if sys.argv[1] == "prepare":
        prepare(sys.argv[2])
    else:
        sys.exit(replace(*sys.argv[2:5]))
