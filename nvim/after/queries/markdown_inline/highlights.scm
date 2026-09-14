; extends

; Pandoc / zotcite citations (`[@citekey]`) parse as CommonMark *shortcut
; links*, so the stock markdown_inline query conceals the brackets and paints
; the inner text with `@markup.link.label` -- i.e. it looks like a bare link.
;
; Re-capture citation shortcut links (link text starting with `@`) as
; `@markup.citation` and bump the priority to 5000 so it wins over the stock
; link-label highlight (priority 100). zotcite's own highlighting is disabled
; (hl_cite_key = false) so the leading `@` stays visible and gets coloured too,
; making a citation easy to distinguish from a link. The bracket concealment is
; left as-is; the `@markup.citation` highlight is defined in
; lua/plugins/zotero.lua.
((shortcut_link
  (link_text) @markup.citation)
  (#lua-match? @markup.citation "^@")
  (#set! priority 5000))
