# CLAUDE.md — AI Assistant Guide for credit_mutuel_pdf_extractor

This file provides context for AI assistants (Claude Code and similar tools) working in this repository.

---

## Project Overview

`credit_mutuel_pdf_extractor` is a Python CLI tool that extracts bank transactions from Crédit Mutuel PDF statements and exports them to CSV, JSON, or Google Sheets.

- **CLI command:** `cmut_process_pdf`
- **Entry point:** `src/credit_mutuel_pdf_extractor/main.py:main`
- **Python version:** 3.11 (see `.python-version`)
- **Package manager:** `uv` (lockfile: `uv.lock`)
- **Task runner:** `just` (see `Justfile`)

---

## Repository Layout

```
credit_mutuel_pdf_extractor/
├── src/credit_mutuel_pdf_extractor/
│   ├── __init__.py          # Empty package marker
│   ├── main.py              # CLI, PDF parsing, export logic (328 lines)
│   └── utils.py             # Helper functions: parse_amount, find_account_headers, format_date (55 lines)
├── config.example.yaml      # Template for config.yaml (never commit the real one)
├── pyproject.toml           # Project metadata, dependencies, entry point
├── Justfile                 # Task automation recipes
├── uv.lock                  # Pinned dependency versions
├── .pre-commit-config.yaml  # Pre-commit hook definitions
├── .secrets.baseline        # Baseline for detect-secrets
├── .python-version          # Pins Python 3.11
└── README.md                # End-user documentation
```

---

## Architecture

The code is split into two modules:

### `main.py` — Business Logic & CLI
- Parses CLI arguments (`argparse`)
- Loads `config.yaml` via PyYAML
- Iterates over PDF files using `pdfplumber`
- Identifies accounts per page via `find_account_headers()` (Y-coordinate based)
- Extracts transaction rows from tables matching column headers: `Date`, `Opération`/`Libellé`, `Débit`, `Crédit`
- Validates balances: `start_balance + sum(transactions) == end_balance` (tolerance: 0.01)
- Generates a SHA256 `UID` per transaction for deduplication
- Exports results to CSV, JSON, or Google Sheets

### `utils.py` — Pure Helper Functions
- `parse_amount(s)` — converts French number format (`"1.234,56"`) to float (`1234.56`)
- `find_account_headers(page)` — extracts account numbers (9–11 digits) with their Y-coordinates from a PDF page
- `format_date(s)` — normalises `DD/MM/YY` or `DD/MM/YYYY` to `ISO YYYY-MM-DD`

### Transaction Data Model
Each extracted transaction is a dict with these keys:

| Field        | Type   | Description                                      |
|-------------|--------|--------------------------------------------------|
| `Account`   | str    | Account number (mapped to label if config provides one) |
| `Date`      | str    | ISO date `YYYY-MM-DD`                            |
| `Description` | str  | Original French text from the PDF                |
| `Comment`   | str    | Mapped description (from config) or empty string |
| `Amount`    | float  | Positive = credit, negative = debit              |
| `LocalIndex` | int   | Transaction sequence number within the account   |
| `UID`       | str    | SHA256 hash for deduplication                    |
| `SourceFile` | str   | Source PDF filename (optional, via `--source-file` flag) |

---

## Development Workflow

### Environment Setup

```bash
# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the tool locally for development
just install

# Or install dependencies for editing
uv sync
```

### Running the Tool

```bash
# Process PDFs, output CSV (default)
just run

# Process PDFs, output JSON
just run json

# Export to Google Sheets
just gsheet

# Remove generated output files
just clean
```

Full CLI syntax:
```bash
cmut_process_pdf data/*.pdf --output results.csv --config config.yaml [--format json] [--gsheet]
```

### Pre-commit Hooks

Pre-commit is the primary code quality gate. Always run before committing:

```bash
# Run all hooks on all files
just check

# Or directly
pre-commit run --all-files
```

Hooks configured (`.pre-commit-config.yaml`):
- `check-yaml` / `check-json` — syntax validation
- `check-added-large-files` — prevents accidental large file commits
- `end-of-file-fixer` / `trailing-whitespace` — formatting
- `detect-secrets` — prevents credential leaks (baseline: `.secrets.baseline`)
- `forbidden-mutual` — enforces correct spelling "Mutuel" (not "mutual")

