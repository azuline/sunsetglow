#!/usr/bin/env bash

set -euxo pipefail

# Prepare a clean dist directory.
rm -rf dist/
mkdir dist

# Directly copy over all assets.
cp -r src/assets dist/assets
# Directly copy over all HTML files.
find src/ -type f -name "*.html" -print0 | while IFS= read -r -d '' file; do
    cp "$file" "${file/#src/dist}"
done
# Compile LaTex blog posts.
find src/ -type f -name "*.tex" -print0 | while IFS= read -r -d '' file; do
    out="$(echo "$file" | perl -pe 's/^src\/(.*)\.tex/dist\/\1.html/')"
    mkdir --parents "$(dirname "$out")"
    pandoc --standalone "$file" --table-of-contents -o "$out"
    perl -0777 -i -pe 's/^.*?<body>\s*(.*?)\s*<\/body>\s*<\/html>\s*$/\1/s' "$out"
done
