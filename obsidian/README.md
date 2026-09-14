# obsidian

An export of my main Obsidian vault's configuration, for reference.

**This is not part of the Neovim → pandoc → Substack pipeline.** It is a separate,
older setup: reading, literature notes, and daily notes, using the Zotero
*desktop connector* rather than zotcite. Nothing in here feeds `publish/`. It is
included because people ask what the note-taking half of my setup looks like, not
because you need it to use the rest of this repo.

Exported 2026-09-14. It will drift; I re-export by hand.

## Use

Copy the JSON files into an existing vault's `.obsidian/` directory, then restart
Obsidian and install the community plugins listed below from within the app. Back
up your own config first — these files replace it wholesale.

```bash
cp config/*.json /path/to/your-vault/.obsidian/
```

## What's exported

`app.json`, `appearance.json`, `community-plugins.json`, `core-plugins.json`,
`hotkeys.json`, `templates.json`, `daily-notes.json`.

Deliberately **not** exported:

- `plugins/` — third-party plugin bundles, and their `data.json` files hold
  credentials — across the installed plugins those files carry API keys, a REST
  API certificate and a stored password. Never copy that directory anywhere
  public.
- `workspace.json`, `bookmarks.json`, `starred.json`, `graph.json`, `types.json` —
  window layout and pointers to specific private notes.
- `themes/` — install from within Obsidian instead.

## Notable settings

Vim mode on. Base font 20pt, `Shimmering Focus` theme, translucency, system
light/dark. Markdown-style links (not wikilinks), attachments in `Assets/`, new
files in `Default/`, templates in `! templates/` (excluded from search via
`userIgnoreFilters`). Daily notes at `Daily/YYYY/MM-MMMM/YYYY-MM-DD-dddd`.

## Community plugins

Writing and research:
`obsidian-zotero-desktop-connector`, `pdf-plus`, `obsidian-kindle-plugin`,
`smart-connections`, `dataview`, `templater-obsidian`, `obsidian-tasks-plugin`,
`obsidian-admonition`, `tag-wrangler`, `obsidian-outliner`,
`obsidian-auto-link-title`, `table-editor-obsidian`, `obsidian-dirtreeist`

Editing and UI:
`obsidian-vimrc-support`, `obsidian-relative-line-numbers`, `obsidian-hider`,
`obsidian-minimal-settings`, `cmdr`, `cm-editor-syntax-highlight-obsidian`,
`obsidian-excalidraw-plugin`

Integration:
`obsidian-local-rest-api`, `obsidian-advanced-uri`,
`obsidian-github-issues`, `github-tasks`, `co-intelligence`

(`obsidian-git` and a few others are installed in that vault but disabled, so
they are not in `community-plugins.json` and not listed here.)
