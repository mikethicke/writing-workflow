"""Automatic git commits for a writing repo.

Opt-in per repo: it does nothing unless `.autocommit.toml` exists at the
repository root. Three triggers, all commit *everything* not .gitignored:

  save <file>     after a save: commit if >= threshold_words words changed
                  since the last commit (nvim BufWritePost)
  exit <file>     on closing the editor: commit any pending change
  publish <file>  after a Substack push: commit the post's directory

Commit messages are written by a small model through the `claude` CLI, with a
plain fallback message if that fails. Nothing here may break the caller: every
failure is reported on stderr and the exit status stays 0.

Config (`.autocommit.toml`, all keys optional):

    enabled = true            # master switch
    push = true               # git push after each commit
    remote = ""               # default: the branch's upstream
    threshold_words = 100     # words changed before a save commits
    model = "haiku"           # passed to `claude --model`
    prefix_publish = "Substack push: "
"""

import argparse
import fcntl
import os
import subprocess
import sys
import tempfile
import tomllib

CONFIG_NAME = ".autocommit.toml"
DEFAULTS = {
    "enabled": True,
    "push": True,
    "remote": "",
    "threshold_words": 100,
    "model": "haiku",
    "prefix_publish": "Substack push: ",
}
MAX_DIFF_CHARS = 12000  # what the model gets to see
MODEL_TIMEOUT = 60
PUSH_TIMEOUT = 60


