# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ETL pipeline that transforms IBM File Manager VLM (View Load Module) XML reports into structured JSON and CSV. VLM reports describe the load modules of an IBM z/OS loadlib.

**Domain glossary (used throughout the codebase):**

| Term | Meaning |
|------|---------|
| VLM | View Load Module — IBM File Manager function that analyses z/OS load libraries |
| Loadlib | Load Library — PDS/PDSE containing executable load modules |
| Loadmod | Load Module — an executable program inside a loadlib |
| CSECT | Control SECTion — a compiled unit inside a load module |
| COPT | Compilation OPTions — IBM compiler flags (COBOL, C/C++, PL/I) |
| LEINFO | Pseudo-COPT token containing LE internal metadata — not a real compiler option |

## Commands

```bash
uv sync                           # install / update dependencies

make run                          # run the full pipeline (all 4 steps)
make run STEPS=2-4                # run steps 2 to 4 only
make clean                        # delete caches + all pipeline-produced files
                                  # (never touches datas/vlm.xml or datas/copt/ dir)

make docs                         # serve MkDocs in foreground (port auto-detected 8000–8050)
make docs-start                   # serve in background (.mkdocs.pid)
make docs-stop                    # stop background server
make docs-build                   # compile to site/

uv run pytest                     # all tests with coverage
uv run pytest tests/test_foo.py::test_bar -v   # single test
uv run ruff check src/ tests/     # lint
uv run ruff check src/ tests/ --fix            # lint + auto-fix
uv run mypy src/                  # type check
```

## Architecture

### Pipeline — 4 steps in sequence

`src/pipeline.py` orchestrates the chain via `subprocess.run(sys.executable, ...)`.
Any non-zero exit code stops the pipeline immediately.

```
datas/vlm.xml  (ISO-8859-1, raw mainframe input — never deleted by clean)
  │
  ▼  [1] clean_report.py    → datas/clean_vlm.xml
  ▼  [2] reformat_copt.py   → datas/clean_vlm_copt.xml  +  datas/copt_ignored.txt
  ▼  [3] build_json.py      → datas/vlm.json
  ▼  [4] extract_copt.py    → datas/copt/copt.csv  +  datas/copt/loadlibs/**/*.txt
```

Configurable paths (`vlm_input`, `final_json`, `copt_csv`) live in `config.toml [settings]`.
Intermediate files (`clean_vlm.xml`, `clean_vlm_copt.xml`, `copt_ignored.txt`) are hard-coded in `pipeline.py`.

### Per-step responsibilities

**`clean_report.py`** — strips ASA printer-control characters and noise lines from the raw report; injects `loadlib` and `memberCount` attributes into `<vlm>` tags; exits with code 1 on business error `FMNBF427`.

**`reformat_copt.py`** — normalises `Copt@Val` so a plain `split()` later isolates each option. Core logic: paren-depth-aware tokeniser (spaces inside `OPTION(A,B)` do not split the token). LEINFO handling has three modes: `placeholder` (default — replaces with `LEINFO=(N)` and saves originals to `copt_ignored.txt`), `remove`, `keep`.

**`build_json.py`** — parses the XML tree (Loadlib → Loadmod → CSECT) into a JSON list. Derives boolean flags (`ThreadSafe`, `CICS`, `DB2`, `WMQ`) from CSECT name patterns. Extracts the `Identify` package code (third `/`-delimited segment) after regex validation; invalid or absent → `null`.

**`extract_copt.py`** — streams JSON rows into `copt.csv` (one line per CSECT that has COPT options). **Refuses to overwrite an existing output file** — `pipeline.py` explicitly deletes it before step 4. Also writes per-CSECT `.txt` files under `datas/copt/loadlibs/<loadlib>/`.

### Shared utilities — `src/utils.py`

Single entry point for config and logging used by every script:
- `load_config()` — reads `config.toml` via stdlib `tomllib`; exits 2 if missing, 3 if invalid TOML
- `setup_logging(config, name)` — attaches a `RotatingFileHandler` (→ `datas/pipeline.log`) and a stderr `StreamHandler` (WARNING+ only). Logger names match script names: `clean_report`, `reformat_copt`, `build_json`, `extract_copt`, `pipeline`.

### Alternative query interface — `script/export_csv.sh`

Uses `jq` to query `datas/vlm.json` directly, bypassing the Python pipeline. Three modes (`-g` global / `-p` options / `-c` compiler) with an optional date filter (`-d yyyy/mm/dd`). Requires `jq` in PATH.

### Debug utility — `src/inspect_copt.py`

Prints every `Copt@Val` from any XML file. Useful to compare before/after `reformat_copt.py`:
```bash
uv run python src/inspect_copt.py -f datas/clean_vlm.xml
uv run python src/inspect_copt.py -f datas/clean_vlm_copt.xml
```

## Key invariants

- `sys.executable` is used for all subprocess calls — ensures the same virtualenv is active in every step.
- `extract_copt.py` refuses to overwrite its CSV output; `pipeline.py` handles deletion before step 4.
- Steps 1–3 overwrite their outputs silently on re-run.
- COPT tokenisation is paren-depth-aware — spaces inside parentheses never split a token.
- `LEINFO` mode defaults to `placeholder`; the pipeline does not pass `--leinfo-mode` explicitly.

## Exit codes (consistent across all scripts)

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Business error (FMNBF427 in raw VLM report) |
| `2` | File / directory not found or not writable |
| `3` | XML or JSON parse error |
| `10` | Unexpected I/O error |
