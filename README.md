# writing-workflow

The setup I use to write long-form essays and publish them to Substack: draft in
Neovim, cite from Zotero, resolve citations with pandoc, push to a Substack draft.

Reading highlights in Zotero and Kindle are imported to Obsidian.

```
reading ─ Zotero + Better BibTeX ─┐
          Kindle highlights ──────┤  (obsidian/)
                                  ↓
                            one citekey
                                  ↓
markdown in Neovim
   ├─ zotcite ............ @citekey completion from your Zotero library
   ├─ pandoc --citeproc .. @citekey → Chicago-style footnotes
   └─ publish_draft.py ... images → Substack CDN, markdown → Substack draft
```
## What's here

| | |
| --- | --- |
| [`publish/`](publish/) | `publish_draft.py` — markdown → Substack draft. Citations, includes, image uploads, footnotes. |
| [`nvim/`](nvim/) | A standalone Neovim config for prose: soft wrap, live word count, distraction-free modes, Zotero completion. |
| [`obsidian/`](obsidian/) | Zotero → literature notes, Kindle highlights → vault. Emits the same `[@citekey]` the publish script resolves. |
| [`docs/`](docs/) | [The full workflow guide](docs/neovim-to-substack-workflow.md) and a [citation cheat sheet](docs/citation-cheat-sheet.md). |

## Quick start

Requires [`uv`](https://docs.astral.sh/uv/), [`pandoc`](https://pandoc.org/), and
Neovim ≥ 0.10. Zotero with [Better BibTeX](https://retorque.re/zotero-better-bibtex/)
is needed only if you cite.

```bash
git clone https://github.com/mikethicke/writing-workflow.git
cd writing-workflow

# 1. the publish tool
cd publish && uv sync && cd ..
mkdir -p ~/.config/substack-publish
cp publish/.env.example ~/.config/substack-publish/.env
chmod 600 ~/.config/substack-publish/.env
$EDITOR ~/.config/substack-publish/.env    # add your publication URL + session cookie

# 2. the editor config 
ln -s "$PWD/nvim" ~/.config/nvim-prose
echo "alias vprose='NVIM_APPNAME=nvim-prose nvim'" >> ~/.zshrc
```

Then write a post with YAML frontmatter and press `<leader>ps`:

```markdown
---
title: My Post Title
subtitle: An optional subtitle
bibliography: references.bib
---

Prose, with a citation [@smithSomething2024] that becomes a footnote.

![Alt text](images/diagram.png "An optional caption")
```

The first push creates the draft and writes `substack_draft_id` back into your
frontmatter; every push after that updates that same draft in place.

Full details — every frontmatter key, the include directive, syncing edits, the
known limitations — are in [`docs/neovim-to-substack-workflow.md`](docs/neovim-to-substack-workflow.md).

## Caveats worth reading before you rely on this

- **Substack has no public API for posts.** This uses
  [`python-substack`](https://github.com/ma2za/python-substack), which is
  reverse-engineered and authenticates with your browser session cookie. It can
  break whenever Substack changes something. `publish/README.md` has the details.
- **Re-running overwrites the whole draft body.** If you edited the post in
  Substack's web editor since the last push, those edits are gone. From Neovim it
  doesn't even prompt.
- **Images re-upload on every push**, so an image-heavy post accumulates
  duplicates on the CDN as you iterate.

## License

MIT, except the bundled Chicago CSL style (CC BY-SA 3.0). See [LICENSE](LICENSE).
