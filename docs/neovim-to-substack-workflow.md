# Neovim → Substack Draft Workflow

A guide for going from a markdown draft written in Neovim to a formatted draft post in Substack, with images and footnotes intact.

**Important caveat:** Substack has no official public API for creating posts. This workflow relies on [`python-substack`](https://github.com/ma2za/python-substack), an unofficial, reverse-engineered library. It authenticates using your session cookie or credentials, and can break if Substack changes its internal API. Always review the draft in the Substack web editor before publishing — this workflow stops at "draft," on purpose.

---

## 1. One-time setup

This uses [`uv`](https://docs.astral.sh/uv/) to keep dependencies isolated in a project-local virtual environment rather than installing globally. If you don't have `uv` yet:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then clone this repository and sync the environment:

```bash
git clone https://github.com/mikethicke/writing-workflow.git
cd writing-workflow/publish
uv sync
```

`publish/pyproject.toml` and `publish/uv.lock` are committed, so `uv sync` builds a project-local `.venv/` with the exact pinned dependencies — nothing touches your system Python. You never need to activate it manually; `uv run` (used below) handles that.

You also need [`pandoc`](https://pandoc.org/) on your `PATH` — it resolves `@citekey` citations into footnotes (skip only if you never cite). On macOS:

```bash
brew install pandoc
```

A note-based CSL style (`chicago-notes-bibliography.csl`) is bundled next to the script; no separate download is needed.

Get your session cookie:
1. Log into Substack in your browser.
2. Open dev tools (F12) → Network tab.
3. Refresh, click any request to substack.com.
4. Copy the full `Cookie` header value (or just the `connect.sid` portion).

Put it in `~/.config/substack-publish/.env`. That location is outside any
repository on purpose — this one is public, and a `.env` in the working tree is
one `git add -f` away from being published:

```bash
mkdir -p ~/.config/substack-publish
cp publish/.env.example ~/.config/substack-publish/.env
chmod 600 ~/.config/substack-publish/.env
```

```
COOKIES_STRING=connect.sid=your-cookie-value-here
PUBLICATION_URL=https://yourname.substack.com
```

To keep it somewhere else, point `SUBSTACK_ENV_FILE` at that path. A `.env` next
to the script still works, for anyone carrying the pre-split layout forward.

This cookie is a live session credential — full access to your Substack account.
It expires when the session does, so a sudden `401` from the script usually means
a stale cookie rather than a broken workflow.

---

## 2. Write your draft in Neovim

Write normal markdown, with an optional Obsidian-style YAML frontmatter block at the top for metadata:

```markdown
---
title: My Post Title
subtitle: Subtitle goes here
audience: everyone
section: Essays
bibliography: references.bib
---

Regular paragraph text with **bold** and *italic*.

![Alt text for this image](./images/chart.png "Caption shown under the image.")

Here's a claim worth footnoting[^1].

As Smith argues, widgets matter [@smith2020widgets].

[^1]: This is the footnote text. It can include **formatting**.
```

- **Frontmatter:** all fields are optional. Recognized keys:
  - `title` — used as the draft title if none is passed on the command line.
  - `subtitle` — used as the draft subtitle if none is passed on the command line.
  - `audience` — one of `everyone`, `only_paid`, `founding`, `only_free`. Defaults to `everyone`.
  - `section` — must match an existing section name in your publication (as returned by Substack's API); the script looks it up and fails if it doesn't exist.
  - `bibliography` — path (relative to the markdown file) to a `.bib` file, or a list of them. When set and the post contains `@citekey` citations, the script resolves them into footnotes before publishing (see **Citations** below). zotcite keeps this file in sync automatically.
  - `reviewed` — a citation key, or a list of them, naming the work(s) a review post is about. Rendered as a blockquote above the first paragraph in Chicago bibliography form (surname first), re-generated from the `.bib` on every publish so it can't go stale. Requires `bibliography`; an unknown key aborts the run. Unlike a body citation it is invisible to citeproc, so a later `[@key]` for the same work still produces a full first-reference footnote.
  - `substack_draft_id` — **written by the script, not by you.** The first run records the id of the draft it created; later runs use it to update that same draft instead of creating a new one (see **Syncing edits** below).
  - `csl` — optional path to a CSL style file, overriding the bundled default (`publish/chicago-notes-bibliography.csl`, a note-based Chicago style).
  - The frontmatter block itself is stripped before conversion and never appears in the post body.
- **Images:** use standard `![alt](path)` syntax — local file paths or URLs both work. Local paths are resolved **relative to the markdown file**, not to wherever you run the script from, so `images/chart.png` works whether you publish from the post's directory or the repo root. Each local image is uploaded to Substack's CDN before the draft is written, and the alt text and the image's real dimensions are carried through. A missing file or a failed upload aborts the run rather than leaving an "IMAGE NOT FOUND" block in the draft. One thing to know: the image needs a line of its own (one written mid-paragraph is not supported and survives as literal `![…](…)` text).
- **Captions:** add one in markdown's title slot, after the path: `![alt](images/chart.png "Caption goes here.")`. Single quotes work too, which is the way to write a caption containing a double quote. The caption becomes Substack's real caption — the styled line rendered under the image — and is entirely separate from the alt text, so keep writing alt text that describes the image for a screen reader and let the caption say whatever the reader should read. Captions are plain text: formatting and links inside one are not carried through. Omit the title and the image simply has no caption, exactly as before.
- **Footnotes:** use standard `[^1]` / `[^1]: text` syntax. `python-substack` converts these into Substack's real native footnote blocks (the small superscript pop-ups), not plain bracketed text.
- **Citations:** insert Pandoc-style `@citekey` or `[@citekey]` citations using the [zotcite](https://github.com/jalvesaq/zotcite) Neovim plugin (in insert mode, type `@` + author/title and pick from the blink completion menu; or from normal mode press `<leader>zc` for the Telescope picker). On publish, the script runs `pandoc --citeproc` with a **note-based CSL** so each citation becomes a real footnote — merged and renumbered alongside any manual `[^n]` footnotes, then mapped onto Substack's native footnote blocks. This only happens when `bibliography` is set in the frontmatter *and* the post actually contains citations; otherwise the markdown passes through untouched. The standalone bibliography/works-cited list is intentionally suppressed (full-note citations already carry the complete reference, and Substack's importer can't render Pandoc's `#refs` div). Requires `pandoc` on your `PATH`.
- **Inline formatting:** `**bold**`, `*italic*`, `***both***`, `~~strikethrough~~`, `` `code` `` and `[links](url)` all work, and they nest — an italicised book title that is also a link can be written either way round, `[*Title*](url)` or `*[Title](url)*`. Backticks fence off markdown, so `` `*x*` `` stays literal. Bare URLs are linked automatically, whether written plainly or in pandoc's `<https://…>` form — which is how the DOIs in citation footnotes arrive, so those come through clickable. Trailing sentence punctuation is kept outside the link.
- **Line wrapping:** wrap your prose however you like. Hard-wrapped lines are rejoined into one paragraph before publishing, since `python-substack` would otherwise make every single line its own paragraph — which looks passable on a desktop but comes out as ragged, over-spaced fragments on a phone. Blank lines still separate paragraphs, and fenced code blocks are left exactly as written.
- **Blockquotes:** `>` on every line or only on the first line of each paragraph both work, with or without a space after the `>`. A `>` on its own line separates paragraphs within the quote.
- **Includes:** a line that is nothing but `-> path/to/file.md` is replaced by that file's contents before anything else happens — the point being a shared footer (or header, or standing disclaimer) that lives in one file and is pointed at from every post in a series:

  ```markdown
  Last paragraph of the review.

  -> ../responses.md
  ```

  The path is relative to the file the arrow is written in, so an included file can itself include others relative to *its* own location. Included files may have their own frontmatter; it is stripped, except that a `bibliography:` in it is added to the post's, so a citation inside a shared footer resolves against the footer's own `.bib`. Image paths inside an included file are likewise interpreted relative to that file. A missing target or an include loop aborts the run.

  The arrow must be alone on its line and the target must end in `.md`, so ordinary prose starting with an arrow is left alone; `\-> file.md` escapes the directive, and directives inside fenced code blocks are ignored.

- **Tables:** not supported by Substack's editor. Avoid them, or convert to an image before publishing.

---

## 3. The publish script

The script lives at `publish/publish_draft.py`, next to the `pyproject.toml` that pins its dependencies and the bundled CSL style. It is long enough, and changes often enough, that it is not reproduced here — read the file itself, which carries a comment wherever the reasoning is not obvious.

What a run does, in order:

1. **Splits the frontmatter** off the top of the file, leaving the body.
2. **Expands includes** — every `-> other.md` line becomes that file's contents, recursively, so everything after this point sees one document.
3. **Resolves citations** — `pandoc --citeproc` with the note-based CSL turns `@citekey` into footnotes, if the post has both a `bibliography` and at least one citation.
4. **Renders the reviewed-work header**, when `reviewed:` names one or more keys, as a blockquote above the first paragraph. It runs after the citations so citeproc never sees it, which is why a later `[@key]` for the same work still gets a full first-reference footnote.
5. **Isolates image lines** — a blank line is inserted either side of any line that is nothing but an image, because python-substack treats a block beginning with `!` as one image and silently drops the rest of that block.
6. **Rejoins soft-wrapped lines** into whole paragraphs, leaving code fences alone and rebuilding blockquotes as it goes.
7. **Uploads local images** to Substack's CDN, resolved relative to the markdown file, and rewrites the markdown to point at the returned URLs.
8. **Converts the markdown** to Substack's document format via python-substack's `Post.from_markdown`, with the library's `parse_inline` replaced by one that handles nested formatting, then patches each image node with its real dimensions and alt text.
9. **Creates or updates the draft**, recording the new draft's id in the frontmatter the first time.

Any failure along the way exits non-zero with a message instead of shipping a half-broken draft: a missing include or an include loop, a missing bibliography or CSL file, a `reviewed:` key that is not in the `.bib`, a missing image file, a failed upload, a pandoc error, or a recorded draft id that no longer exists in Substack.

Run it with title and subtitle coming from the frontmatter:

```bash
uv run --project publish publish/publish_draft.py path/to/my-post.md
```

Or override them (or supply them, if the file has no frontmatter) with positional arguments:

```bash
uv run --project publish publish/publish_draft.py my-post.md "My Post Title" "An optional subtitle"
```

Title resolution order: CLI argument, then frontmatter `title`, then a hard error if neither is set. Subtitle works the same way but defaults to empty instead of erroring.

`uv run` uses the project's `.venv`, creating and populating it on first use — there is no activation step and no install step. `--project publish` names the folder holding the `pyproject.toml`, which is what lets the command be run from the repository root, or from anywhere else, rather than only from `publish/` itself. The project also installs a `substack-draft` entry point, so `uv run --project publish substack-draft my-post.md` is equivalent.

This creates a **draft** in Substack — it does not publish or send anything. Open the link it prints, do a final visual check in the web editor, then hit publish yourself when ready.

### Syncing edits

The first run creates a draft and writes its id back into your frontmatter as `substack_draft_id`. Every run after that **updates that same draft in place** rather than piling up duplicates, so the usual loop is: edit the markdown, re-run, refresh the Substack tab.

Updating replaces the draft body wholesale, which has one consequence worth internalizing: **the sync is one-way.** Anything you typed into the Substack web editor since the last run — a typo fix, a tweaked pull quote — is overwritten. Treat the markdown file as the single source of truth and make your edits there.

To guard against doing that by accident, the script asks before overwriting when run from an interactive terminal:

```
Overwrite Substack draft 123456? Edits made in the web editor will be lost. [y/N]
```

Pass `-y`/`--yes` to skip the prompt in scripts. When there's no tty — as with the Neovim mapping below — it proceeds without asking, since blocking on stdin there would just hang the editor.

Two other flags and failure modes:

- `--new` forces a fresh draft even when the file already has an id, and records the new id in its place. The old draft stays in Substack, now unlinked; the script prints its id so you can delete it by hand.
- If the recorded draft has been deleted in Substack (or already published — publishing moves a post off the drafts endpoint), the update returns a 404 and the script tells you to re-run with `--new` or clear the frontmatter key.

Note that local images re-upload on every sync rather than reusing the URLs already on Substack's CDN, so an image-heavy post accumulates duplicate uploads as you iterate.

---

## 4. Wire it into Neovim

This is wired into the prose config (`nvim/init.lua` in this repo). Since title/subtitle come from frontmatter, the command passes only the file path. `--project` tells `uv` which `.venv` to use, so it works regardless of Neovim's current directory, and the async call surfaces the draft URL (or any error) via `vim.notify`:

```lua
local substack_dir = vim.g.substack_publish_dir
  or vim.fn.expand("~/github/writing-workflow/publish")
local function substack_draft()
  if vim.bo.filetype ~= "markdown" then
    vim.notify("Not a markdown file", vim.log.levels.WARN)
    return
  end
  local input = vim.fn.expand("%:p")
  local cmd = {
    "uv", "run", "--project", substack_dir,
    substack_dir .. "/publish_draft.py", input,
  }
  vim.notify("Creating Substack draft...")
  vim.system(cmd, { text = true }, function(res)
    vim.schedule(function()
      if res.code == 0 then
        vim.notify(res.stdout or "Draft created")
      else
        vim.notify("Substack error:\n" .. (res.stderr or ""), vim.log.levels.ERROR)
      end
    end)
  end)
end
vim.keymap.set("n", "<leader>ps", substack_draft, { desc = "Create Substack draft from markdown" })
vim.api.nvim_create_user_command("SubstackDraft", substack_draft, {})
```

From within a draft that has a `title` in its frontmatter, press `<leader>ps` (or run `:SubstackDraft`) to send the current file straight to a Substack draft. Includes, citations, and image uploads all happen as part of that step.

The first press creates the draft; every press after that updates it, and the notification says which happened. Because the mapping runs without a tty it never prompts, so remember that a press discards any web-editor edits made since the last sync. The `substack_draft_id` line appears in your frontmatter after the first press — the file is rewritten on disk, so Neovim will prompt to reload it (or reload it silently if you have `autoread` on).

---

## 5. Fallback: manual copy-paste

If you don't want to set up the script, Substack's web editor parses pasted plain markdown reasonably well — headings, bold/italic, links, and lists convert automatically.

Limitations of this path:
- **Local images** won't render from pasted text — you'll need to drag or paste each image in separately.
- **Footnotes** won't convert — `[^1]` shows up as literal text; you'd re-add footnotes manually via the editor's footnote button.
- **Citations, includes, and the reviewed-work header** are all things the script does before Substack ever sees the text, so none of them happen: `@citekey`, `-> footer.md`, and `reviewed:` would all paste through as-is.
- **Tables** aren't supported either way.

---

## Known limitations of this whole workflow

- Unofficial API — no guarantee it keeps working after Substack ships changes.
- Session-cookie auth — keep `.env` out of version control, rotate the cookie if anything seems off.
- Always ends at "draft" — final review and publishing stay manual, which is the point.
- Sync is one-way (markdown → Substack) and overwrites the whole draft body, so the web editor can't be used for durable edits.
- Once a post is published it's no longer a draft, and re-running the script can't update it.
- Tables have no equivalent in Substack's editor, and an image written mid-paragraph rather than on its own line passes through as literal markdown.
