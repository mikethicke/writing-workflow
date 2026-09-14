# obsidian

The reading end of the workflow: getting sources *into* notes, so their citekeys
can come back out in a draft.

Two plugins do the work.

**[Zotero Integration](https://github.com/mgmeyers/obsidian-zotero-integration)**
(`obsidian-zotero-desktop-connector`) pulls an item out of Zotero — metadata,
abstract, PDF annotations — and renders it into a literature note. It also
inserts citations, and this is where it meets the rest of the repo: its `Pandoc`
cite format produces `[@citekey]`, the exact syntax
[`publish/publish_draft.py`](../publish) resolves into footnotes, and the same
Better BibTeX keys that [`nvim/`](../nvim) completes via zotcite. One Zotero
library, one key format, from reading through to a published draft.

**[Kindle Highlights](https://github.com/hadynz/obsidian-kindle-plugin)**
(`obsidian-kindle-plugin`) syncs highlights and notes from Amazon into the vault.

Everything else in my vault is unrelated to writing and isn't here.

## Requirements

- [Zotero](https://www.zotero.org/) desktop, running, with
  [Better BibTeX](https://retorque.re/zotero-better-bibtex/) installed — the
  citekeys come from BBT.
- [Dataview](https://github.com/blacksmithgu/obsidian-dataview) — the template
  writes inline fields (`**Title**:: ...`), which are only queryable with it.
  The note still renders without it; you just can't query across notes.
- Optionally [Admonition](https://github.com/valentine195/obsidian-admonition),
  to style the custom callout types the template uses (`[!Cite]`, `[!md]`,
  `[!LINK]`, `[!Abstract]`). Without it they fall back to default callouts.

Zotero Integration downloads its own `pdfannots2json` binary on first use, for
pulling PDF annotations. Don't commit it — it's ~23 MB.

## Install

Install both plugins from Obsidian's community browser first, so the directories
exist, then drop the settings in and restart Obsidian:

```bash
VAULT=/path/to/your-vault
cp -r plugins/* "$VAULT/.obsidian/plugins/"
mkdir -p "$VAULT/! templates"
cp "templates/Literature Note.md" "$VAULT/! templates/"
```

These `data.json` files *replace* each plugin's settings — back up yours first if
you have them configured. Nothing else in `.obsidian/` is touched, so your other
plugins and preferences are left alone.

## What the settings do

**Zotero Integration** (`plugins/obsidian-zotero-desktop-connector/data.json`)

- Literature notes land in `Literature Notes/@{{citekey}}.md`; extracted images
  in `Assets/{{citekey}}/`. Both paths assume those folders exist — change
  `exportFormats[].outputPathTemplate` if your vault is laid out differently.
- Rendered from `! templates/Literature Note.md` (included here).
- Three cite formats: **Pandoc** (`[@citekey]` — the one that feeds the publish
  script), **Chicago notes**, and **Chicago author-date**.
- `citeSuggestTemplate` is `[[{{citekey}}]]`, so the citation *suggester* makes
  an internal link to the literature note rather than a bare key.

**Kindle Highlights** (`plugins/obsidian-kindle-plugin/data.json`)

Highlights go to `Reading/Books/Kindle`, with book metadata, no sync on boot.
Login state and last-sync timestamp are stripped — you sign in yourself, and the
plugin rewrites those on first sync.

## The template

`templates/Literature Note.md` is [Nunjucks](https://mozilla.github.io/nunjucks/),
which Zotero Integration renders. Worth knowing about it:

- Frontmatter carries `citekey`, `status: unread`, and an empty `dateread`, so
  notes are filterable by reading state.
- Creators are grouped by role, so editors and translators don't get labelled as
  authors.
- Annotations are wrapped in `{% persist "annotations" %}`. **This is the part
  that matters:** re-importing an item appends only annotations newer than the
  last import, under a dated heading, instead of overwriting the note. Your own
  writing under `# Notes` survives. If you edit the template, keep that block.
- Highlights render with their Zotero highlight colour preserved as a `<mark>`.
