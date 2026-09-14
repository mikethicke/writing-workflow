-- Distraction-free writing.
--   No-Neck-Pain pads the sides so the main buffer is a fixed 100-column
--     writing column -- with `wrap` on this soft-wraps prose at 100 chars
--     (no newlines are written to the file). Line numbers, spell, etc. stay.
--     Auto-enabled on start/new tab; toggle manually with <leader>n.
--   Zen Mode centres the text and hides UI chrome (toggle with <leader>z).
--   Twilight dims everything except the paragraph you're in.
return {
  {
    "shortcuts/no-neck-pain.nvim",
    lazy = false,  -- load at startup so enableOnVimEnter actually fires
    opts = {
      width = 100,
      autocmds = { enableOnVimEnter = true, enableOnTabEnter = true },
    },
    keys = { { "<leader>n", "<cmd>NoNeckPain<CR>", desc = "Toggle 100-col writing margin" } },
  },
  {
    "folke/zen-mode.nvim",
    opts = { window = { width = 82 } },
    keys = { { "<leader>z", "<cmd>ZenMode<CR>", desc = "Toggle Zen Mode" } },
  },
  {
    "folke/twilight.nvim",
    opts = {},
  },
}
