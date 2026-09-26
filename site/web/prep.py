"""Small source adjustments for the TeX4ht run (applied to a temporary copy, never to the book).

TeX4ht cannot end a longtable caption row with \\ when the first column is \raggedright:
use \tabularnewline there, which means the same thing to LaTeX.
The paperback's collage cover is left out (see below).
"""
import pathlib, re, sys

ru = pathlib.Path(sys.argv[1])
for tex in ru.rglob("*.tex"):
    s = tex.read_text(encoding="utf-8")
    t = re.sub(r"(\\begin\{longtable\}[^\n]*\n\\caption\{[^\n]*?\}(?:\\label\{[^}]*\})?)\\\\", r"\1\\tabularnewline", s)
    if t != s:
        tex.write_text(t, encoding="utf-8")

# The paperback's collage cover is print artwork (and too large for dvisvgm); the web pages don't use it.
pb = ru / "paperback" / "main.tex"
if pb.exists():
    s = pb.read_text(encoding="utf-8")
    pb.write_text(re.sub(r"^\\input\{paperback/cover\}.*$", "", s, flags=re.M), encoding="utf-8")
