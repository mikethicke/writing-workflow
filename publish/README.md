# publish

`publish_draft.py` turns a markdown file into a Substack draft: it resolves
`@citekey` citations into footnotes, rewrites inline `^[note]` footnotes into
the labelled form, splices in shared includes, uploads local
images to Substack's CDN, turns `{{subscribe}}` and `{{youtube <link>}}` lines
into the editor's subscribe widget and video embed, and converts the result
into Substack's internal document format.

It stops at *draft*. It cannot publish a post or send an email.

`publish_about.py` runs the same pipeline and writes the result to the
publication's About page, which has no draft stage — see below.

## Install

```bash
uv sync
```

Also needs [`pandoc`](https://pandoc.org/) on `PATH` — only when a post has both a
`bibliography` and at least one citation, or a `reviewed:` key. `brew install pandoc`.

## Credentials

Substack has no API tokens. `python-substack` authenticates as your browser, so
the script needs a full session cookie. Copy `.env.example` to
`~/.config/substack-publish/.env` and fill it in; that file has instructions for
getting the cookie out of devtools.

The default location is outside any repository on purpose — **this repo is
public**, and a `.env` in the working tree is one `git add -f` away from being
published. Lookup order:

1. `$SUBSTACK_ENV_FILE` — explicit override, any path
2. `~/.config/substack-publish/.env` (honours `$XDG_CONFIG_HOME`) — the default
3. `.env` next to the script — back-compat with the older layout

Variables already exported in your environment win over all three.

The cookie is a live credential with full access to your account, and it expires
when the session does. A sudden `401` almost always means a stale cookie.

## Use

```bash
uv run publish_draft.py path/to/post.md
uv run substack-draft path/to/post.md          # same thing, via the entry point
uv run publish_draft.py post.md "Title" "Subtitle"   # override frontmatter
uv run publish_draft.py post.md --new          # force a second, separate draft
uv run publish_draft.py post.md -y             # don't prompt before overwriting
```

Frontmatter keys it reads:

| key | meaning |
| --- | --- |
| `title` | draft title; required unless passed as an argument |
| `subtitle` | draft subtitle |
| `bibliography` | path to a `.bib`, relative to the markdown file |
| `csl` | CSL style override; defaults to the bundled Chicago notes style |
| `audience` | `everyone` (default) or a paid tier |
| `section` | publication section name |
| `reviewed` | citekey(s) of the work under review, rendered as a header blockquote |
| `substack_draft_id` | written by the script; links this file to its draft |

Paths — bibliographies, CSL files, images, includes — all resolve relative to the
**markdown file**, not the working directory, so a post folder is self-contained.

## The About page

`publish_about.py` sends a markdown file to the publication's About page
instead of to a draft:

```bash
uv run publish_about.py about.md
uv run substack-about about.md                 # same thing, via the entry point
uv run publish_about.py about.md --dry-run     # print the document, send nothing
uv run publish_about.py about.md -y            # don't prompt
```

It runs the same pipeline — includes, citations, image uploads, the
`{{subscribe}}` and `{{youtube}}` shortcodes — with these differences:

- **There is no draft.** The About page is a field on the publication, not a
  post, and Substack has no draft stage for it. A run replaces the live page
  at once. The prompt says so; `--dry-run` shows what would be sent.
- **No title or subtitle.** The page's heading is whatever `#` heading the
  markdown starts with. `title`, `subtitle`, `audience`, `section` and
  `reviewed` in the frontmatter are ignored; `bibliography` and `csl` work.
- **`{{subscribe}}` becomes a button, not a widget.** The About page's own
  template uses a plain subscribe button, so that is what the shortcode
  becomes here. The caption, if any, is the button's label — plain text.

What is known about the endpoint, since none of it is documented: the page is
`subscribe_content` on the publication, saved with
`PUT /api/v1/publication` as a JSON-encoded document in the post body format.
A PUT of that one field leaves the rest of the publication untouched. The
About editor's schema names its marks `italic` and `bold` where python-substack
writes `em` and `strong`, so the script renames them. All of this was found by
watching the web editor save the page.

## Things to know before trusting it

**It rewrites your markdown file.** After the first run it inserts
`substack_draft_id` into the frontmatter. That's how re-runs find the draft.

**Re-running replaces the entire draft body.** There is no merge. Any edit made
in Substack's web editor since the last push is discarded. The confirmation
prompt only appears when stdin is a tty — so the Neovim mapping, which runs
headless, never asks. If you edit in both places, you will lose the web edits.

**It monkeypatches the library.** `substack.post.parse_inline` is replaced at
import (see the comment at that line) because the stock implementation mishandles
nested bold/italic and links. That is a hook into another package's private
internals, which is why `python-substack` is pinned to an exact version in
`pyproject.toml` rather than floated. Bumping it means re-reading the patch and
doing a test publish — the failure mode is silently mangled formatting, not a
crash.

**The underlying API is unofficial.** Substack can change it without notice.
Always eyeball the draft in the web editor before publishing.

## Bundled files

`chicago-notes-bibliography.csl` is the Chicago Manual of Style 18th edition
(notes and bibliography) style from the [CSL styles
repository](https://github.com/citation-style-language/styles), used under
CC BY-SA 3.0. It is not covered by this repo's MIT license.
