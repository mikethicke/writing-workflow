"""Replace a Substack publication's About page with a markdown file.

The About page is not a post. Substack stores it as one field on the
publication -- `subscribe_content`, a JSON-encoded document in the same format
as a post body -- and there is no draft stage: writing the field changes the
live page at once. So this runs publish_draft's pipeline (includes, citations,
image uploads, markdown conversion) and then, instead of creating a draft,
PUTs the document to /api/v1/publication.

None of that endpoint is documented. It was found by watching the web editor
save the page; see publish/README.md for what is known about it.
"""

import argparse
import json
import os
import sys

from substack import Api
from substack.post import Post

import autocommit
import publish_draft as draft

# The label Substack's own About page template gives its subscribe button.
_DEFAULT_BUTTON_TEXT = "Subscribe now"

# python-substack writes emphasis with the mark names the post editor uses;
# the About page editor's schema names the same marks differently. Read off
# the live editor (`.ProseMirror`'s pmViewDesc.node.type.schema.marks), whose
# full list is: link, textStyle, bold, code, highlight, italic, strike,
# subscript, superscript.
_EDITOR_MARKS = {"em": "italic", "strong": "bold"}


def rename_marks(node):
    """Rename marks in place, recursively, to the About editor's names."""
    for mark in node.get("marks") or []:
        mark["type"] = _EDITOR_MARKS.get(mark["type"], mark["type"])
    for child in node.get("content") or []:
        rename_marks(child)


def insert_subscribe_buttons(post, captions, publication_url):
    """Replace each `{{subscribe}}` placeholder paragraph with a button node.

    A post gets a subscribeWidget (email box plus caption); the About page's
    own template uses a plain `button` node pointing at the subscribe URL, so
    that is what a shortcode becomes here. The shortcode's caption, if any, is
    the button's label -- plain text, not markdown, because a button label
    cannot carry formatting.
    """
    tokens = {draft._SUBSCRIBE_TOKEN.format(i): i for i in range(len(captions))}
    found = set()

    content = []
    for node in post.draft_body.get("content", []):
        text = "".join(child.get("text", "") for child in node.get("content") or [])
        index = tokens.get(text.strip()) if node.get("type") == "paragraph" else None
        if index is None:
            content.append(node)
            continue
        found.add(index)
        content.append({
            "type": "button",
            "attrs": {
                # The trailing `?` is what Substack's template emits; kept as-is.
                "url": f"{publication_url}/subscribe?",
                "text": captions[index] or _DEFAULT_BUTTON_TEXT,
                "action": None,
                "class": None,
            },
        })
    post.draft_body["content"] = content

    if len(found) != len(captions):
        sys.exit(
            "A {{subscribe}} shortcode did not survive conversion. Make sure it "
            "is alone on its line, outside any list or blockquote."
        )


def confirm_replace(publication_url, assume_yes):
    """Ask before replacing the live page, when there's someone to ask.

    Same rule as publish_draft.confirm_overwrite: non-interactive callers (the
    Neovim mapping) proceed without a prompt. The stakes are higher here --
    there is no draft to review first -- which is what the wording says.
    """
    if assume_yes or not sys.stdin.isatty():
        return True
    answer = input(
        f"Replace the live About page at {publication_url}/about? This takes "
        "effect immediately, and edits made in the web editor will be lost. [y/N] "
    )
    return answer.strip().lower() in ("y", "yes")


def build_document(markdown_path, api, publication_url):
    """Run the markdown through the post pipeline and return the document body."""
    with open(markdown_path, "r") as f:
        raw = f.read()

    metadata, content = draft.parse_frontmatter(raw)
    base_dir = os.path.dirname(os.path.abspath(markdown_path))

    content, included_bibs = draft.expand_includes(
        content, base_dir, base_dir, (os.path.realpath(markdown_path),)
    )
    draft.merge_included_bibliographies(metadata, base_dir, included_bibs)

    content, subscribe_captions = draft.extract_subscribe_widgets(content)
    content, youtube_ids = draft.extract_youtube_embeds(content)
    content = draft.resolve_citations(content, metadata, base_dir)
    # No reviewed-work header: an About page is not a review.

    content = draft.unwrap_soft_breaks(draft.isolate_image_lines(content))
    content, images = draft.upload_images(content, base_dir, api)

    # Post is only a container for its draft_body here: the title, subtitle
    # and byline it also holds are never sent. user_id is required by the
    # constructor and unused.
    post = Post(title="About", subtitle="", user_id=0)
    post.from_markdown(content)
    draft.apply_image_attrs(post, images)
    if subscribe_captions:
        insert_subscribe_buttons(post, subscribe_captions, publication_url)
    if youtube_ids:
        draft.insert_youtube_embeds(post, youtube_ids)
    rename_marks(post.draft_body)
    return post.draft_body


def publish(markdown_path, assume_yes=False, dry_run=False):
    cookies_string, publication_url = draft.require_credentials()
    api = Api(cookies_string=cookies_string, publication_url=publication_url)

    body = build_document(markdown_path, api, publication_url)

    if dry_run:
        print(json.dumps(body, indent=1, ensure_ascii=False))
        print("\nDry run: About page left unchanged.", file=sys.stderr)
        return

    if not confirm_replace(publication_url, assume_yes):
        sys.exit("Aborted; About page left unchanged.")

    # python-substack has no method for this endpoint, and its generic call()
    # sends arguments as query parameters where a JSON body is needed, so this
    # goes through the library's requests session directly. That is a private
    # attribute -- the other reason python-substack is pinned exactly.
    response = api._session.put(
        f"{publication_url}/api/v1/publication",
        json={"subscribe_content": json.dumps(body)},
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    if response.status_code == 401:
        sys.exit("Substack returned 401: the session cookie has probably expired.")
    if not response.ok:
        sys.exit(
            f"Substack returned {response.status_code} updating the About page:\n"
            f"{response.text[:500]}"
        )

    print(f"About page updated: {publication_url}/about")
    autocommit.safe_run("publish", markdown_path)


def main():
    parser = argparse.ArgumentParser(
        description="Replace the publication's About page with a markdown file."
    )
    parser.add_argument("markdown_path", help="path to the markdown file")
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="skip the confirmation prompt before replacing the live page",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the document that would be sent, and send nothing",
    )
    args = parser.parse_args()
    publish(args.markdown_path, args.yes, args.dry_run)


if __name__ == "__main__":
    main()
