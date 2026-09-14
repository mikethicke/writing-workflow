#!/usr/bin/env bash
# Re-export the prose config from the dotfiles repo into this directory.
#
# dotfiles is the source of truth; this directory is a published snapshot that
# flattens nvim-prose together with the nvim-common modules it depends on. The
# two local edits that make the snapshot standalone -- dropping the
# ~/.config/nvim-common runtimepath prepend, and defaulting the publish-tool
# path to this repo -- are reapplied here, so re-running this is safe.
#
# Usage:  ./sync-from-dotfiles.sh [path-to-dotfiles/config]
set -euo pipefail

SRC="${1:-$HOME/dotfiles/config}"
DEST="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for d in "$SRC/nvim-prose" "$SRC/nvim-common"; do
  [ -d "$d" ] || { echo "not found: $d" >&2; exit 1; }
done

cp "$SRC/nvim-prose/init.lua"       "$DEST/init.lua"
cp "$SRC/nvim-prose/lazy-lock.json" "$DEST/lazy-lock.json"
cp "$SRC/nvim-prose/lua/plugins/"*.lua "$DEST/lua/plugins/"
cp "$SRC/nvim-common/lua/common/"*.lua "$DEST/lua/common/"
mkdir -p "$DEST/after/queries/markdown_inline"
cp "$SRC/nvim-prose/after/queries/markdown_inline/highlights.scm" \
   "$DEST/after/queries/markdown_inline/"

python3 - "$DEST/init.lua" <<'PY'
import io, re, sys
path = sys.argv[1]
s = io.open(path, encoding="utf-8").read()

s = s.replace(
    """-- ~/.config/nvim-prose/init.lua
-- Neovim configuration for PROSE / long-form markdown writing.
""",
    """-- init.lua -- Neovim configuration for PROSE / long-form markdown writing.
--
-- Install by pointing NVIM_APPNAME at this directory, e.g.
--   ln -s ~/github/writing-workflow/nvim ~/.config/nvim-prose
--   alias vprose='NVIM_APPNAME=nvim-prose nvim'
--
-- This is a self-contained snapshot: the modules under lua/common/ are shared
-- with the author's separate coding config, vendored here so the config stands
-- alone. See nvim/README.md.
""")

# lua/common/ is local here, so the shared-config runtimepath hook is dead weight.
s = re.sub(
    r"-- \d+\. Make the shared modules in ~/\.config/nvim-common available\.\n"
    r"vim\.opt\.runtimepath:prepend\(vim\.fn\.expand\(\"~/\.config/nvim-common\"\)\)\n\n"
    r"-- \d+\. Options and keymaps shared with the coding config\.\n",
    "-- 2. Options and keymaps shared with the coding config (vendored in\n"
    "--    lua/common/, so they resolve from this config's own runtimepath).\n",
    s)

# The author's path points into the private substack repo; ours must not.
s = re.sub(
    r'local substack_dir = vim\.fn\.expand\("[^"]*"\)',
    '--\n'
    "--    Override the tool's location by setting vim.g.substack_publish_dir before\n"
    '--    this file loads; otherwise it is expected at the path below.\n'
    'local substack_dir = vim.g.substack_publish_dir\n'
    '  or vim.fn.expand("~/github/writing-workflow/publish")',
    s)

# Dropping that section leaves a hole in the numbering: upstream's 3 became our
# 2 (written literally above), so every later header shifts down by one.
def shift(m):
    return "-- %d%s." % (int(m.group(1)) - 1, m.group(2))

s = re.sub(r"^-- ([4-9]|[1-9]\d)([a-z]?)\.", shift, s, flags=re.M)

io.open(path, "w", encoding="utf-8").write(s)
PY

echo "synced from $SRC"
echo "review the diff before committing."
