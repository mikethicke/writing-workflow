import argparse
import os
import re
import shutil
import subprocess
import sys

import yaml
from dotenv import load_dotenv
import substack.post
from substack import Api
from substack.exceptions import SubstackAPIException
from substack.post import Post

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSL = os.path.join(SCRIPT_DIR, "chicago-notes-bibliography.csl")


def _load_credentials():
    """Load COOKIES_STRING / PUBLICATION_URL from the first .env that exists.

    COOKIES_STRING is a live Substack session cookie, so the default location
    is deliberately outside any repository: this script is checked out inside a
    public repo, and a .env sitting next to it is one `git add -f` away from
    being published. Search order:

      1. $SUBSTACK_ENV_FILE            -- explicit override, any path
      2. ~/.config/substack-publish/.env  (or $XDG_CONFIG_HOME)  -- the default
      3. .env beside this script       -- back-compat with the pre-split layout

    Anything already exported in the environment wins over all of these;
    load_dotenv does not overwrite existing variables.
    """
    explicit = os.environ.get("SUBSTACK_ENV_FILE")
    if explicit:
        # An override that points nowhere is a typo, not a reason to fall
        # through to a different account's credentials.
        if not os.path.isfile(explicit):
            sys.exit(f"SUBSTACK_ENV_FILE is set but not a file: {explicit}")
        load_dotenv(explicit)
        return explicit

    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    for candidate in (
        os.path.join(xdg, "substack-publish", ".env"),
        os.path.join(SCRIPT_DIR, ".env"),
    ):
        if os.path.isfile(candidate):
            load_dotenv(candidate)
            return candidate

    # Nothing found. Don't fail here -- --help and the credential-free parts of
    # the pipeline still work; publish() reports the missing values itself.
    return None


_load_credentials()

# Frontmatter key linking a markdown file to the Substack draft it produced.
DRAFT_ID_KEY = "substack_draft_id"

# Frontmatter key naming the work (or works) a review post is about. Rendered
# as a citation above the body rather than as a footnote; see
# prepend_reviewed_header.
REVIEWED_KEY = "reviewed"

# Pandoc-style inline citation: @key or [@key], where a key is letters/digits
# plus the internal punctuation Better BibTeX may emit. A backslash-escaped
# \@ (literal at-sign) is deliberately not matched.
_CITATION_RE = re.compile(r"(?<!\w)(?<!\\)@[\w][\w:.#$%&+?<>~/-]*")

# A single Better BibTeX key, as accepted in the `reviewed` frontmatter. This
# is deliberately stricter than _CITATION_RE: the key is interpolated into a
# YAML document below, so anything that could break out of a quoted scalar --
# a quote, a newline -- has to be rejected rather than escaped.
_CITEKEY_RE = re.compile(r"^[\w][\w:.#$%&+?<>~/-]*$")

# The `:::` fence pandoc wraps a rendered bibliography and its entries in.
_CSL_FENCE_RE = re.compile(r"^:{3,}")

# A URL scheme that citeproc has capitalized. A CSL style applies
# capitalize-first to whichever field a bare URL lands in -- `howpublished` in
# a BibTeX @misc reaches the style as the publisher, for instance -- turning
# `https://` into `Https://`. That reads wrong, and the patterns that linkify a
# bare URL further down would not recognise it.
_CAPITALIZED_SCHEME_RE = re.compile(r"\bHttps?(?=://)")


def parse_frontmatter(text):
    """Split Obsidian-style YAML frontmatter from the rest of the markdown.

    Returns (metadata_dict, body_without_frontmatter).
    """
    if not text.startswith("---"):
        return {}, text

    lines = text.splitlines(keepends=True)
    for i in range(1, len(lines)):
        if lines[i].startswith("---"):
            frontmatter = "".join(lines[1:i])
            body = "".join(lines[i + 1 :])
            return yaml.safe_load(frontmatter) or {}, body

    return {}, text


# A line that is nothing but an include directive: `-> ../responses.md`. The
# target has to end in .md so that a line of prose opening with an arrow is
# left alone, and a backslash -- `\-> not-an-include.md` -- escapes it.
_INCLUDE_RE = re.compile(r"^->[ \t]+(?P<path>\S+\.(?:md|markdown))[ \t]*$")
_ESCAPED_INCLUDE_RE = re.compile(r"^\\(->[ \t]+\S+\.(?:md|markdown)[ \t]*)$")

