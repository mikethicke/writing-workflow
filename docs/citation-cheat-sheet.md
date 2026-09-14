# Citation Cheat Sheet

Quick reference for citing sources in Substack post drafts. Companion to
[`neovim-to-substack-workflow.md`](./neovim-to-substack-workflow.md).

**The one-line summary:** you type `[@citekey]`; on publish, pandoc turns every
citation into a real Substack footnote using Chicago full-note style. There is
no separate works-cited list — each footnote carries the complete reference.

---

## 1. Setup per post

Every post that cites anything needs `bibliography` in its frontmatter:

```markdown
---
title: College After AI
bibliography: references.bib
---
```

The path is relative to the markdown file. Each post folder gets its own
`references.bib`, which **zotcite writes automatically when you save the
buffer** — you never edit it by hand. (Corollary: don't hand-edit it, your
changes get overwritten on the next save.)

Optional: `csl: some-style.csl` overrides the bundled
`publish/chicago-notes-bibliography.csl`. You almost never want this.

---

## 2. Inserting a citation key

| How | What it does |
|---|---|
| Type `@` then letters, in insert mode | Blink completion menu, matches first author's last name or title |
| `<leader>zc` in normal mode | Telescope picker, seeded from the word under/before the cursor |
| `<leader>zf` in normal mode | Telescope picker, **whole library** — use this for multi-word queries like `lucas american higher` |
| `:Zseek pattern` | Same picker, from the command line (only the first word is used as the pattern) |

`<C-x><C-b>`, zotcite's own insert-mode picker, **does not work under tmux** —
`C-b` is the tmux prefix. That's what `<leader>zc` exists for.

Keys are Better BibTeX keys (`lucasAmericanHigherEducation2006`), matching the
exported `.bib`.

---

## 3. Looking up bibliographic information

Put the cursor **on a citation key** in normal mode:

| Key | Shows |
|---|---|
| `<leader>zi` | Authors, year, title — in the status bar. The quick "what is this?" |
| `<leader>za` | **All fields** zotcite has for the reference |
| `<leader>zb` | Inserts the abstract into the buffer (if Zotero has one) |
| `<leader>zo` | Opens the attachment (PDF, etc.) registered in Zotero |

Other lookups:

- `:Zannotations key` — pull your PDF annotations into the buffer.
  Add a negative integer to offset wrong page labels: `:Zannotations key -10`
- `:Znote key` — pull Zotero notes in
- `:Zinfo` — zotcite's internal state, for when something's broken

You can also just read `references.bib` — it's plain text in the post folder:

```bash
grep -A20 'jarvisGutenberg' posts/01-college-after-ai/references.bib
```

---

## 4. Citation syntax

All examples below are **verified output** from this repo's pandoc + CSL setup.

### The basic form

Put the citation in square brackets, immediately after the sentence's period —
that's where the footnote marker lands:

```markdown
...a short, 550-year, parenthesis in human history.[@jarvisGutenbergParenthesisAge2023]
```

> ¹ Jeff Jarvis, *The Gutenberg Parenthesis: The Age of Print and Its Lessons for the Age of the Internet* (Bloomsbury Academic, 2023).

### Page numbers and other locators

Comma, then the locator:

```markdown
...drivers of social and cultural change.[@lucasAmericanHigherEducation2006, pp. 51-66]
```

> ¹ Christopher J. Lucas, *American Higher Education* (Palgrave Macmillan US, 2006), 51–66, https://doi.org/10.1007/978-1-137-10841-8.

A bare number works too (`, 51`) and renders identically to `p. 51`. Other
recognized locators: `chap. 3`, `sec. 2`, `para. 4`, `bk. 1`, `fig. 7`,
`vol. 2`, `n. 14`.

### Several sources in one footnote

Separate with a semicolon:

```markdown
...has been declining.[@saadPerceivedImportanceCollege2025; @salamCollegeEnrollmentFalling2024]
```

