-- ~/.config/nvim-common/lua/common/surround.lua
-- Add/change/delete surrounding pairs -- quotes, brackets, HTML tags, and
-- (for prose) markdown emphasis markers. This is nvim-surround, the maintained
-- Lua rewrite of tpope/vim-surround; the core keymaps are the same.
--
--   ys{motion}{char}  add a surround      ysiw"  ->  word becomes "word"
--   yss{char}         surround the line
--   S{char}           surround the visual selection
--   cs{old}{new}      change a surround   cs"'   ->  "word" becomes 'word'
--   ds{char}          delete a surround   ds"    ->  "word" becomes word
--
-- Openers add a space inside, closers don't: ys$( -> ( text ), ys$) -> (text).
-- `t` targets an HTML/JSX tag (cst renames it), `f` a function call.
-- In markdown, ysiw* italicises a word and ysiw` makes it inline code.
-- Returns a lazy.nvim plugin spec.

return {
  "kylechui/nvim-surround",
  version = "*",       -- latest stable release
  event = "VeryLazy",  -- nothing is needed until you're actually editing
  opts = {},           -- defaults; setup() is called by lazy with these
}