# Opening or closing fence of a code block, inside which nothing is a directive.
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def _rebase_images(content, from_dir, root_dir):
    """Rewrite an included file's image paths to mean the same thing spliced in.

    Image paths are resolved relative to the post being published, but a path
    written in an included file means what it says *there*. Re-expressing it
    relative to the post keeps it pointing at the same file once the two
    documents are one. (_IMAGE_RE lives with the rest of the image handling
    below.)
    """
    if os.path.realpath(from_dir) == os.path.realpath(root_dir):
        return content

    def replace(match):
        src = match.group("src")
        if _is_remote(src) or os.path.isabs(src):
            return match.group(0)
        rebased = os.path.relpath(os.path.join(from_dir, src), root_dir)
        return _format_image(match.group("alt"), rebased, _caption_of(match))

    return _IMAGE_RE.sub(replace, content)


def expand_includes(content, base_dir, root_dir, stack):
    """Splice `-> other.md` lines into the document, before anything else runs.

    A review series wants the same footer at the foot of every entry, and one
    file that every entry points at beats a paragraph pasted into each of them.
    The directive is replaced by the included file's body, so by the time
    citations are resolved and images are uploaded there is a single document
    again and every later pass sees the included text as if it had been typed
    in place.

    Paths are relative to the file the directive appears in, so an included
    file can include others relative to itself; `base_dir` is that file's
    directory and `root_dir` the published post's, which is what image paths
    end up relative to. Frontmatter in an included file is stripped, except
    that its `bibliography` is collected and merged into the post's, so a
    citation in a shared footer resolves against the footer's own .bib.

    Returns (expanded_content, bibliographies), the latter absolute paths.
    """
    out = []
    bibs = []
    fence = None

    for line in content.splitlines():
        match = _FENCE_RE.match(line)
        if match:
            marker = match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            out.append(line)
            continue
        if fence is not None:
            out.append(line)
            continue

        escaped = _ESCAPED_INCLUDE_RE.match(line)
        if escaped:
            out.append(escaped.group(1))
            continue

        match = _INCLUDE_RE.match(line)
        if not match:
            out.append(line)
            continue

        written = match.group("path")
        path = written if os.path.isabs(written) else os.path.join(base_dir, written)
        path = os.path.realpath(path)
        if not os.path.isfile(path):
            sys.exit(f"Included file not found: {path} (written as '{written}' in {stack[-1]})")
        if path in stack:
            chain = " -> ".join(stack + (path,))
            sys.exit(f"Include loop: {chain}")

        with open(path, "r") as f:
            metadata, body = parse_frontmatter(f.read())

        included_dir = os.path.dirname(path)
        bib = metadata.get("bibliography")
        for entry in bib if isinstance(bib, list) else [bib] if bib else []:
            bibs.append(os.path.realpath(os.path.join(included_dir, entry)))

        body, nested = expand_includes(body, included_dir, root_dir, stack + (path,))
        bibs.extend(nested)

        # Blank lines either side: the included text is its own set of blocks,
        # and must not run into the paragraph above or below the directive.
        out.append("")
        out.append(_rebase_images(body, included_dir, root_dir).strip("\n"))
        out.append("")

    return "\n".join(out), bibs

def record_draft_id(markdown_path, draft_id):
    """Write the Substack draft id back into the file's YAML frontmatter.

    This is what makes a later run an update rather than a second draft. The
    file is rewritten line by line rather than round-tripped through PyYAML so
    that comments, key order, and hand-wrapped values survive untouched. Files
    with no frontmatter get a minimal block prepended.
    """
    with open(markdown_path, "r") as f:
        lines = f.readlines()

    entry = f"{DRAFT_ID_KEY}: {draft_id}\n"

    if lines and lines[0].startswith("---"):
        for i in range(1, len(lines)):
            if lines[i].startswith("---"):
                for j in range(1, i):
                    if lines[j].split(":", 1)[0].strip() == DRAFT_ID_KEY:
                        lines[j] = entry
                        break
                else:
                    lines.insert(i, entry)
                break
        else:
            # Unterminated frontmatter: parse_frontmatter read the whole file
            # as body, so treat it as having none.
            lines = ["---\n", entry, "---\n", "\n"] + lines
    else:
        lines = ["---\n", entry, "---\n", "\n"] + lines

    with open(markdown_path, "w") as f:
        f.writelines(lines)