**Never use `--no-verify` to skip hooks.**

### Packaging & Publishing

```bash
# Build the package
just build

# Publish to PyPI (requires 1Password access for token)
just publish
```

---

## Configuration File

The tool expects a `config.yaml` at the path passed via `--config`. See `config.example.yaml` for the structure:

```yaml
account_mapping:
  123456789: "Main Checking"    # int keys — leading zeros are lost

description_mapping:
  "VIR SEPA FROM": "Transfer"  # case-insensitive substring match

google_sheets:
  spreadsheet_id: "YOUR_SPREADSHEET_ID"
  sheet_name: "Transactions"
  credentials_file: "credentials.json"
```

**Security:** `config.yaml` and `credentials.json` are git-ignored. They are managed via 1Password:
```bash
just secrets-pull   # download from 1Password vault
just secrets-push   # upload to 1Password vault
just secrets-setup  # initial vault setup
```

---

## Key Conventions

### Python Style
- Python 3.11+, no type hints currently in the codebase
- Standard library `logging` module — use `logger = logging.getLogger(__name__)`
- Log levels: `INFO` for progress, `WARNING` for non-critical issues, `ERROR` for failures, `CRITICAL` for balance discrepancies
- Use `sys.exit(1)` on unrecoverable errors
- Use `yaml.safe_load()` only — never `yaml.load()`

### Regex Patterns
- Account numbers: `\d{9,11}(\.\.\.)?` (9–11 digits, optional ellipsis suffix)
- Dates: `(\d{2})/(\d{2})/(\d{2,4})`
- Column header matching: substring search (case-sensitive French column names)

### Balance Validation
Balance validation is non-negotiable. If `abs(start + transactions - end) > 0.01`, log CRITICAL and skip the account's transactions. Do not relax this threshold without explicit justification.

### Google Sheets Deduplication
When merging new data with existing sheet data:
- Deduplication key: `['Account', 'Date', 'Description', 'Amount']`
- `SourceFile` is excluded from the key (statements can overlap)
- `keep='last'` — new data takes precedence over old

### Spelling
The pre-commit hook enforces: always write **"Mutuel"** (French), never "mutual".

---

## Dependencies

| Package      | Version   | Purpose                        |
|-------------|-----------|-------------------------------|
| `pdfplumber` | >=0.11.9  | PDF text/table extraction      |
| `pandas`     | >=2.0.0   | DataFrame manipulation, export |
| `PyYAML`     | >=6.0.1   | Config file parsing            |
| `gspread`    | >=6.1.4   | Google Sheets API client       |

Dev dependencies: `pre-commit`, `detect-secrets`

Add new dependencies via:
```bash
uv add <package>        # runtime dependency
uv add --dev <package>  # dev-only dependency
```

---

## What Does Not Exist (Yet)

- **No test suite** — no `tests/` directory, no pytest, no unittest
- **No CI/CD** — no GitHub Actions or other pipelines
- **No type annotations** — the codebase uses no `typing` hints

When adding tests, use `pytest` and place them in `tests/`. When adding type hints, use Python 3.11 syntax (`list[str]`, `dict[str, int]`, `str | None`).

---

## Common Tasks for AI Assistants

### Adding a new export format
1. Add format handling in `main.py` alongside the existing CSV/JSON branches
2. Add a corresponding `just` recipe in `Justfile`
3. Document in `README.md`

### Modifying transaction parsing
- Table column detection is in `main.py` — look for the `any(... in col ...)` patterns
- Amount parsing is in `utils.parse_amount()` — handles French locale formatting
- Date parsing is in `utils.format_date()`

### Updating dependencies
```bash
uv add <package>@latest   # upgrade a specific package
uv lock --upgrade          # upgrade all packages
```

### Debugging PDF parsing issues
Enable verbose logging and inspect page-level output with `pdfplumber`:
```python
with pdfplumber.open("file.pdf") as pdf:
    for page in pdf.pages:
        print(page.extract_text())
        print(page.extract_tables())
```
