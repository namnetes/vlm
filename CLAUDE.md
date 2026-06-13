# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ETL pipeline that transforms IBM File Manager VLM (View Load Module) XML
reports into structured JSON and CSV.

**AGENTS.md is the canonical, AI-assistant-shared reference** for this repo —
domain glossary, full command list, the 4-step pipeline architecture,
per-script responsibilities, key invariants, and exit codes. Read it first
and keep it in sync with any structural change.

## Quick commands

```bash
uv sync                                          # install deps
make run                                         # full pipeline (datas/vlm.xml -> datas/vlm.json + copt/)
make run STEPS=2-4                               # partial run (aliases: clean|copt|json|extract)
make query QUERY_MODE=-g|-p|-c                   # datas/vlm.json -> CSV via script/export_csv.sh
uv run pytest tests/test_foo.py::test_bar -v     # single test
uv run ruff check src/ tests/ --fix              # lint + autofix
uv run mypy src/                                 # type check
make docs / docs-build                           # MkDocs (port auto-detected 8000-8050)
```

## Repo-specific conventions (override global defaults)

- `ruff.toml`: line-length **80** (not 88), target `py312`. `D`
  (pydocstyle), `TRY`, `PL`, `FBT` rule sets are enabled — every public
  function needs a Google-style docstring with Args/Returns/Raises.
- `mypy --strict` on `src/` (configured in `pyproject.toml`).
- Commit titles enforced by `gitlint`: Conventional Commits, ≤ 72 chars
  (see AGENTS.md "Commit messages").

## Structure notes not covered in AGENTS.md

- `datas/` is entirely gitignored (large generated files plus the ~385 MB
  raw `vlm.xml` input) — never assume anything under it is tracked.
- `doc/` is the MkDocs source; each pipeline script has a matching
  `doc/<script>/business_rules.md` page — update these when business rules
  in `src/` change.
- `draft/` holds work-in-progress prompts for AI assistants, not part of
  the runtime pipeline.
- `doc/glossaire.md` is the canonical domain glossary, part of the MkDocs
  nav — keep terminology consistent with it across `doc/` and `AGENTS.md`.
- `script/export_csv.sh` is a standalone jq-based query path, independent
  of the Python pipeline.