def confirm_overwrite(draft_id, assume_yes):
    """Ask before clobbering an existing draft, when there's someone to ask.

    Updating replaces the draft body wholesale, so anything typed into the
    Substack web editor since the last sync is lost. Non-interactive callers
    (the Neovim mapping runs the script with no tty) proceed without asking --
    blocking on stdin there would hang the editor.
    """
    if assume_yes or not sys.stdin.isatty():
        return True
    answer = input(
        f"Overwrite Substack draft {draft_id}? Edits made in the web editor "
        "will be lost. [y/N] "
    )
    return answer.strip().lower() in ("y", "yes")


def _normalize_urls(text):
    """Lower-case any URL scheme citeproc capitalized.

    Applied to everything that comes back from citeproc so that a bare URL in
    a reference is written the way it is everywhere else, and so that the
    inline parser recognises it and Substack gets a real link.
    """
    return _CAPITALIZED_SCHEME_RE.sub(lambda match: match.group(0).lower(), text)


def _citeproc_command(metadata, base_dir):
    """Build the pandoc invocation that resolves this document's citations.

    Shared by the two things that need citeproc -- the footnotes in the body and
    the reviewed-work header -- so both are rendered from the same bibliography
    and the same style, and a broken path is reported the same way whichever
    one hits it first. The caller adds whatever else its own pass needs.
    """
    # `bibliography` may be a single path or a list; paths are relative to the
    # markdown file, matching how zotcite and pandoc interpret them.
    bib = metadata.get("bibliography")
    bib_paths = bib if isinstance(bib, list) else [bib]
    cmd = ["pandoc", "-f", "markdown", "-t", "markdown", "--wrap=preserve",
           "--citeproc"]
    for path in bib_paths:
        resolved = path if os.path.isabs(path) else os.path.join(base_dir, path)
        if not os.path.isfile(resolved):
            sys.exit(f"Bibliography file not found: {resolved}")
        cmd += ["--bibliography", resolved]

    csl = metadata.get("csl")
    csl = (csl if os.path.isabs(csl) else os.path.join(base_dir, csl)) if csl else DEFAULT_CSL
    if not os.path.isfile(csl):
        sys.exit(f"CSL style file not found: {csl}")
    return cmd + ["--csl", csl]


def resolve_citations(content, metadata, base_dir):
    """Turn pandoc @citekeys into formatted footnotes via pandoc + citeproc.

    zotcite inserts `@key` citations and keeps the .bib file named in the
    document's `bibliography:` frontmatter up to date. Substack's markdown
    importer knows nothing about citations, so we resolve them here first.

    A note-based CSL (Chicago notes-bibliography by default) renders each
    citation as a real footnote, which merges and renumbers with any manual
    `[^n]` footnotes and maps onto Substack's native footnote blocks. The
    standalone bibliography is suppressed on purpose: as a fenced `#refs` div
    it would not survive Substack's importer, and full-note citations already
    carry the complete reference.

    Returns the resolved markdown, or the original content unchanged when no
    bibliography is configured or the document contains no citations.
    """
    if not metadata.get("bibliography"):
        return content
    if not _CITATION_RE.search(content):
        return content

    if shutil.which("pandoc") is None:
        sys.exit(
            "Document has citations and a 'bibliography' but pandoc is not "
            "installed. Install pandoc or remove the citations."
        )

    cmd = _citeproc_command(metadata, base_dir) + ["-M", "suppress-bibliography=true"]
    result = subprocess.run(cmd, input=content, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"pandoc failed to resolve citations:\n{result.stderr}")
    return _normalize_urls(result.stdout)


