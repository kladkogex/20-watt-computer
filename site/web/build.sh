#!/usr/bin/env bash
# Build the web edition into _site/read/ (run from the repository root; needs Docker).
# Both editions are converted from the LaTeX sources with make4ht (TeX4ht): the full book and the
# paperback. Every chapter page carries both texts, and the reader switches «Коротко / Полностью».
set -euo pipefail
out=${1:-_site/read}
tmp=$(mktemp -d)
if [ -n "${KEEP:-}" ]; then echo "work dir: $tmp"; else trap 'rm -rf "$tmp"' EXIT; fi
cp -r ru figures "$tmp"/
cp site/web/web.cfg "$tmp"/ru/
python3 site/web/prep.py "$tmp"/ru
printf '%s\n' '\def\pgfsysdriver{pgfsys-dvisvgm4ht.def}' '\input{main}' > "$tmp"/ru/full.tex
printf '%s\n' '\def\pgfsysdriver{pgfsys-dvisvgm4ht.def}' '\input{paperback/main}' > "$tmp"/ru/short.tex
for job in full short; do
  # make4ht's default DOM filters decode &#x003C; in MathML back to a bare "<", so they are off;
  # site/web/post.py does the clean-up instead
  docker run --rm -u "$(id -u):$(id -g)" -v "$tmp":/w -e HOME=/tmp -e TEXINPUTS=/w/ru:/w: -w /w/ru texlive/texlive \
    make4ht -u -f html5-common_domfilters -c web.cfg -d "/w/html-$job" -j "$job" "$job.tex" > "$tmp/$job.log" 2>&1 \
    || { tail -20 "$tmp/$job.log"; exit 1; }
  if grep -a -q '^! ' "$tmp/ru/$job.log"; then
    echo "TeX errors in the $job edition:"; grep -a -A2 '^! ' "$tmp/ru/$job.log" | head -30; exit 1
  fi
done
python3 site/web/post.py "$tmp/html-full" "$tmp/html-short" "$out"
