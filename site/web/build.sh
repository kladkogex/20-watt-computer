#!/usr/bin/env bash
# Build the web edition into _site/read/<lang>/ for every edition (run from the repository root; needs Docker).
# Each edition (full book + paperback) is converted from LaTeX with make4ht (TeX4ht): pdflatex for the
# Latin/Cyrillic editions, xelatex for zh, ja, ko. Every chapter page carries both texts and the reader
# switches between the short and the full one. A CJK edition that fails to convert is skipped (PDF only);
# any other failure stops the build.
#   WEB_LANGS="en ru"  bash site/web/build.sh _site/read     # a subset
#   KEEP=1 ...                                                # keep the work directory
set -euo pipefail
out=${1:-_site/read}
# Default: the Latin- and Cyrillic-script editions (an edition whose sources are incomplete is skipped).
# zh, ja, ko and ar convert (see the engines below), but the text labels inside their TikZ figures are lost:
# dvisvgm does not draw their OpenType CJK/Arabic glyphs from TeX4ht's DVI. Until that is solved they stay
# PDF-only; build them explicitly with WEB_LANGS to work on it.
langs=${WEB_LANGS:-ru en es pt uk fr vi}
repo=$(pwd)
tmp=$(mktemp -d)
if [ -n "${KEEP:-}" ]; then echo "work dir: $tmp"; else trap 'rm -rf "$tmp"' EXIT; fi

# one source tree per edition: <lang>/, figures/, the TeX4ht config and the source adjustments
for lang in $langs; do
  [ -f "$lang/main.tex" ] && [ -f "$lang/paperback/main.tex" ] || { echo "skip $lang: no sources"; continue; }
  mkdir -p "$tmp/$lang"
  cp -r "$lang" figures "$tmp/$lang/"
  cp site/web/web.cfg "$tmp/$lang/$lang/"
  python3 site/web/prep.py "$tmp/$lang/$lang"
  printf '%s\n' '\def\pgfsysdriver{pgfsys-dvisvgm4ht.def}' '\input{main}' > "$tmp/$lang/$lang/full.tex"
  printf '%s\n' '\def\pgfsysdriver{pgfsys-dvisvgm4ht.def}' '\input{paperback/main}' > "$tmp/$lang/$lang/short.tex"
done

convert() {  # convert <lang> <job>: prints "ok <lang> <job>" or "fail <lang> <job>"
  local lang=$1 job=$2 x=""
  # zh, ja: xelatex (TeX4ht registers every Unicode character: extra memory); ko, ar: lualatex (see prep.py)
  case $lang in zh|ja) x="-x" ;; ko|ar) x="-l" ;; esac
  # make4ht's default DOM filters decode &#x003C; in MathML back to a bare "<", so they are off;
  # site/web/post.py does the clean-up instead
  if docker run --rm -u "$(id -u):$(id -g)" -v "$tmp/$lang":/w -e HOME=/tmp -e TEXINPUTS="/w/$lang:/w:" \
       -e extra_mem_bot=30000000 -e extra_mem_top=30000000 \
       -w "/w/$lang" texlive/texlive make4ht $x -u -f html5-common_domfilters -c web.cfg -d "/w/html-$job" -j "$job" "$job.tex" \
       > "$tmp/$lang/$job.log" 2>&1 && ! grep -a -q '^! ' "$tmp/$lang/$lang/$job.log" \
       && ls "$tmp/$lang/html-$job/${job}ch1.html" >/dev/null 2>&1; then
    echo "ok $lang $job"
  else
    echo "fail $lang $job"
  fi
}
export -f convert; export tmp
results=$(for lang in $langs; do if [ -d "$tmp/$lang" ]; then printf '%s full\n%s short\n' "$lang" "$lang"; fi; done \
          | xargs -P 3 -L 1 bash -c 'convert "$0" "$1"')
echo "$results"

built=""
for lang in $langs; do
  if echo "$results" | grep -q "^ok $lang full$" && echo "$results" | grep -q "^ok $lang short$"; then
    built="$built $lang"
  elif [ -d "$tmp/$lang" ]; then
    # an edition that does not convert (e.g. still being translated) stays PDF-only; the site lists only built ones
    echo "WARNING web edition: $lang not converted, PDF only"; grep -a -m3 -A2 '^! ' "$tmp/$lang/$lang/"*.log 2>/dev/null | head -12
  fi
done
# alphabetical by language code: no edition comes first because it is "the original"
built=$(echo $built | tr " " "\n" | sort | tr "\n" " ")
built=$(echo $built)
case " $built " in *" ru "*) ;; *) echo "the Russian web edition did not convert"; exit 1 ;; esac

mkdir -p "$out"
for lang in $built; do
  python3 site/web/post.py --lang "$lang" --src "$tmp/$lang/$lang" --full "$tmp/$lang/html-full" \
          --short "$tmp/$lang/html-short" --out "$out/$lang" --langs "${built// /,}"
done
# the reader learns which editions exist from this file
python3 -c "import json,sys; json.dump(sys.argv[1:], open('$out/langs.json','w'))" $built

# links shared before the multilingual reader (read/06.html#x9-...) go to the Russian pages
if [ -d "$out/ru" ]; then
  for f in "$out"/ru/*.html; do
    b=$(basename "$f")
    printf '<!doctype html><meta charset="utf-8"><title>…</title><link rel="canonical" href="ru/%s"><script>location.replace("ru/%s"+location.hash)</script><a href="ru/%s">→</a>\n' "$b" "$b" "$b" > "$out/$b"
  done
fi
echo "web edition: $built"