def render_reference(citekey, metadata, base_dir):
    """Render one bibliography entry as a single line of markdown.

    The note CSL turns every `[@key]` into a footnote, which is the wrong shape
    for the work a review is *about*: that citation belongs in the body, above
    the first paragraph, where a reader meets it before the argument. Asking
    citeproc for a bibliography of exactly one entry yields the same reference
    in its bibliography form -- surname first, periods -- which is the
    conventional shape for a review header.
    """
    cmd = _citeproc_command(metadata, base_dir)
    result = subprocess.run(
        cmd, input=f'---\nnocite: "@{citekey}"\n---\n',
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.exit(
            f"pandoc failed to render the reviewed work '{citekey}':\n{result.stderr}"
        )

    # Drop the `:::` fences of the .csl-bib-body div. --wrap=preserve keeps the
    # entry itself on one line; joining is defensive in case a style emits more.
    entry = " ".join(
        line.strip()
        for line in _normalize_urls(result.stdout).splitlines()
        if line.strip() and not _CSL_FENCE_RE.match(line.strip())
    )
    if not entry:
        # citeproc renders an unknown key as an empty bibliography and still
        # exits 0, so silence here means the key is missing, not that the entry
        # is blank. Failing loudly matters: a header that quietly vanishes is
        # easy to miss in the Substack editor.
        sys.exit(
            f"Reviewed work '{citekey}' is not in the bibliography. Check the "
            "key, and that the item is still in this post's Zotero collection."
        )
    return entry


def prepend_reviewed_header(content, metadata, base_dir):
    """Put the reviewed work's full citation above the post, as a blockquote.

    A review needs to say what it is reviewing before it starts reviewing, and
    a footnote marker on the first line does not do that. `reviewed:` in the
    frontmatter names the work; the citation is rendered from `references.bib`
    on every publish, so it tracks corrections made in Zotero instead of
    quietly going stale the way a hand-pasted reference would. Several works
    may be listed, and they keep the order they were written in -- one pandoc
    run each, because a single run would sort them the way the CSL wants.

    This runs after resolve_citations, so citeproc never sees the header. It
    does not count as a first citation: a later `[@key]` for the same work
    still renders as a full first-reference footnote.
    """
    reviewed = metadata.get(REVIEWED_KEY)
    if not reviewed:
        return content
    if not metadata.get("bibliography"):
        sys.exit(
            f"'{REVIEWED_KEY}' needs a 'bibliography' in the frontmatter to "
            "render the citation from."
        )
    if shutil.which("pandoc") is None:
        sys.exit(
            f"Document has a '{REVIEWED_KEY}' work but pandoc is not installed. "
            f"Install pandoc or remove '{REVIEWED_KEY}'."
        )

    keys = reviewed if isinstance(reviewed, list) else [reviewed]
    entries = []
    for key in keys:
        # zotcite writes keys bare, but `@key` is how they are written
        # everywhere else in the document, so accept both spellings.
        key = str(key).lstrip("@")
        if not _CITEKEY_RE.match(key):
            sys.exit(f"Not a usable citation key in '{REVIEWED_KEY}': {key!r}")
        entries.append("> " + render_reference(key, metadata, base_dir))

    # A bare `>` between entries makes each reviewed work its own paragraph
    # within the one blockquote, which is what unwrap_soft_breaks rebuilds.
    return "\n>\n".join(entries) + "\n\n" + content.lstrip("\n")


# Inline markdown constructs, in the order they win a tie when two of them
# start at the same offset. Anything inside backticks is literal, so `code`
# comes first; `***x***` must beat `**x**`, and `**x**` must beat `*x*`.
_INLINE_PATTERNS = (
    ("code", re.compile(r"`([^`]+)`")),
    ("link", re.compile(r"\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\(([^)]+)\)")),
    ("bold_italic", re.compile(r"\*\*\*(.+?)\*\*\*")),
    ("bold", re.compile(r"\*\*(.+?)\*\*")),
    ("italic", re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")),
    ("strikethrough", re.compile(r"~~(.+?)~~")),
    # <https://example.com> -- how pandoc writes a bare URL, and how the DOIs
    # in CSL-rendered citation footnotes arrive.
    ("autolink", re.compile(r"<((?:https?|mailto):[^>\s]+)>")),
    # A URL typed straight into the prose. The last character is constrained so
    # that sentence punctuation right after the URL stays out of the link.
    ("url", re.compile(r"(?i:https?)://[^\s<>\[\]()]*[^\s<>\[\]().,;:!?'\"]")),
)

_MARKS = {
    "code": ({"type": "code"},),
    "bold_italic": ({"type": "strong"}, {"type": "em"}),
    "bold": ({"type": "strong"},),
    "italic": ({"type": "em"},),
    "strikethrough": ({"type": "strikethrough"},),
}


def _with_marks(marks, *new):
    """Add marks, ignoring any whose type is already applied.

    A construct nested inside one of its own kind -- a bare URL inside a
    markdown link's label, say -- would otherwise emit the same mark type
    twice, which ProseMirror treats as malformed. The outer one wins, which
    matches how markdown reads it.
    """
    kinds = {mark["type"] for mark in marks}
    return marks + tuple(m for m in new if m["type"] not in kinds)


def _next_inline_match(text, pos):
    """The earliest inline construct at or after `pos`, or None."""
    best = None
    for kind, pattern in _INLINE_PATTERNS:
        for match in pattern.finditer(text, pos):
            # `![alt](url)` is an image, not a link. Inline images aren't
            # supported in a paragraph anyway, so skip past it and keep
            # looking rather than mangling it into a link.
            if kind == "link" and match.start() and text[match.start() - 1] == "!":
                continue
            # A bare URL that is really an image target -- `![alt](url)` -- or
            # the inside of an autolink we failed to close is already spoken
            # for; linking it would strand the surrounding punctuation.
            if kind == "url" and (
                text[max(0, match.start() - 2):match.start()] == "]("
                or text[match.start() - 1:match.start()] == "<"
            ):
                continue
            if best is None or match.start() < best[1].start():
                best = (kind, match)
            break
    return best


def parse_inline(text, marks=()):
    """Parse inline markdown into marked text tokens, honouring nesting.

    Replaces python-substack's own parse_inline, which collects every match
    from every pattern into one flat list and never looks inside a match. That
    breaks whenever formatting nests. An italicised link, `*[Title](url)*`,
    matches the italic *and* the link patterns over overlapping spans, and both
    get emitted -- the raw `[Title](url)` markdown rendered in italics, then the
    link, then a leftover `*`. Writing it the other way round, `[*Title*](url)`,
    instead yields a link whose visible text is literally `*Title*`.

    This version scans left to right for the earliest construct, then recurses
    into that construct's own text carrying the accumulated marks down, so
    either spelling produces one link that is also italic.
    """
    tokens = []
    pos = 0
    while pos < len(text):
        found = _next_inline_match(text, pos)
        if found is None:
            break
        kind, match = found

        if match.start() > pos:
            tokens.append({"content": text[pos:match.start()], "marks": list(marks)})

        if kind in ("autolink", "url"):
            # The URL is its own visible text, so there is nothing to recurse
            # into -- and nothing inside it should be read as markdown.
            href = match.group(1) if kind == "autolink" else match.group(0)
            display = href[len("mailto:"):] if href.startswith("mailto:") else href
            link = {"type": "link", "attrs": {"href": href}}
            tokens.append({"content": display, "marks": list(_with_marks(marks, link))})
        elif kind == "code":
            # Backticks fence off markdown: whatever is inside is literal.
            tokens.append({"content": match.group(1), "marks": list(_with_marks(marks, *_MARKS[kind]))})
        elif kind == "link":
            link = {"type": "link", "attrs": {"href": match.group(2)}}
            tokens.extend(parse_inline(match.group(1), _with_marks(marks, link)))
        else:
            tokens.extend(parse_inline(match.group(1), _with_marks(marks, *_MARKS[kind])))

        pos = match.end()

    if pos < len(text):
        tokens.append({"content": text[pos:], "marks": list(marks)})

    return [token for token in tokens if token["content"]]


# python-substack calls parse_inline as a module global from every one of its
# block handlers (paragraphs, list items, blockquotes), so rebinding it here
# fixes them all at once.
substack.post.parse_inline = parse_inline


# A line that opens a block of its own, so the line above it must not swallow
# it as a continuation.
_BLOCK_START_RE = re.compile(
    r"""^[ \t]*(
        \#{1,6}[ \t]                    # heading
      | >                               # blockquote
      | [-*+][ \t]                      # bullet
      | \d+[.)][ \t]                    # ordered list item
      | \[\^[^\]]+\]:                   # footnote definition
      | !\[                             # image
      | \|                              # table row
      | ```                             # code fence
      | (-{3,}|\*{3,}|_{3,})[ \t]*$     # horizontal rule
    )""",
    re.VERBOSE,
)

# The converse: a line that is complete in itself and never continues onto the
# next one, however the author wrapped it.
_NO_CONTINUATION_RE = re.compile(
    r"^[ \t]*(\#{1,6}[ \t]|!\[|\||(-{3,}|\*{3,}|_{3,})[ \t]*$)"
)

# Markdown's explicit line break: two trailing spaces, or a trailing backslash.
_HARD_BREAK_RE = re.compile(r"(  |\\)$")


def _join_soft_breaks(lines):
    """Collapse each run of soft-wrapped lines into a single line.

    Markdown reads a lone newline inside a paragraph as a space, and only a
    blank line as a paragraph break. Returns (paragraph, blank_line_after)
    pairs, one per paragraph.
    """
    paragraphs = []
    open_paragraph = False
    for line in lines:
        if not line.strip():
            # A blank line ends the paragraph, even inside a blockquote where
            # it arrives as a bare `>`.
            open_paragraph = False
            continue
        # Drop the break marker itself; a trailing backslash would otherwise
        # show up verbatim in the post.
        text = _HARD_BREAK_RE.sub("", line).strip()
        if not text:
            # A line holding nothing but a break marker.
            if paragraphs:
                paragraphs[-1][1] = True
            open_paragraph = False
            continue
        if (
            open_paragraph
            and not _BLOCK_START_RE.match(line)
            and not _NO_CONTINUATION_RE.match(paragraphs[-1][0])
        ):
            paragraphs[-1][0] += " " + text
        else:
            paragraphs.append([text, False])
        # python-substack has no hard-break node, so the closest it can render
        # an explicit break as is a paragraph break -- which is already what a
        # trailing "  " produced. Writing it out as a real blank line makes
        # that explicit and keeps the rewrite stable if it runs twice.
        hard_break = bool(_HARD_BREAK_RE.search(line))
        paragraphs[-1][1] = hard_break
        open_paragraph = not hard_break
    return [tuple(paragraph) for paragraph in paragraphs]


def unwrap_soft_breaks(content):
    """Rejoin hard-wrapped prose so each paragraph is one line.

    python-substack turns every single line of a block into its own ProseMirror
    paragraph. For text wrapped at some fixed column -- anything pasted out of a
    terminal, or the pandoc-formatted quotations in these posts -- that yields a
    stack of one-line paragraphs. It looks passable on a desktop, where the
    original wrap width is close to the column width, but on a phone every line
    re-wraps and the quotation comes out as ragged, over-spaced fragments.

    Blockquotes are rebuilt marker and all, which also repairs lazy
    continuations: python-substack only recognises a quote line that literally
    begins with `>`, so an unprefixed continuation line would otherwise fall out
    of the quotation and become body text.

    Fenced code is copied through untouched -- its line breaks are the content.
    """
    out = []
    quote = []
    plain = []
    in_fence = False

    def flush_plain():
        for paragraph, blank_after in _join_soft_breaks(plain):
            out.append(paragraph)
            if blank_after:
                out.append("")
        plain.clear()

    def flush_quote():
        # Paragraphs within the quotation are already separated by a bare `>`,
        # so an explicit break needs nothing extra here.
        for i, (paragraph, _) in enumerate(_join_soft_breaks(quote)):
            if i:
                out.append(">")
            out.append("> " + paragraph)
        quote.clear()

    for line in content.split("\n"):
        if line.strip().startswith("```"):
            flush_plain()
            flush_quote()
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue

        if not line.strip():
            flush_plain()
            flush_quote()
            if out and out[-1].strip():
                out.append("")
            continue

        marker = re.match(r"[ \t]*>[ \t]?", line)
        if marker:
            flush_plain()
            quote.append(line[marker.end():])
        elif quote and not _BLOCK_START_RE.match(line):
            # Lazy continuation: still part of the quotation above.
            quote.append(line)
        else:
            flush_quote()
            plain.append(line)

    flush_plain()
    flush_quote()
    return "\n".join(out)


# Markdown image reference: ![alt](src), with an optional title -- either
# ![alt](src "caption") or ![alt](src 'caption'). Substack has no use for a
# title attribute, so the pipeline reads it as the image's caption: the text
# rendered under the image, separate from the alt text.
_IMAGE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\("
    r"(?P<src>[^)\s]+)"
    r"""(?:[ \t]+(?:"(?P<caption_d>[^"]*)"|'(?P<caption_s>[^']*)'))?"""
    r"\)"
)

# A whole line that is nothing but an image, possibly wrapped in a link.
_IMAGE_LINE_RE = re.compile(r"^\s*\[?" + _IMAGE_RE.pattern + r"\)?(\]\([^)\s]+\))?\s*$")


def _is_remote(src):
    return src.startswith(("http://", "https://", "//", "data:"))


def _caption_of(match):
    """The caption written as an _IMAGE_RE title, or "" if there wasn't one."""
    for group in ("caption_d", "caption_s"):
        caption = match.group(group)
        if caption is not None:
            return caption.strip()
    return ""


def _format_image(alt, src, caption):
    """Render an image reference, carrying any caption through as a title.

    Used where the result is handed back to _IMAGE_RE rather than to Substack,
    so it has to round-trip. A caption containing a double quote is written
    with single quotes instead; one containing both is beyond what markdown
    title syntax can express, and the outer quotes are dropped from it.
    """
    if not caption:
        return f"![{alt}]({src})"
    if '"' not in caption:
        return f'![{alt}]({src} "{caption}")'
    if "'" not in caption:
        return f"![{alt}]({src} '{caption}')"
    stripped = caption.replace('"', "")
    return f'![{alt}]({src} "{stripped}")'


def isolate_image_lines(content):
    """Put a blank line either side of any line that is just an image.

    python-substack splits the document into blocks on blank lines and treats a
    block starting with `!` as a single image, silently discarding the rest of
    the block. An image written directly above a paragraph -- normal in Obsidian
    -- would therefore eat that paragraph. Separating them keeps both.
    """
    out = []
    in_fence = False
    for line in content.split("\n"):
        if line.strip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.strip() and _IMAGE_LINE_RE.match(line):
            if out and out[-1].strip():
                out.append("")
            out.append(line)
            out.append("")
            continue
        # A blank line we just inserted stands in for one written by hand.
        if not in_fence and not line.strip() and out and not out[-1].strip():
            continue
        out.append(line)
    return "\n".join(out)


def upload_images(content, base_dir, api):
    """Upload locally-referenced images and point the markdown at Substack.

    python-substack does try to upload local images itself, but it resolves the
    path against the current working directory rather than the document, and it
    swallows any failure -- so publishing `![](images/foo.png)` from anywhere
    but the post's own directory quietly produces an "IMAGE NOT FOUND" block in
    the draft. Doing it here means paths resolve relative to the markdown file
    and a failed upload stops the run instead of shipping a broken draft.

    Returns (content, images), where images records every image in document
    order so the resulting nodes can be given real dimensions, alt text and
    captions. Remote images are recorded too -- nothing to upload, but they
    still need their alt text and caption written onto the node.

    The markdown handed back has any caption title stripped out. Substack
    carries the caption in a node of its own rather than an attribute, and
    python-substack's image pattern is non-greedy enough that a title would
    otherwise be swallowed into the src.
    """
    images = []

    def replace(match):
        src = match.group("src")
        alt = match.group("alt")
        caption = _caption_of(match)

        if _is_remote(src):
            images.append({"url": src, "alt": alt, "caption": caption, "meta": {}})
            return f"![{alt}]({src})"

        path = src if os.path.isabs(src) else os.path.join(base_dir, src)
        if not os.path.isfile(path):
            sys.exit(f"Image not found: {path} (referenced as '{src}')")

        try:
            uploaded = api.get_image(path)
        except Exception as exc:
            sys.exit(f"Failed to upload image '{src}': {exc}")

        url = uploaded.get("url")
        if not url:
            sys.exit(f"Substack accepted image '{src}' but returned no URL.")

        images.append({"url": url, "alt": alt, "caption": caption, "meta": uploaded})
        print(f"Uploaded {src}")
        return f"![{alt}]({url})"

    return _IMAGE_RE.sub(replace, content), images


def apply_image_attrs(post, images):
    """Give the images their real size, alt text and captions.

    python-substack emits every plain markdown image with no alt text and a
    hardcoded 1456x819 frame, which stretches anything that is not 16:9. The
    upload response carries the true dimensions, so patch them in afterwards.
    Nodes are matched in document order, so the same image used twice still
    gets the alt text written at each spot.

    A caption is not an attribute in Substack's schema: it is a `caption` node
    sitting beside the `image2` node inside the `captionedImage` wrapper, whose
    content is inline text with no intervening paragraph. python-substack never
    builds one, so it is appended here.
    """
    pending = list(images)
    for node in post.draft_body.get("content", []):
        if node.get("type") != "captionedImage":
            continue
        for child in node.get("content", []):
            attrs = child.get("attrs") or {}
            record = next((r for r in pending if r["url"] == attrs.get("src")), None)
            if record is None:
                continue
            pending.remove(record)

            if record["alt"] and not attrs.get("alt"):
                attrs["alt"] = record["alt"]

            width = record["meta"].get("imageWidth")
            height = record["meta"].get("imageHeight")
            if width and height:
                attrs["width"] = width
                attrs["height"] = height
                attrs["resizeWidth"] = min(width, 728)

            if record["caption"]:
                # Rebinding rather than appending: the loop above is walking
                # the old list, which must not grow underneath it.
                node["content"] = node.get("content", []) + [
                    {
                        "type": "caption",
                        "content": [{"type": "text", "text": record["caption"]}],
                    }
                ]


def publish(markdown_path, title=None, subtitle=None, force_new=False, assume_yes=False):
    with open(markdown_path, "r") as f:
        raw = f.read()

    metadata, content = parse_frontmatter(raw)
    base_dir = os.path.dirname(os.path.abspath(markdown_path))

    content, included_bibs = expand_includes(
        content, base_dir, base_dir, (os.path.realpath(markdown_path),)
    )
    if included_bibs:
        declared = metadata.get("bibliography") or []
        declared = list(declared) if isinstance(declared, list) else [declared]
        seen = {os.path.realpath(os.path.join(base_dir, p)) for p in declared}
        for path in included_bibs:
            if path not in seen:
                declared.append(path)
                seen.add(path)
        metadata["bibliography"] = declared

    content = resolve_citations(content, metadata, base_dir)
    content = prepend_reviewed_header(content, metadata, base_dir)

    title = title or metadata.get("title")
    if not title:
        sys.exit("No title given (pass as an argument or set 'title' in frontmatter).")
    subtitle = subtitle if subtitle is not None else metadata.get("subtitle", "")
    audience = metadata.get("audience", "everyone")
    section = metadata.get("section")

    recorded_id = metadata.get(DRAFT_ID_KEY)
    draft_id = None if force_new else recorded_id

    cookies_string = os.getenv("COOKIES_STRING")
    publication_url = os.getenv("PUBLICATION_URL")
    missing = [
        name
        for name, value in (
            ("COOKIES_STRING", cookies_string),
            ("PUBLICATION_URL", publication_url),
        )
        if not value
    ]
    if missing:
        # Without this, Api() fails somewhere inside python-substack with an
        # error that says nothing about the real problem.
        sys.exit(
            f"Missing {' and '.join(missing)}.\n"
            f"Copy .env.example to ~/.config/substack-publish/.env and fill it "
            f"in (or point $SUBSTACK_ENV_FILE at your own file)."
        )

    api = Api(
        cookies_string=cookies_string,
        publication_url=publication_url,
    )
    user_id = api.get_user_id()

    post = Post(title=title, subtitle=subtitle, user_id=user_id, audience=audience)

    if section:
        post.set_section(section, api.get_sections())

    content = unwrap_soft_breaks(isolate_image_lines(content))
    content, images = upload_images(content, base_dir, api)
    # No `api=` here on purpose: every local image is already a CDN URL, and
    # letting python-substack re-post those URLs to /image would upload each
    # one a second time and could hand back a src that no longer matches what
    # apply_image_attrs is looking for.
    post.from_markdown(content)
    apply_image_attrs(post, images)

    if draft_id:
        if not confirm_overwrite(draft_id, assume_yes):
            sys.exit("Aborted; draft left unchanged.")
        try:
            api.put_draft(draft_id, **post.get_draft())
        except SubstackAPIException as exc:
            if exc.status_code == 404:
                sys.exit(
                    f"Draft {draft_id} no longer exists in Substack (deleted or "
                    f"already published). Re-run with --new to create a fresh "
                    f"draft, or remove '{DRAFT_ID_KEY}' from the frontmatter."
                )
            raise
        action = "updated"
    else:
        draft = api.post_draft(post.get_draft())
        draft_id = draft.get("id")
        record_draft_id(markdown_path, draft_id)
        if recorded_id:
            print(f"Note: previous draft {recorded_id} is now orphaned in Substack.")
        action = "created"

    print(f"Draft {action}: {draft_id}")
    print(f"Edit it at: {publication_url}/publish/post/{draft_id}")


def main():
    parser = argparse.ArgumentParser(
        description="Create or update a Substack draft from a markdown file."
    )
    parser.add_argument("markdown_path", help="path to the markdown file")
    parser.add_argument(
        "title", nargs="?", help="draft title (defaults to frontmatter 'title')"
    )
    parser.add_argument(
        "subtitle", nargs="?", help="draft subtitle (defaults to frontmatter 'subtitle')"
    )
    parser.add_argument(
        "--new",
        action="store_true",
        help=f"create a new draft even if the file already has a {DRAFT_ID_KEY}",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="skip the confirmation prompt when overwriting an existing draft",
    )
    args = parser.parse_args()
    publish(args.markdown_path, args.title, args.subtitle, args.new, args.yes)


if __name__ == "__main__":
    main()
