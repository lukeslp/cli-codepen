# CLAUDE.md

## What This Is

Python CLI tool that pushes local HTML/CSS/JS to CodePen via the Prefill API. Single file (`codepen_prefill.py`), zero dependencies beyond Python 3.8+.

**GitHub**: lukeslp/cli-codepen

## Commands

```bash
# Run tests
python3 tests/test_codepen_prefill.py

# Inbox workflow (default batch mode)
python3 codepen_prefill.py --batch

# Batch with explicit directory
python3 codepen_prefill.py --batch ./some-dir --outfile launcher.html

# Single file to CodePen
python3 codepen_prefill.py --single index.html

# Install in dev mode
pip install -e .
```

## Architecture

Single-module CLI (`codepen_prefill.py`) with no external dependencies.

**Input modes**: `--single` (parse one HTML), `--folder` (scan directory), `--html/--css/--js` (separate files), `--batch` (launcher page for many files)

**Inbox/sent workflow**: `--batch` with no directory defaults to `inbox/`, processes HTML files, moves them to `sent/<timestamp>/`. `--no-move` skips the move.

**Key functions**:
- `parse_single_html()` — lossless extraction of styles, scripts, externals, head, classes
- `generate_batch_html()` — launcher page with one CodePen button per file
- `ensure_dirs()` / `move_to_sent()` — inbox/sent file management
- `build_payload()` — assembles CodePen API JSON

**Duplicate file**: `codepen-prefill` is a copy of `codepen_prefill.py` — keep them in sync.

## File Layout

```
codepen_prefill.py     # Main module (canonical)
codepen-prefill        # Duplicate (keep in sync)
pyproject.toml         # Package config
inbox/                 # Drop HTML files here for --batch
sent/                  # Processed files moved here (timestamped subdirs)
tests/                 # Test suite (19 tests)
  test_codepen_prefill.py
  fixtures/            # Test fixtures (folder/, separate/, single/)
```

## Conventions

- Tests use plain assert + custom runner (no pytest required, but pytest-compatible)
- No external dependencies — stdlib only
- `inbox/*` and `sent/*` are gitignored (only `.gitkeep` tracked)
