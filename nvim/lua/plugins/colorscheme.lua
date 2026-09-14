-- Prose theme: Everforest (dark, medium) -- a warm, soft green dark theme.
return {
  "neanias/everforest-nvim",
  priority = 1000, -- load before everything else
  config = function()
    require("everforest").setup({ background = "medium" })
    vim.o.background = "dark"
    vim.cmd.colorscheme("everforest")
  end,
}
