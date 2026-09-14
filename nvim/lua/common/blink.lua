-- ~/.config/nvim-common/lua/common/blink.lua
-- Shared completion engine, used by both the coding and prose configs.
-- Its LSP source surfaces zotcite's zotero_ls citations, so typing `@` plus a
-- few letters pops a live citation menu; it also completes paths, snippets,
-- and buffer words.
-- Returns a lazy.nvim plugin spec.

return {
  "saghen/blink.cmp",
  -- version = "1.*" fetches a release with a prebuilt fuzzy-matcher binary, so
  -- no Rust toolchain is needed. It falls back to a Lua matcher (with a
  -- warning) if the download is ever unavailable.
  version = "1.*",
  opts = {
    -- 'default' preset leaves <CR> free to insert newlines (important when
    -- writing prose):
    --   <C-space> open menu   <C-y> accept   <C-e> dismiss
    --   <C-n>/<C-p> or arrows to select
    keymap = {
      preset = "default",
      -- The preset scrolls the docs popup with <C-b>/<C-f>, but <C-b> is the
      -- default tmux prefix and never reaches Neovim. Release both and move
      -- "scroll docs" onto <C-u>/<C-d>. The trailing "fallback" keeps those
      -- keys' normal insert-mode behavior whenever no docs popup is open.
      ["<C-b>"] = {},
      ["<C-f>"] = {},
      ["<C-u>"] = { "scroll_documentation_up", "fallback" },
      ["<C-d>"] = { "scroll_documentation_down", "fallback" },
      -- Tab accepts the selected suggestion; Esc dismisses the menu. Each
      -- falls back to its normal insert-mode behavior when no menu is open,
      -- so Tab still indents and Esc still leaves insert mode as usual.
      ["<Tab>"] = { "select_and_accept", "fallback" },
      ["<Esc>"] = { "hide", "fallback" },
    },
    completion = { documentation = { auto_show = true } },
    sources = { default = { "lsp", "path", "snippets", "buffer" } },
  },
}
