-- Live citation keys pulled directly from your Zotero database (no manual export).
--   :Zseek [pattern] open a Telescope picker (whole library if no pattern)
--   <leader>zc       insert a citekey via Telescope, seeded from the word
--                    under/before the cursor (normal mode)
--   <leader>zf       same, but always opens on the whole library (normal mode)
--   @<letters>       insert-mode auto-completion by author/title
-- NOT usable under tmux: zotcite's own insert-mode <C-x><C-b> picker. C-b is
-- the tmux prefix, so the second half of the chord never reaches Neovim -- see
-- the comment on the keymaps below.
-- Requires Zotero (with Better BibTeX) and the sqlite3 command-line tool.
return {
  "jalvesaq/zotcite",
  dependencies = {
    "nvim-treesitter/nvim-treesitter",
    "nvim-telescope/telescope.nvim",
  },
  ft = { "markdown" },
  config = function()
    require("zotcite").setup({
      -- Insert Better BibTeX keys so they match a BBT-exported references.bib.
      key_type = "better-bibtex",
      -- Turn off zotcite's own citation highlighting. It hard-codes the
      -- `Identifier` group (looks like a link) AND conceals the leading `@`.
      -- We colour citations ourselves via the after/queries markdown_inline
      -- query (`@markup.citation`), which keeps the `@` visible so a citation
      -- is easy to spot as a citation rather than a link.
      hl_cite_key = false,
    })
    -- zotcite's built-in citation picker is <C-x><C-b>, but <C-b> is the tmux
    -- prefix and never reaches Neovim. Add a tmux-safe normal-mode trigger.
    -- It fits zotcite's existing <leader>z* family (zo/zi/za/zb) and drops you
    -- into insert mode right after the inserted key. (In insert mode, just type
    -- @ for the blink menu, or <C-x><C-o> for omni-completion.)
    local function set_zotcite_keymaps(bufnr)
      vim.keymap.set("n", "<leader>zc", function()
        require("zotcite.get").citation()
      end, { buffer = bufnr, desc = "Zotcite: insert citation (picker)" })

      -- <leader>zc seeds the picker from whatever word is under/before the
      -- cursor, which is fine most of the time but inherits the same
      -- single-word limit as the @-trigger (zotcite's own LSP completion
      -- only ever captures a %S+ token). This variant always opens with
      -- the full library so a multi-word author/title query can be typed
      -- straight into Telescope's own fuzzy prompt instead.
      vim.keymap.set("n", "<leader>zf", function()
        local seek = require("zotcite.seek")
        local rownr = vim.api.nvim_win_get_cursor(0)[1] - 1
        local col = vim.api.nvim_win_get_cursor(0)[2]
        seek.refs("", function(ref)
          if not ref then return end
          local kt = require("zotcite.config").get_key_type(vim.api.nvim_get_current_buf())
          local cite = kt == "zotero" and ref.value.key or ref.value.cite
          if not (vim.bo.filetype == "tex" or vim.bo.filetype == "rnoweb") then
            cite = "@" .. cite
          end
          vim.api.nvim_buf_set_text(0, rownr, col, rownr, col, { cite })
          vim.api.nvim_win_set_cursor(0, { rownr + 1, col + #cite })
          vim.schedule(require("zotcite.hl").citations)
        end)
      end, { buffer = bufnr, desc = "Zotcite: insert citation (full-library picker)" })
    end

    -- `ft = { "markdown" }` above means lazy.nvim loads this config() in
    -- response to the FileType event firing on the buffer you're already in
    -- -- so a FileType autocmd registered here would never fire for that
    -- same buffer (only for markdown buffers opened afterwards). Apply the
    -- keymaps immediately to the current buffer too, or <leader>zc/<leader>zf
    -- silently fall through to Vim's builtin zc/zf fold commands instead.
    set_zotcite_keymaps(vim.api.nvim_get_current_buf())
    vim.api.nvim_create_autocmd("FileType", {
      pattern = "markdown",
      callback = function(ev) set_zotcite_keymaps(ev.buf) end,
    })

    -- Style citations so they read as references, not bare links.
    -- The after/queries/markdown_inline/highlights.scm query captures
    -- `[@citekey]` shortcut links as `@markup.citation` (priority 5000, so it
    -- beats zotcite's Identifier extmark). Here we give that group a muted,
    -- non-underlined italic look borrowed from the theme's `Special` colour.
    -- Change the `fg`/attrs below to taste (e.g. link to "Comment" for a
    -- fainter aside, or "Number"/"Constant" for more presence).
    local function set_citation_hl()
      local special = vim.api.nvim_get_hl(0, { name = "Special", link = false })
      vim.api.nvim_set_hl(0, "@markup.citation", {
        fg = special.fg,
        italic = true,
        underline = false,
      })
    end
    set_citation_hl()
    vim.api.nvim_create_autocmd("ColorScheme", { callback = set_citation_hl })
  end,
}
