#!/usr/bin/env bash
# Build the web edition into _site/read/<lang>/ for every edition (run from the repository root; needs Docker).
# Each edition (full book + paperback) is converted from LaTeX with make4ht (TeX4ht): pdflatex for the
# Latin/Cyrillic editions, xelatex for zh, ja, ko. Every chapter page carries both texts and the reader
# switches between the short and the full one. A CJK edition that fails to convert is skipped (PDF only);
# any other failure stops the build.
#   WEB_LANGS="en ru"  bash site/web/build.sh _site/read     # a subset
#   KEEP=1 ...                                                # keep the work directory
set -euo pipefail
ulimit -f 4194304   # no file written by this script may exceed 4 GB (the host-side logs included)
# Guard rail: every TeX run may write at most 2 GB per file (a TeX error loop in
# nonstopmode can otherwise write an endless log); all engine output goes to log files, never to the console.
out=${1:-_site/read}
# Every edition; one whose sources are incomplete (e.g. still being translated) is skipped.
langs=${WEB_LANGS:-ru en es pt uk fr vi zh ja ko ar}
# TeX4ht draws the TikZ figures through DVI and dvisvgm, which loses CJK and Arabic OpenType text in labels;
# for these editions the figures come from the edition's own PDF engine instead (site/web/figs.py; needs
# pdftocairo and pdfinfo from poppler-utils on the host).
figs_from_pdf=${FIGS_FROM_PDF:-zh ja ko ar}
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
  case " $figs_from_pdf " in *" $lang "*)
    # an untouched copy (the book's own preamble and fonts) for the figures, see site/web/figs.py
    mkdir -p "$tmp/figs-$lang"; cp -r "$lang" figures "$tmp/figs-$lang/"
    python3 site/web/figs.py prepare "$tmp/figs-$lang/$lang" ;;
  esac
done

convert() {  # convert <lang> <job>: prints "ok <lang> <job>" or "fail <lang> <job>"
  local lang=$1 job=$2 x=""
  # zh, ja: xelatex (TeX4ht registers every Unicode character: extra memory); ko, ar: lualatex (see prep.py)
  case $lang in zh|ja) x="-x" ;; ko|ar) x="-l" ;; esac
  # make4ht's default DOM filters decode &#x003C; in MathML back to a bare "<", so they are off;
  # site/web/post.py does the clean-up instead
  if docker run --rm --ulimit fsize=2147483648 -u "$(id -u):$(id -g)" -v "$tmp/$lang":/w -e HOME=/tmp -e TEXINPUTS="/w/$lang:/w:" \
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
          | xargs -r -P 3 -L 1 bash -c 'convert "$0" "$1"')
echo "$results"

# figures from the PDF engine: one tight page per tikzpicture, in the order TeX4ht numbers its SVGs
figures() {  # figures <lang> <job>
  local lang=$1 job=$2 eng=pdflatex
  case $lang in zh|ja|ko) eng=xelatex ;; ar) eng=lualatex ;; esac
  for pass in 1 2; do
    docker run --rm --ulimit fsize=2147483648 -u "$(id -u):$(id -g)" -v "$tmp/figs-$lang":/w -e HOME=/tmp -e TEXINPUTS="/w/$lang:/w:" \
      -w "/w/$lang" texlive/texlive $eng -interaction=nonstopmode "figs-$job.tex" > /dev/null 2>&1 || true
  done
  if [ -f "$tmp/figs-$lang/$lang/figs-$job.pdf" ] && [ -d "$tmp/$lang/html-$job" ]; then
    python3 "$repo/site/web/figs.py" replace "$tmp/figs-$lang/$lang/figs-$job.pdf" "$tmp/$lang/html-$job" "$job" || true
  else
    echo "WARNING figures $lang $job: no PDF; keeping TeX4ht figures"
  fi
}
export -f figures; export repo
for lang in $figs_from_pdf; do
  if [ -d "$tmp/figs-$lang" ] && echo "$results" | grep -q "^ok $lang full$"; then printf '%s full\n%s short\n' "$lang" "$lang"; fi
done | xargs -r -P 3 -L 1 bash -c 'figures "$0" "$1"'

built=""
for lang in $langs; do
  if echo "$results" | grep -q "^ok $lang full$" && echo "$results" | grep -q "^ok $lang short$"; then
    built="$built $lang"
  elif [ -d "$tmp/$lang" ]; then
    # an edition that does not convert (e.g. still being translated) stays PDF-only; the site lists only built ones
    echo "WARNING web edition: $lang not converted, PDF only"; { grep -a -m3 -A2 "^! " "$tmp/$lang/$lang/"*.log 2>/dev/null | head -12; } || true
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