> ¹ Lydia Saad, *Perceived Importance of College Hits New Low*, Gallup, 2025, https://…; Erum Salam, "College Enrollment Is Falling at a 'Concerning' Rate…," *The Guardian*, December 8, 2024, https://…

### Naming the author in your own prose

Drop the brackets from the key and bracket the locator instead. Citeproc sees
the author is already in the sentence and doesn't repeat it:

```markdown
As @jarvisGutenbergParenthesisAge2023 [12] observes, print culture was an anomaly.
```

> ¹ *The Gutenberg Parenthesis*, 12.

To suppress the author but keep the reference, use `-@key`:

```markdown
The Guardian reported the decline last December.[-@salamCollegeEnrollmentFalling2024]
```

> ¹ "College Enrollment Is Falling at a 'Concerning' Rate, New Data Reveals."

### Repeat citations shorten automatically

The first citation of a work is the full reference; every later one is Chicago
short form (`Jarvis, *The Gutenberg Parenthesis*.`). You don't do anything —
the CSL handles it. This is also why reordering paragraphs is safe.

---

## 5. Footnotes with references *and* commentary

This is the case worth memorizing. **Anything before the `@key` is a prefix;
anything after the locator is a suffix.** Both land inside the footnote,
around the reference.

### Comment after the reference — most common

```markdown
...the standard account of the medieval origins.[@lucasAmericanHigherEducation2006, 51-66. I find the periodization unconvincing, but this is the account everyone works from.]
```

> ¹ Christopher J. Lucas, *American Higher Education* (Palgrave Macmillan US, 2006), 51–66, https://…. I find the periodization unconvincing, but this is the account everyone works from.

Note the **period before the comment**, so the sentence reads correctly.

### Comment before the reference

```markdown
...universities ran the medieval book trade.[For the fullest treatment, see @lucasAmericanHigherEducation2006, 51-66. Jarvis tells a rather different story.]
```

> ¹ For the fullest treatment, see Lucas, *American Higher Education*, 51–66. Jarvis tells a rather different story.

Pandoc capitalizes the first word of a prefix, so write `see @key` and let it
become `See @key` when the prefix stands alone.

### Formatting inside the comment

Bold, italic, and links all survive into the footnote:

```markdown
[@saadPerceivedImportanceCollege2025. The **partisan gap** is discussed [here](https://example.com).]
```

### Long notes: use a manual footnote instead

When the note is a paragraph rather than a clause, write a real footnote and
put **unbracketed** citations inside it:

```markdown
This deserves more attention than a parenthesis allows.[^credentials]

[^credentials]: The story is more complicated than I let on. See
@lucasAmericanHigherEducation2006 [51-66], which covers the medieval side, and
compare @randallcollinsCredentialSocietyHistorical2019 on the twentieth century.
```

> ¹ The story is more complicated than I let on. See Christopher J. Lucas, *American Higher Education* (Palgrave Macmillan US, 2006), 51–66, https://…, which covers the medieval side, and compare…

Two rules for citations inside manual footnotes:

1. **Don't use square brackets.** A bracketed `[@key]` inside an existing
   footnote can't nest, so citeproc falls back to a parenthetical:
   `(Lydia Saad, *Perceived Importance…*, 3)`. Ugly. Use the narrative form.
2. **Bracket the locator**: `@key [51-66]`, not `@key, 51-66`. With a comma the
   page number lands *after* the URL, which reads badly.

### Comment-only footnote

No citation involved — plain markdown footnote, nothing special:

```markdown
...frat parties, and building solar cars.[^aside]

[^aside]: I did not build a solar car.
```

### Numbering

Citation footnotes and manual `[^name]` footnotes are **merged and renumbered
together** in document order. Use descriptive names (`[^credentials]`) rather
than `[^1]`, `[^2]` — the names never appear in output and you'll never have to
renumber by hand.

---

