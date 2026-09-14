-- ~/.config/nvim-common/lua/common/options.lua
-- Options shared by BOTH the coding and prose configs.

local opt = vim.opt

opt.mouse = "a"                 -- enable mouse support
opt.clipboard = "unnamedplus"   -- use the system clipboard
opt.ignorecase = true           -- case-insensitive searching...
opt.smartcase = true            -- ...unless the search contains a capital letter
opt.termguicolors = true        -- 24-bit colour (required by the themes)
opt.splitright = true           -- vertical splits open to the right
opt.splitbelow = true           -- horizontal splits open below
opt.undofile = true             -- persistent undo across sessions
opt.updatetime = 250            -- snappier diagnostics / events
opt.scrolloff = 4               -- keep a few lines visible around the cursor