def git(root, *args, check=True, timeout=None):
    result = subprocess.run(
        ["git", "-C", root, *args],
        capture_output=True, text=True, timeout=timeout,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def find_root(path):
    """The repo root containing `path` if it has a config file, else None."""
    start = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    result = subprocess.run(
        ["git", "-C", start, "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    root = result.stdout.strip()
    return root if os.path.isfile(os.path.join(root, CONFIG_NAME)) else None


def load_config(root):
    with open(os.path.join(root, CONFIG_NAME), "rb") as f:
        user = tomllib.load(f)
    unknown = set(user) - set(DEFAULTS)
    if unknown:
        print(f"autocommit: unknown config keys ignored: {sorted(unknown)}", file=sys.stderr)
    return {**DEFAULTS, **{k: v for k, v in user.items() if k in DEFAULTS}}


def _count_words(text):
    return len(text.split())


def words_changed(root):
    """Words added plus removed in the working tree relative to HEAD.

    Untracked, unignored text files count by their whole length. A repo with
    no commits yet compares against the empty tree.
    """
    has_head = subprocess.run(
        ["git", "-C", root, "rev-parse", "--verify", "-q", "HEAD"],
        capture_output=True,
    ).returncode == 0
    total = 0
    if has_head:
        diff = git(root, "diff", "HEAD", "--word-diff=porcelain", "-U0", "--no-color")
        for line in diff.splitlines():
            if line[:1] in "+-" and not line.startswith(("+++", "---")):
                total += _count_words(line[1:])
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    for rel in filter(None, untracked):
        try:
            with open(os.path.join(root, rel), "r", encoding="utf-8") as f:
                total += _count_words(f.read())
        except (UnicodeDecodeError, OSError):
            pass  # binary or unreadable: committed, but adds nothing to the count
    return total


def fallback_message(root):
    stat = git(root, "diff", "--cached", "--shortstat").strip()
    names = git(root, "diff", "--cached", "--name-only").split()
    what = names[0] if len(names) == 1 else f"{len(names)} files"
    return f"Autosave: {what}" + (f" ({stat})" if stat else "")


def model_message(root, cfg, context):
    """One-line commit message from a small model, or None on any failure."""
    diff = git(root, "diff", "--cached", "--no-color", "--word-diff=plain", "-U1")
    if not diff.strip():
        return None
    prompt = (
        "Write a git commit message for this edit to an essay draft. "
        "One line, under 72 characters, imperative mood, say what changed in "
        "the writing (e.g. 'Tighten intro; add paragraph on tariffs'). "
        f"{context}Output only the message.\n\n"
        f"<diff>\n{diff[:MAX_DIFF_CHARS]}\n</diff>"
    )
    try:
        # Run from a scratch directory so no project CLAUDE.md/hooks apply.
        with tempfile.TemporaryDirectory() as scratch:
            result = subprocess.run(
                ["claude", "-p", "--model", cfg["model"], "--tools", "",
                 "--no-session-persistence", "--disable-slash-commands"],
                input=prompt, capture_output=True, text=True,
                timeout=MODEL_TIMEOUT, cwd=scratch,
            )
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = result.stdout.strip().splitlines() if result.returncode == 0 else []
    message = lines[0].strip().strip("`\"'") if lines else ""
    return message[:100] or None


def commit_and_push(root, cfg, paths=None, prefix=""):
    """Stage `paths` (default: everything), commit, optionally push."""
    git(root, "add", "-A", "--", *(paths or ["."]))
    if subprocess.run(["git", "-C", root, "diff", "--cached", "--quiet"]).returncode == 0:
        return  # nothing staged
    context = "This commit accompanies pushing the post to Substack. " if prefix else ""
    message = prefix + (model_message(root, cfg, context) or fallback_message(root))
    git(root, "commit", "-q", "-m", message)
    print(f"autocommit: {message}")
    if cfg["push"]:
        push(root, cfg)


def _remote_args(cfg):
    return [cfg["remote"], "HEAD"] if cfg["remote"] else []


def _git_quiet(root, *args):
    return subprocess.run(
        ["git", "-C", root, *args],
        capture_output=True, text=True, timeout=PUSH_TIMEOUT,
    )


def push(root, cfg):
    """Push; if the remote has moved on, merge it in and push again.

    A conflicting merge is aborted, leaving the local commits as they were, and
    pushing stops until the user sorts it out by hand.
    """
    remote = _remote_args(cfg)
    result = _git_quiet(root, "push", "-q", *remote)
    if result.returncode == 0:
        return
    pull = _git_quiet(root, "pull", "--no-rebase", "--no-edit", "-q", *remote)
    if pull.returncode != 0:
        if merge_in_progress(root):
            _git_quiet(root, "merge", "--abort")
            print("autocommit: remote has diverged and merging conflicts; "
                  "merge aborted, not pushed. Resolve by hand.", file=sys.stderr)
        else:
            print(f"autocommit: pull failed: {pull.stderr.strip()}", file=sys.stderr)
        return
    print("autocommit: merged remote changes")
    result = _git_quiet(root, "push", "-q", *remote)
    if result.returncode != 0:
        print(f"autocommit: push failed: {result.stderr.strip()}", file=sys.stderr)


def _git_path_exists(root, name):
    path = git(root, "rev-parse", "--git-path", name).strip()
    return os.path.exists(os.path.join(root, path))


def merge_in_progress(root):
    return _git_path_exists(root, "MERGE_HEAD")


def unfinished_operation(root):
    """True mid-merge/rebase/cherry-pick or with unresolved conflicts.

    Committing then would bake conflict markers into history, so all triggers
    stand down until the user finishes the operation.
    """
    if any(_git_path_exists(root, n) for n in
           ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD")):
        return True
    return bool(git(root, "ls-files", "--unmerged").strip())


def run(mode, path):
    root = find_root(path)
    if not root:
        return
    cfg = load_config(root)
    if not cfg["enabled"]:
        return
    if unfinished_operation(root):
        print("autocommit: merge/rebase in progress or conflicts unresolved; skipping",
              file=sys.stderr)
        return

    # One run at a time per repo: rapid saves must not race on the index. A
    # run that finds the lock held just skips; the next save picks it up.
    lock_path = git(root, "rev-parse", "--git-path", "autocommit.lock").strip()
    lock = open(os.path.join(root, lock_path), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    try:
        if mode == "save":
            if words_changed(root) >= cfg["threshold_words"]:
                commit_and_push(root, cfg)
        elif mode == "exit":
            commit_and_push(root, cfg)
        elif mode == "publish":
            post_dir = os.path.dirname(os.path.abspath(path))
            commit_and_push(root, cfg, [post_dir], cfg["prefix_publish"])
    finally:
        lock.close()


def safe_run(mode, path):
    """run(), but never raises: callers are editors and publish scripts."""
    try:
        run(mode, path)
    except Exception as exc:  # noqa: BLE001 - must not break the caller
        print(f"autocommit: {exc}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Automatic git commits for a writing repo.")
    parser.add_argument("mode", choices=["save", "exit", "publish"])
    parser.add_argument("path", help="a file or directory inside the repo")
    args = parser.parse_args()
    safe_run(args.mode, args.path)


if __name__ == "__main__":
    main()
