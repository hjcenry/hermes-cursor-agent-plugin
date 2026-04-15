#!/usr/bin/env sh
# Install Hermes cursor_agent plugin into ~/.hermes/plugins/cursor-agent
# Optionally create ~/.hermes/cursor_agent.json from example if missing.
# Usage: ./install.sh   (run from this directory or pass PLUGIN_SRC as first arg)

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SRC=${1:-"$SCRIPT_DIR"}

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
DEST="$HERMES_HOME/plugins/cursor-agent"
CFG="$HERMES_HOME/cursor_agent.json"
EXAMPLE="$SRC/cursor_agent.example.json"

if [ ! -f "$SRC/plugin.yaml" ] || [ ! -f "$SRC/__init__.py" ]; then
  echo "error: plugin.yaml / __init__.py not found under: $SRC" >&2
  exit 1
fi

mkdir -p "$DEST"

for name in \
  plugin.yaml __init__.py config.py parser.py formatter.py \
  resolve_binary.py process_registry.py runner.py \
  TECHNICAL_DESIGN.md .gitignore cursor_agent.example.json
do
  if [ -f "$SRC/$name" ]; then
    cp -f "$SRC/$name" "$DEST/"
  fi
done

echo "Installed plugin to: $DEST"

if [ -f "$CFG" ]; then
  echo "Config already exists (not overwritten): $CFG"
else
  if [ -f "$EXAMPLE" ]; then
    cp -f "$EXAMPLE" "$CFG"
    echo "Created config from example: $CFG"
    echo '  Edit "projects" and paths before use.'
  else
    echo "No example JSON found; create manually: $CFG"
  fi
fi

echo "Restart Hermes Gateway / CLI to load the plugin."
