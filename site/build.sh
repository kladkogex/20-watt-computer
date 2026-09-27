#!/usr/bin/env bash
# Assemble the static website into _site/ (run from the repository root; the web edition needs Docker).
# Used by site/deploy.sh, which publishes _site/ to the gh-pages branch.
set -euo pipefail
rm -rf _site
mkdir -p _site/breadboard _site/pdf
cp site/index.html _site/
cp site/og-card.png _site/
mkdir -p _site/author && cp site/author/index.html _site/author/
# every edition that has been built: ru, en, zh, ja, ko, es, pt (full book and paperback)
cp */20-watt-computer-*.pdf _site/pdf/
# breadboard.html is a page fragment (title, styles, markup, script); wrap it into a full document
{
  printf '<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
  printf '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
  printf '%s\n' '<script>try{var t=localStorage.getItem("20w-theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t);}catch(e){}</script>'
  printf '%s\n' '<meta property="og:title" content="Neuron breadboard: build the machine yourself">' '<meta property="og:description" content="Wire up spiking neurons in your browser: 13 challenges from logic gates to dopamine learning, scored in neurons, spikes and picojoules.">' '<meta property="og:image" content="https://kladkogex.github.io/20-watt-computer/og-card.png">' '<meta name="twitter:card" content="summary_large_image">'
  printf '<style>[hidden]{display:none!important}body{margin:0}</style>\n</head>\n<body>\n'
  cat site/breadboard/breadboard.html
  printf '\n</body>\n</html>\n'
} > _site/breadboard/index.html
# the web edition: every chapter as a page (LaTeX -> HTML with make4ht; needs Docker)
bash site/web/build.sh _site/read
cp site/llms.txt _site/
# sitemap for search engines (submit https://kladkogex.github.io/20-watt-computer/sitemap.xml in Search Console)
base=https://kladkogex.github.io/20-watt-computer/
{
  printf '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
  for u in "" breadboard/ author/ $(cd _site && ls read/*/*.html pdf/*.pdf); do
    printf '  <url><loc>%s%s</loc></url>\n' "$base" "$u"
  done
  printf '</urlset>\n'
} > _site/sitemap.xml
touch _site/.nojekyll
echo "site assembled in _site/"