## 6. The work under review

A review has to say what it is reviewing before it starts reviewing, and a
footnote marker on the first line does not do that. Name the work in the
frontmatter instead:

```markdown
---
title: Who Is Responsible?
bibliography: references.bib
reviewed: braunWhoResponsible2024
---
```

On publish the script renders that key as a blockquote above the first
paragraph, in Chicago **bibliography** form — surname first, periods, rather
than the parenthetical form the footnotes use:

> Lucas, Christopher J. *American Higher Education*. Palgrave Macmillan US, 2006. https://doi.org/10.1007/978-1-137-10841-8.

Reviewing more than one book is a list, and the works stay in the order you
wrote them rather than being sorted by the style:

```markdown
reviewed:
  - braunWhoResponsible2024
  - lucasAmericanHigherEducation2006
```

Three things worth knowing:

- **It is re-rendered on every publish**, from `references.bib`. Fix the
  metadata in Zotero and the header follows. This is the whole point of the
  key: a hand-pasted citation goes stale silently.
- **An unknown key stops the run**, with the key named. Unlike a body
  citation, which publishes as a bold **key?**, a missing header would just
  vanish — easy to miss when you eyeball the draft.
- **It doesn't count as a citation.** Citeproc never sees the header, so the
  first `[@key]` you write for the same book still renders as a full
  first-reference footnote, duplicating it. The usual fix is the review
  convention: cite the book under review by bare page number in your prose —
  `(51)` — and keep footnotes for everything else.

---

## 7. Checking your work before publishing

### Dry-run the citation resolution

The single most useful command. Renders exactly what the publish script will
send to Substack, without touching Substack:

```bash
cd posts/01-college-after-ai
pandoc -f markdown -t markdown --wrap=preserve --citeproc \
  -M suppress-bibliography=true \
  --bibliography references.bib \
  --csl ../../publish/chicago-notes-bibliography.csl \
  college-after-ai.md
```

Watch for `[WARNING] Citeproc: citation somekey not found` — a typo'd or
missing key renders as a bold **somekey?** in the output rather than failing.

### Find broken keys fast

```bash
# keys cited in the post but missing from the bibliography
comm -23 \
  <(grep -o '@[A-Za-z][A-Za-z0-9_:.#$%&+?<>~/-]*' college-after-ai.md | tr -d '@' | sort -u) \
  <(grep -o '^@[A-Za-z]*{[^,]*' references.bib | cut -d'{' -f2 | sort -u)
```

Anything it prints is a citation that will publish as **key?**. Usually it
means the item was removed from the Zotero collection, or the key changed.
Swap the two `<(...)` blocks to list unused entries instead.

### Publish

`<leader>ps` in Neovim (or `:SubstackDraft`) creates the Substack draft;
citations are resolved as part of that step. It stops at *draft* — always
eyeball the footnotes in Substack's editor before publishing.

---

## 8. Gotchas

- **`<leader>pp` (PDF export) doesn't use the note CSL.** It calls pandoc
  without `--csl`, so the PDF shows author-date parentheticals, not footnotes.
  Fine for reading; not a preview of the published post. Use the dry-run
  command in §7 for that.
- **No bibliography list is generated**, on purpose. Full-note citations
  already carry the complete reference, and Substack's importer can't render
  pandoc's `#refs` div.
- **Citations only resolve if `bibliography` is in the frontmatter.** Without
  it the publish script passes the markdown through untouched and your
  `[@citekey]` text ships literally into the draft.
- **A literal at-sign** — an email or a handle — must be escaped as `\@` or the
  publish script's regex treats it as a citation.
- **Tables aren't supported by Substack** at all. Convert to an image.
- **`references.bib` is regenerated by zotcite on save.** Fix metadata in
  Zotero, not in the `.bib`.
- **Citation highlighting**: citations show as muted italics via a custom
  treesitter query, with the `@` left visible so they don't read as links.
