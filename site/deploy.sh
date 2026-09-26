#!/usr/bin/env bash
# Build the website and publish it to the gh-pages branch (GitHub Pages serves that branch).
# Run from the repository root: bash site/deploy.sh
set -euo pipefail
bash site/build.sh
rev=$(git rev-parse --short HEAD)
tmp=$(mktemp -d)
cp -r _site/. "$tmp"/
cd "$tmp"
git init -q -b gh-pages
git add -A
git -c user.name="$(git -C "$OLDPWD" config user.name)" -c user.email="$(git -C "$OLDPWD" config user.email)" \
    commit -q -m "Deploy website from $rev"
git push -q -f "$(git -C "$OLDPWD" remote get-url origin)" gh-pages
cd "$OLDPWD"; rm -rf "$tmp"
echo "published gh-pages from $rev"
