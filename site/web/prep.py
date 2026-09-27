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

# Korean: kotex does not run under TeX4ht (neither engine); the web build uses LuaLaTeX with fontspec and the
# Un fonts instead (the HTML text does not depend on TeX fonts; the SVG figures do) and sets the Korean names.
if ru.name == "ko":
    KO = ("\\usepackage{fontspec}\n\\setmainfont{UnBatang}\n\\setsansfont{UnDotum}\n"
          "\\AtBeginDocument{\\renewcommand{\\contentsname}{차례}\\renewcommand{\\figurename}{그림}"
          "\\renewcommand{\\tablename}{표}\\renewcommand{\\bibname}{참고 문헌}\\renewcommand{\\appendixname}{부록}}\n")
    for f in (ru / "main.tex", ru / "paperback" / "main.tex"):
        s = f.read_text(encoding="utf-8")
        s = re.sub(r"^\\set(?:main|sans)hangulfont.*$\n?", "", s, flags=re.M)
        s = s.replace("\\usepackage[hangul]{kotex}\n", KO + "\\providecommand{\\nocompresspunctuations}{}\\providecommand{\\compresspunctuations}{}\n")
        f.write_text(s, encoding="utf-8")

# Ukrainian: TeX4ht writes the Cyrillic appendix letter into its cross-reference file as "\\T2A\\CYRA",
# which TeX reads back as the undefined command \\T; make it harmless (the rest is only part of a key).
if ru.name == "uk":
    f = ru / "main.tex"
    s = f.read_text(encoding="utf-8")
    # number the appendices A-D for TeX4ht's keys; site/web/post.py shows them as А, Б, В, Г again
    # (babel-ukrainian redefines \\Alph to Cyrillic, so spell the letters out)
    s = s.replace("\\appendix\n", "\\appendix\n\\renewcommand{\\thechapter}{\\ifcase\\value{chapter}\\or A\\or B\\or C\\or D\\or E\\or F\\fi}\n", 1)
    f.write_text(s, encoding="utf-8")

# Spanish: babel's Spanish math adjustments break \\int under TeX4ht; es-minimal switches them off for the web
# (decimal points and percent signs are already kept plain in the book).
if ru.name == "es":
    for f in (ru / "main.tex", ru / "paperback" / "main.tex"):
        s = f.read_text(encoding="utf-8")
        s = s.replace("[spanish,", "[spanish,es-minimal,", 1)
        # babel-spanish still breaks amsmath's \\int under TeX4ht ("Limit controls must follow a math operator")
        s = s.replace("\\begin{document}", "\\AtBeginDocument{\\def\\int{\\intop\\nolimits}}\n\\begin{document}", 1)
        f.write_text(s, encoding="utf-8")
