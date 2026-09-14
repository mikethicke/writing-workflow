-- Treesitter parsers for markdown (used by render-markdown and zotcite).
--
-- This tracks nvim-treesitter's `main` branch. The old `master` branch is
-- frozen at Neovim 0.10/0.11 and crashes on 0.12: it registers its query
-- directives with the pre-0.11 match format (a single TSNode per capture),
-- but Neovim >= 0.11 passes a TSNode *list*. Here that hit markdown's
-- `#set-lang-from-info-string!` directive, so any buffer containing a fenced
-- code block with a language tag (```lua) blew up during render-markdown's
-- async parse with:
--
--   treesitter.lua:197: attempt to call method 'range' (a nil value)
--
-- `main` drops the module system entirely: there is no configs.setup() and no
-- highlight table. Parsers and queries install into stdpath("data")/site
-- (already on the runtimepath) and highlighting is started per-buffer.
--
-- Requires the tree-sitter CLI (>= 0.26.1) and a C compiler on PATH.
--
--   macOS   brew install tree-sitter-cli
--
--   Ubuntu  do NOT use apt: 24.04 ships 0.20.8, 25.10 ships 0.22.6 and even
--           26.04 ships only 0.25.9, all below the 0.26.1 floor (0.20.x has no
--           `tree-sitter build` subcommand at all, which is what installs
--           shell out to). `cargo install tree-sitter-cli` builds rquickjs-sys
--           through bindgen and needs a working libclang. Grab the static
--           binary instead:
--             curl -fsSL https://github.com/tree-sitter/tree-sitter/releases/\
--             latest/download/tree-sitter-linux-x64.gz \
--               | gunzip > ~/.local/bin/tree-sitter && chmod +x $_
--
-- The version floor is only checked by `:checkhealth nvim-treesitter`, never
-- at install time -- too old a CLI fails to build parsers with no warning, so
-- checkhealth is the signal to trust.
--
-- markdown_inline and yaml are never a buffer's own filetype -- markdown
-- injects into them -- but both parsers must be installed for inline markup
-- and YAML front matter to highlight. The custom @markup.citation query in
-- after/queries/markdown_inline/highlights.scm extends whatever
-- markdown_inline highlights.scm ends up on the runtimepath, so it keeps
-- working unchanged.

local parsers = { "markdown", "markdown_inline", "yaml" }

return {
  "nvim-treesitter/nvim-treesitter",
  branch = "main",
  lazy = false,          -- the main branch does not support lazy-loading
  build = ":TSUpdate",
  config = function()
    -- install() skips parsers that are already present, so this only does work
    -- on a fresh clone or when a parser is added to the list above.
    require("nvim-treesitter").install(parsers)

    -- Replaces master's `highlight = { enable = true }`: resolve the filetype
    -- to a parser and start highlighting, quietly doing nothing when no parser
    -- is installed for it.
    vim.api.nvim_create_autocmd("FileType", {
      callback = function(ev)
        local lang = vim.treesitter.language.get_lang(ev.match)
        if not lang or not vim.treesitter.language.add(lang) then
          return
        end
        vim.treesitter.start(ev.buf, lang)
      end,
    })
  end,
}
