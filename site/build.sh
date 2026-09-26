#!/usr/bin/env bash
# Assemble the static website into _site/ (run from the repository root).
# Used by site/deploy.sh, which publishes _site/ to the gh-pages branch.
set -euo pipefail
rm -rf _site
mkdir -p _site/breadboard _site/pdf
cp site/index.html _site/
cp ru/20-watt-computer-ru.pdf ru/20-watt-computer-ru-paperback.pdf _site/pdf/
# breadboard.html is a page fragment (title, styles, markup, script); wrap it into a full document
{
  printf '<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
  printf '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
  printf '<style>[hidden]{display:none!important}body{margin:0}</style>\n</head>\n<body>\n'
  cat site/breadboard/breadboard.html
  printf '\n</body>\n</html>\n'
} > _site/breadboard/index.html
touch _site/.nojekyll
echo "site assembled in _site/"
