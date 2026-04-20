# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VLM is a data processing pipeline that transforms raw IBM File Manager reports
(View Load Module function on z/OS) into queryable JSON and CSV files.
All source code and documentation is written in **French**.

**Domain vocabulary:**
- **Loadlib** — z/OS load library (PDS/PDSE containing executables)
- **Loadmod** — load module (an executable binary inside a loadlib)
- **CSECT** — Control SECTion (a compiled unit within a loadmod)
- **COPT** — Compilation OPTions (compiler flags: COBOL, C++, PL/I)
- **Identify** — package identifier in the form `AppCode/Hash/PackageCode`
- **LEINFO** — Language Environment metadata embedded inside COPT strings

## Development Commands

```bash
uv sync                        # install dependencies
uv run pytest                  # run all tests
uv run pytest tests/test_foo.py::test_bar  # run a single test
uv run ruff check . --fix      # lint and auto-fix
```

## Pipeline Architecture

Four sequential stages, each a standalone Python script in `src/`:

| Stage | Script | Input → Output |
|-------|--------|----------------|
| 1 | `clean_report.py` | Raw XML (iso8859-1, ASA chars) → Clean UTF-8 XML |
| 2 | `reformat_copt.py` | Clean XML → XML with normalized COPT strings |
| 3 | `build_json.py` | Normalized XML → Hierarchical JSON |
| 4 | `extract_copt.py` | JSON → CSV + per-loadlib text files |

**Orchestrator:** `src/pipeline.py` runs all stages in sequence.
Supports partial runs: `uv run src/pipeline.py 2-4` or
`uv run src/pipeline.py extract`.

**Query tool:** `script/export_csv.sh` — Bash script using `jq` and `awk`
that queries the JSON output. Three modes: `-g` (global), `-p` (options),
`-c` (compiler). Requires `jq` installed. Optional `-d yyyy/mm/dd` date filter.

**Shared utilities:** `src/utils.py` loads `config.toml` (logging, file paths)
and sets up a rotating file handler (`pipeline.log`, 2 GB max, 5 backups).

### JSON structure (Stage 3 output)

```
[ { Loadlib, MemberCount,
    Loadmods: [ { Name,
                  CSECTs: [ { Name, Compiler, Linkedon, Identify,
                              ThreadSafe, CICS, DB2, WMQ,  ← derived booleans
                              Copt: ["OPT1", "OPT2", ...] } ] } ] } ]
```

`ThreadSafe`, `CICS`, `DB2`, `WMQ` are derived by `build_json.py` from COPT
content — they do not appear in the raw XML.

## Package Manager

- Always use `uv`. Never suggest `pip` or `poetry`.
- Setup: `uv sync`
- Add dependency: `uv add <package>`
- Run script: `uv run <script.py>`

## Python Standards

- Python version: **3.12+**.
- Line length: **88 characters** maximum (Ruff/Black style).
- Type hints required on **all** function and method signatures (parameters
  and return type).
- f-strings for all string formatting; no `%` formatting, no `.format()`.
- `pathlib.Path` for all file-system paths; never `os.path`.
- `logging` module for all output in production code; `print()` only in
  one-off scripts or CLI entry points.
- Specific exceptions only — never bare `except:` or `except Exception:`.

### Naming conventions

| Element                 | Convention            | Example                         |
| ----------------------- | --------------------- | ------------------------------- |
| Variable / function     | `snake_case`          | `record_count`, `read_csv_file` |
| Class                   | `PascalCase`          | `CsvReader`, `SortKey`          |
| Constant (module-level) | `UPPER_SNAKE_CASE`    | `DEFAULT_DELIMITER`             |
| Private helper          | `_leading_underscore` | `_parse_header`                 |

### Documentation — accessibility first

**Goal: every source file must be readable by a beginner with no prior
context.** Assume the reader knows Python basics but nothing about the
mainframe domain.

#### Module docstring (mandatory on every `.py` file)

```python
"""
Short one-line summary of what this module does.

Longer description: purpose, inputs, outputs, key limitations.

Example:
    uv run script.py --input data/customers.csv
"""
```

#### Function / method docstring — Google Style

Mandatory on all public functions; strongly recommended on private helpers
> 5 lines.

```python
def compute_balance(debit: Decimal, credit: Decimal) -> Decimal:
    """Calculate the net balance after applying debit and credit.

    Args:
        debit: Total amount debited (must be >= 0).
        credit: Total amount credited (must be >= 0).

    Returns:
        Net balance as a Decimal: credit - debit.

    Raises:
        ValueError: If debit or credit is negative.
    """
```

Rules: `Args` required if any parameter exists. `Returns` required unless
`None`. `Raises` required for every raised exception. Plain language only.

#### Inline comments

Explain *why*, never *what*. Complete sentences, capital first letter,
max 2 lines — otherwise move to the docstring.

## Shell / Bash Standards

- Line length: **80 characters** maximum.
- Always start scripts with `set -euo pipefail`.
- Use `\` for line continuation to respect the 80-char limit.

## Data Handling (FR locale)

- CSV delimiter: `;` (semicolon).
- Encoding: UTF-8.
- Always specify `sep=';'` or `delimiter=';'` in Pandas/Polars IO calls.
- Use `.` as decimal separator for raw data.
