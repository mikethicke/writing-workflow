# nvim

A Neovim config for writing prose, not code. Separate from any coding config —
it runs under its own `NVIM_APPNAME`, so the two never fight over keymaps,
plugins, or `wrap`.

## Install

```bash
ln -s "$PWD/nvim" ~/.config/nvim-prose
alias vprose='NVIM_APPNAME=nvim-prose nvim'
```

First launch bootstraps [lazy.nvim](https://github.com/folke/lazy.nvim) and
installs everything. `lazy-lock.json` pins the versions that are known to work.

Optional, for citations: Zotero with
[Better BibTeX](https://retorque.re/zotero-better-bibtex/), which
[zotcite](https://github.com/jalvesaq/zotcite) reads.

## What it does differently from a coding config

**Prose reads by paragraph, not by line.** `wrap`, `linebreak`, and `breakindent`
are on, and `j`/`k` move by *display* line so a wrapped paragraph navigates the
way it looks. A count still uses logical lines, so `5j` with relative numbers
does what you expect. `H`/`L` go to the start/end of the display line.

**A live word count** sits in the statusline, via Vim's native `wordcount()`.
The statusline re-evaluates on redraw, so it updates as you type with no autocmd.
With a visual selection active it shows `selected / total`.

**Three degrees of distraction-free**, because they do different jobs:

| key | plugin | effect |
| --- | --- | --- |
| — | no-neck-pain | pads the sides to a fixed 100-column writing column; on by default |
| `<leader>n` | no-neck-pain | toggle that margin |
| `<leader>z` | zen-mode | centre the text, hide all UI chrome |
| — | twilight | dim everything except the paragraph you're in |

**Citations are first-class.** `spell` is on, `conceallevel=2` lets
render-markdown hide the raw syntax, and pandoc-style `[@citekey]` citations get
their own highlight so they don't look like broken links — see
`after/queries/markdown_inline/highlights.scm` for why that needs a custom
treesitter query.

## Keymaps

Leader is `<Space>`.

| key | does |
| --- | --- |
| `<leader>zc` | zotcite picker, seeded from the word under the cursor |
| `<leader>zf` | zotcite picker over the whole library |
| `<leader>pp` | export the current file to PDF via pandoc (uses `references.bib` if present) |
| `<leader>ps` | push the current file to a Substack draft |
| `<leader>n` / `<leader>z` | writing margin / zen mode |
| `<leader>ff` `<leader>fg` `<leader>fb` `<leader>fh` | telescope: files, grep, buffers, help |
| `<leader>w` | write |

`:SubstackDraft` does the same as `<leader>ps`.

`<leader>ps` shells out to `../publish/publish_draft.py`. If you keep this repo
somewhere other than `~/github/writing-workflow`, set the path before the config
loads:

```lua
vim.g.substack_publish_dir = "/path/to/writing-workflow/publish"
```

## Layout

```
init.lua                 options, keymaps, statusline, pandoc + Substack commands
lua/common/              modules shared with the author's coding config, vendored
lua/plugins/             colorscheme, focus modes, markdown rendering, treesitter, zotero
after/queries/           the citation highlight query
sync-from-dotfiles.sh    re-export from the upstream dotfiles repo
```

`lua/common/` is vendored so this config stands alone. Upstream it lives in a
separate `nvim-common` directory shared with a coding config; `sync-from-dotfiles.sh`
re-flattens it and reapplies the two edits that make the copy standalone. If you
are not me, ignore that script — this directory is the whole config.
