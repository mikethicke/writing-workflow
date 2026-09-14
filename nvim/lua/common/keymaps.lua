-- ~/.config/nvim-common/lua/common/keymaps.lua
-- Keymaps shared by BOTH configs. (<leader> is set in each init.lua.)

local map = vim.keymap.set

-- Clear search highlighting with Esc
map("n", "<Esc>", "<cmd>nohlsearch<CR>")

-- Line navigation: H/L for start/end of line (replaces ^/$)
map({ "n", "v", "o" }, "H", "^", { desc = "First non-blank" })
map({ "n", "v", "o" }, "L", "$", { desc = "End of line" })

-- Sentence as an operator motion. NOTE: nvim-surround (common/surround.lua)
-- claims normal-mode ds/cs/ys, so those now mean delete/change/add surround.
-- For sentences use d) c) y), the dis/das text objects, or a count: d2s.
-- This map still applies to every other operator: >s, =s, gus, !s.
map("o", "s", ")", { desc = "To end of sentence" })

-- Move between splits with Ctrl + h/j/k/l
map("n", "<C-h>", "<C-w>h", { desc = "Window left" })
map("n", "<C-j>", "<C-w>j", { desc = "Window down" })
map("n", "<C-k>", "<C-w>k", { desc = "Window up" })
map("n", "<C-l>", "<C-w>l", { desc = "Window right" })

-- Save the current file
map("n", "<leader>w", "<cmd>write<CR>", { desc = "Save file" })
