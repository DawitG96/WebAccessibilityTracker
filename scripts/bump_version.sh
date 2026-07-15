#!/bin/sh
# Incrementa la patch version (X.Y.Z -> X.Y.Z+1) nel file VERSION alla radice del progetto.
set -e
cd "$(dirname "$0")/.."

VERSION_FILE="VERSION"
current=$(tr -d '[:space:]' < "$VERSION_FILE")
major=$(echo "$current" | cut -d. -f1)
minor=$(echo "$current" | cut -d. -f2)
patch=$(echo "$current" | cut -d. -f3)
new_version="$major.$minor.$((patch + 1))"

echo "$new_version" > "$VERSION_FILE"
echo "Versione: $current -> $new_version"
