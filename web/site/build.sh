#!/usr/bin/env bash
# Builds site/dist: the landing pages from site/public plus a copy of the web player under /player.
# Runs on Cloudflare before each deploy (wrangler.toml [build]); cratebox.html at the repo root stays the source.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf dist && mkdir -p dist/player
cp -R public/. dist/
for f in cratebox.html index.html sw.js manifest.webmanifest icon-180.png icon-512.png filetest.html; do cp "../$f" dist/player/; done
cp -R ../vendor dist/player/vendor
echo "built site/dist: $(find dist -type f | wc -l) files"
