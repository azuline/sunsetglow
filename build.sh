#!/usr/bin/env bash

set -euxo pipefail

# Prepare a clean dist directory.
rm -rf dist/
mkdir dist

# Directly copy over all assets.
cp -r src/assets dist/assets
# Directly copy over all HTML files.
find src/ -type f -name "*.html" | xargs -I{} sh -c 'cp "{}" "$(echo "{}" | sed "s/^src/dist/")"'
