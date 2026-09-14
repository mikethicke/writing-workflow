-- Render markdown inline in the buffer: headings, bold, lists, tables, callouts.
return {
  "MeanderingProgrammer/render-markdown.nvim",
  dependencies = { "nvim-treesitter/nvim-treesitter" },
  ft = { "markdown" },
  opts = {
    -- Parsers not installed in this config; disabling avoids the checkhealth
    -- warnings and trims extra treesitter passes.
    html = { enabled = false },
    latex = { enabled = false },
    -- Don't render while actively typing; the async render pass racing against
    -- live edits is what triggers the nvim_buf_get_text out-of-bounds crash.
    render_modes = { "n", "c", "t" },
    -- Give the buffer time to settle before re-rendering.
    debounce = 200,
  },
}
