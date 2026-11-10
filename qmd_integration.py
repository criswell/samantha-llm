#!/usr/bin/env python3
"""
qmd index integration for the cerebrum.

qmd's file scanner skips any path segment that starts with "." (hidden
directories), and the cerebrum stores memories under hidden `.ai/`
directories (`.ai/<area>/.ai/*.md`). A collection rooted at the cerebrum's
`.ai` directory therefore only sees pre-restructure strays, which is how
the search index once went silently stale for months.

The fix is a "view" directory: a tree of symlinks that presents the same
memory files through non-hidden paths. qmd's scan follows symlinks, so
the view gives it full reach into the cerebrum. The view is disposable
cache (rebuilt on every refresh) and lives under
~/.cache/samantha-llm/qmd-view.

Refresh flow (refresh_qmd_index):
  1. build_qmd_view: (re)create the symlink view
  2. ensure_collection: point the qmd collection at the view (only
     re-points when the stored path drifts; editing the collection is
     otherwise a full reindex)
  3. qmd update: incremental rescan (new + changed files)
  4. qmd embed: only when the update reports pending vectors (embeds are
     resumable; a timeout just leaves the remainder pending)

Both `samantha-llm memories index` and merge_sessions.py call
refresh_qmd_index() so the index never goes stale silently.

All qmd subprocess calls are timeout-guarded: the rerank path inside qmd
is known to hang on some setups, and an unguarded subprocess turns any
hang into a frozen caller.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_COLLECTION_NAME = "samantha-cerebrum"
DEFAULT_GLOB_MASK = "**/*.md"

# Memory areas stored under <cerebrum>/.ai/<area>/.ai (canonical layout).
# `subconscious` is deliberately not indexed: it holds transient session
# workspaces, not durable memories.
MEMORY_AREAS = [
    "short-term-memory",
    "long-term-memory",
    "current-tasks",
    "work-experience",
    "procedural-memory",
]

# Non-hidden cerebrum subtrees that are also worth searching.
EXTRA_DIRS = ["ralph-guardrails"]

DEFAULT_EMBED_TIMEOUT = 3600  # full-corpus first embed can take ~30 min
UPDATE_TIMEOUT = 180


def _print(msg):
    print(msg, flush=True)


def get_qmd_bin():
    """Locate the qmd binary (PATH, then bun-style ~/node_modules)."""
    found = shutil.which("qmd")
    if found:
        return found
    bun_global = Path.home() / "node_modules" / "qmd" / "qmd"
    if bun_global.exists() and os.access(bun_global, os.access.X_OK):
        return str(bun_global)
    return None


def _run_qmd(args, timeout, index_name=None):
    """Run a qmd command with a hard timeout. Returns (rc, stdout, stderr).

    Raises subprocess.TimeoutExpired so callers can decide how to degrade.
    """
    qmd = get_qmd_bin()
    if not qmd:
        raise RuntimeError("qmd binary not found")
    cmd = [qmd]
    if index_name:
        cmd.extend(["--index", index_name])
    cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def _view_root():
    return Path.home() / ".cache" / "samantha-llm" / "qmd-view"


def build_qmd_view(cerebrum_path):
    """(Re)build the symlink view of the cerebrum's memory corpus.

    Returns the view root Path. Raises RuntimeError when symlinks cannot
    be created (e.g. Windows without Developer Mode), so callers can warn
    and skip qmd indexing rather than silently indexing nothing.
    """
    cerebrum = Path(cerebrum_path)
    ai_root = cerebrum / ".ai"
    if not ai_root.is_dir():
        raise RuntimeError(f"no .ai directory under {cerebrum}")

    view = _view_root()

    # Paranoia guard: this directory is wiped on every rebuild, so it must
    # live under the user's cache dir before we rmtree anything.
    cache_root = Path.home() / ".cache"
    if cache_root not in view.parents:
        raise RuntimeError(f"view root {view} is outside ~/.cache; refusing to rebuild")

    if view.exists():
        shutil.rmtree(view)
    view.mkdir(parents=True)

    linked_areas = []
    failures = []

    for area in MEMORY_AREAS:
        src = ai_root / area / ".ai"
        if src.is_dir():
            try:
                os.symlink(src, view / area)
                linked_areas.append(area)
            except OSError as e:
                failures.append(f"{area}: {e}")

    for extra in EXTRA_DIRS:
        src = ai_root / extra
        if src.is_dir():
            try:
                os.symlink(src, view / extra)
                linked_areas.append(extra)
            except OSError as e:
                failures.append(f"{extra}: {e}")

    # Top-level cerebrum docs (.ai/*.md), linked individually so the view
    # root does not pull the area directories in a second time.
    doc_count = 0
    for doc in sorted(ai_root.glob("*.md")):
        try:
            os.symlink(doc, view / doc.name)
            doc_count += 1
        except OSError as e:
            failures.append(f"{doc.name}: {e}")

    if failures and not linked_areas and not doc_count:
        raise RuntimeError(
            "could not create symlinks for the qmd view ("
            + "; ".join(failures[:3])
            + "). On Windows, enable Developer Mode or run as Administrator."
        )

    return view


def _collection_config_path(index_name=None):
    """qmd stores collections in ~/.config/qmd/<index_name>.yml.

    The default index uses index.yml; a custom --index name gets its own
    config file of the same name.
    """
    name = index_name if index_name else "index"
    return Path.home() / ".config" / "qmd" / f"{name}.yml"


def _configured_collection_path(collection_name, index_name=None):
    """Read the collection's configured path from qmd's index config."""
    cfg = _collection_config_path(index_name)
    if not cfg.exists():
        return None
    try:
        import yaml
        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        entry = (data.get("collections") or {}).get(collection_name) or {}
        return entry.get("path")
    except Exception:
        return None


def ensure_collection(view_root, collection_name=DEFAULT_COLLECTION_NAME,
                      index_name=None):
    """Make sure the qmd collection points at the view root.

    Returns (ok, created) where created is True when the collection was
    added or re-pointed (full reindex) rather than left untouched.
    """
    view = str(Path(view_root).resolve())

    configured = _configured_collection_path(collection_name, index_name)
    if configured and Path(configured).resolve() == Path(view):
        return True, False

    # Best-effort remove (the collection may not exist yet), then add.
    if configured:
        try:
            _run_qmd(["collection", "remove", collection_name], timeout=60,
                     index_name=index_name)
        except Exception:
            pass

    try:
        rc, out, err = _run_qmd(
            ["collection", "add", view, "--name", collection_name,
             "--mask", DEFAULT_GLOB_MASK],
            timeout=300, index_name=index_name)
    except subprocess.TimeoutExpired:
        raise RuntimeError("qmd collection add timed out")

    if rc != 0:
        raise RuntimeError(f"qmd collection add failed: {err.strip() or out.strip()}")

    # Set the collection context once for search-quality (idempotent).
    try:
        _run_qmd(
            ["context", "add", "/",
             "Personal memory system for Samantha Hartwell, an AI software "
             "engineer. Contains memories of past work, technical decisions, "
             "and ongoing projects."],
            timeout=60, index_name=index_name)
    except Exception:
        pass  # context is a nice-to-have, never fatal

    return True, True


def refresh_qmd_index(cerebrum_path, collection_name=DEFAULT_COLLECTION_NAME,
                      index_name=None, embed=True,
                      embed_timeout=DEFAULT_EMBED_TIMEOUT, quiet=False):
    """Full refresh: rebuild view, ensure collection, update, embed if needed.

    Returns True on success. Never raises for qmd-side failures (prints a
    warning and returns False) so callers like merge_sessions can treat
    this as best-effort. Only build_qmd_view's symlink problems and qmd
    absences propagate as exceptions, and those are also caught by the
    callers that need to degrade gracefully.
    """
    def info(msg):
        if not quiet:
            _print(msg)

    qmd = get_qmd_bin()
    if not qmd:
        info("qmd is not installed; skipping index refresh")
        return False

    # 1. View
    try:
        view = build_qmd_view(cerebrum_path)
    except RuntimeError as e:
        info(f"qmd view build skipped: {e}")
        return False

    # 2. Collection
    try:
        _, created = ensure_collection(view, collection_name=collection_name,
                                       index_name=index_name)
        if created:
            info("qmd collection (re)created pointing at the memory view")
    except RuntimeError as e:
        info(f"qmd collection setup failed: {e}")
        return False

    # 3. Update (incremental rescan)
    try:
        rc, out, err = _run_qmd(["update"], timeout=UPDATE_TIMEOUT,
                                index_name=index_name)
    except subprocess.TimeoutExpired:
        info("qmd update timed out; index left as-is (safe to retry)")
        return False

    if rc != 0:
        info(f"qmd update failed: {err.strip() or out.strip()}")
        return False

    # 4. Embed only when there is pending work (embeds are resumable).
    pending = 0
    m = re.search(r"(\d+) unique hashes? need vectors", out)
    if m:
        pending = int(m.group(1))

    if embed and pending > 0:
        info(f"embedding {pending} new/changed file(s)...")
        try:
            rc, out, err = _run_qmd(["embed"], timeout=embed_timeout,
                                    index_name=index_name)
            if rc != 0:
                info(f"qmd embed failed: {err.strip() or out.strip()}")
                return False
        except subprocess.TimeoutExpired:
            # Embed is resumable: whatever completed is stored, the rest
            # stays pending and the next refresh picks it up.
            info("qmd embed timed out; remaining vectors stay pending "
                 "(next refresh resumes)")
            return False

    return True


if __name__ == "__main__":
    # Manual smoke: python3 qmd_integration.py <cerebrum-path>
    if len(sys.argv) < 2:
        print("usage: qmd_integration.py <cerebrum-path>")
        sys.exit(1)
    ok = refresh_qmd_index(Path(sys.argv[1]))
    sys.exit(0 if ok else 1)
