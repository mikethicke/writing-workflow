-- ~/.config/nvim-common/lua/common/telescope.lua
-- Shared fuzzy finder, used by both the coding and prose configs.
-- Returns a lazy.nvim plugin spec.

return {
  "nvim-telescope/telescope.nvim",
  branch = "0.1.x",
  dependencies = {
    "nvim-lua/plenary.nvim",
    -- Optional native sorter. Needs `make` and a C compiler.
    -- If the build ever fails, just delete this one line.
    { "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
  },
  config = function()
    local telescope = require("telescope")
    telescope.setup({})
    pcall(telescope.load_extension, "fzf")

    local builtin = require("telescope.builtin")
    local map = vim.keymap.set
    map("n", "<leader>ff", builtin.find_files, { desc = "Find files" })
    map("n", "<leader>fg", builtin.live_grep,  { desc = "Grep in files" })
    map("n", "<leader>fb", builtin.buffers,    { desc = "Open buffers" })
    map("n", "<leader>fh", builtin.help_tags,  { desc = "Help tags" })
  end,
}
