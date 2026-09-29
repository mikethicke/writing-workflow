-- init.lua -- Neovim configuration for PROSE / long-form markdown writing.
--
-- Install by pointing NVIM_APPNAME at this directory, e.g.
--   ln -s ~/github/writing-workflow/nvim ~/.config/nvim-prose
--   alias vprose='NVIM_APPNAME=nvim-prose nvim'
--
-- This is a self-contained snapshot: the modules under lua/common/ are shared
-- with the author's separate coding config, vendored here so the config stands
-- alone. See nvim/README.md.

-- 1. Leader key (must be set before plugins load).
vim.g.mapleader = " "
vim.g.maplocalleader = " "

-- 2. Options and keymaps shared with the coding config (vendored in
--    lua/common/, so they resolve from this config's own runtimepath).
require("common.options")
require("common.keymaps")

-- 3. Options specific to writing prose.
local opt = vim.opt
opt.number = true               -- absolute number on the current line...
opt.relativenumber = true       -- ...relative numbers on the rest
opt.wrap = true                 -- soft-wrap long lines
opt.linebreak = true            -- ...wrap at word boundaries, not mid-word
opt.breakindent = true          -- keep wrapped lines visually aligned
opt.spell = true                -- spell checking on
opt.spelllang = "en_us"
opt.conceallevel = 2            -- let render-markdown hide the raw markup

-- 3c. Live word count in the statusline, via Vim's native wordcount(). The
--     statusline is re-evaluated on redraw (cursor move, edits, mode change),
--     so this updates as you type with no extra autocmd needed. Shows
--     "selected / total" while a visual selection is active.
_G.prose_wordcount = function()
  local wc = vim.fn.wordcount()
  if wc.visual_words then
    return wc.visual_words .. " / " .. wc.words .. " words"
  end
  return wc.words .. " words"
end
opt.laststatus = 2
opt.statusline = table.concat({
  "%<%f %h%w%m%r",              -- truncate, relative path, flags
  "%=",                         -- right-align the rest
  "%{v:lua.prose_wordcount()}",
  "  %-14.(%l,%c%V%) %P",       -- line,col  percentage-through-file
}, "")

-- 3b. Navigate by visual (wrapped) lines, since prose "lines" are long
--     paragraphs that span many screen rows. Bare j/k move by display line;
--     a count (e.g. 5j) still uses logical lines so relative-number jumps work.
local map = vim.keymap.set
map({ "n", "v" }, "j", "v:count == 0 ? 'gj' : 'j'", { expr = true, desc = "Down by display line" })
map({ "n", "v" }, "k", "v:count == 0 ? 'gk' : 'k'", { expr = true, desc = "Up by display line" })
map({ "n", "v" }, "<Down>", "gj", { desc = "Down by display line" })
map({ "n", "v" }, "<Up>", "gk", { desc = "Up by display line" })
-- Make H/L (start/end of line, from common.keymaps) respect display lines too.
map({ "n", "v", "o" }, "H", "g^", { desc = "Start of display line" })
map({ "n", "v", "o" }, "L", "g$", { desc = "End of display line" })

-- 4. Bootstrap the lazy.nvim plugin manager.
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
  vim.fn.system({
    "git", "clone", "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable", lazypath,
  })
end
vim.opt.runtimepath:prepend(lazypath)

-- 5. Load plugins: the shared Telescope spec + everything in lua/plugins/.
require("lazy").setup({
  require("common.telescope"),
  require("common.blink"),
  require("common.surround"),
  { import = "plugins" },
})

-- 6. Export the current markdown file to PDF with pandoc.
--    If a references.bib sits in the same folder, it is used for citations.
--    Trigger with <leader>pp.
vim.keymap.set("n", "<leader>pp", function()
  if vim.bo.filetype ~= "markdown" then
    vim.notify("Not a markdown file", vim.log.levels.WARN)
    return
  end
  local input = vim.fn.expand("%:p")
  local output = vim.fn.expand("%:p:r") .. ".pdf"
  local bib = vim.fn.expand("%:p:h") .. "/references.bib"
  local cmd = { "pandoc", input, "-o", output, "--citeproc" }
  if vim.fn.filereadable(bib) == 1 then
    vim.list_extend(cmd, { "--bibliography", bib })
  end
  vim.notify("Exporting -> " .. output)
  vim.system(cmd, { text = true }, function(res)
    vim.schedule(function()
      if res.code == 0 then
        vim.notify("Exported: " .. output)
      else
        vim.notify("Pandoc error:\n" .. (res.stderr or ""), vim.log.levels.ERROR)
      end
    end)
  end)
end, { desc = "Export markdown to PDF (pandoc)" })

-- 7. Push the current markdown file to a Substack draft with <leader>ps, or
--    to the publication's About page with <leader>pa.
--    publish_draft.py resolves @citekeys (via pandoc + the bundled note CSL),
--    uploads local images, and converts footnotes to Substack's native blocks.
--    It stops at "draft" -- review and publish yourself in the web editor.
--    publish_about.py runs the same pipeline but writes the live About page.
--
--    Override the tool's location by setting vim.g.substack_publish_dir before
--    this file loads; otherwise it is expected at the path below.
local substack_dir = vim.g.substack_publish_dir
  or vim.fn.expand("~/github/writing-workflow/publish")
local function substack_run(script, started, fallback)
  if vim.bo.filetype ~= "markdown" then
    vim.notify("Not a markdown file", vim.log.levels.WARN)
    return
  end
  local input = vim.fn.expand("%:p")
  local cmd = {
    "uv", "run", "--project", substack_dir,
    substack_dir .. "/" .. script, input,
  }
  vim.notify(started)
  vim.system(cmd, { text = true }, function(res)
    vim.schedule(function()
      if res.code == 0 then
        vim.notify(res.stdout or fallback)
      else
        vim.notify("Substack error:\n" .. (res.stderr or ""), vim.log.levels.ERROR)
      end
    end)
  end)
end
local function substack_draft()
  substack_run("publish_draft.py", "Creating Substack draft...", "Draft created")
end
-- The About page has no draft stage: this replaces the live page at once.
local function substack_about()
  substack_run("publish_about.py", "Updating Substack About page...", "About page updated")
end
vim.keymap.set("n", "<leader>ps", substack_draft, { desc = "Create Substack draft from markdown" })
vim.keymap.set("n", "<leader>pa", substack_about, { desc = "Replace Substack About page with markdown" })
vim.api.nvim_create_user_command("SubstackDraft", substack_draft, {})
vim.api.nvim_create_user_command("SubstackAbout", substack_about, {})

-- 8. Auto-commit for writing repos. Opt-in: only repos that have an
--    .autocommit.toml at their root (see publish/autocommit.py). A save commits
--    once ~threshold_words words have changed; closing nvim commits whatever
--    is pending. Runs detached so it never blocks the editor or outlives it
--    badly; a Substack push commits through publish_draft.py itself.
local function autocommit(mode)
  local file = vim.fn.expand("%:p")
  if file == "" then return end
  local found = vim.fs.find(".autocommit.toml", { upward = true, path = vim.fs.dirname(file) })
  if #found == 0 then return end
  vim.fn.jobstart({
    "uv", "run", "--project", substack_dir,
    substack_dir .. "/autocommit.py", mode, file,
  }, { detach = true })
end
local autocommit_group = vim.api.nvim_create_augroup("ProseAutocommit", { clear = true })
vim.api.nvim_create_autocmd("BufWritePost", {
  group = autocommit_group,
  callback = function() autocommit("save") end,
})
vim.api.nvim_create_autocmd("VimLeavePre", {
  group = autocommit_group,
  callback = function() autocommit("exit") end,
})
