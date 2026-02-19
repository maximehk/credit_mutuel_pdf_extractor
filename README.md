# Crédit Mutuel PDF Extractor

[![PyPI version](https://img.shields.io/pypi/v/credit_mutuel_pdf_extractor.svg)](https://pypi.org/project/credit_mutuel_pdf_extractor/)

A robust Python utility to extract transaction data from Crédit Mutuel bank statement PDFs, validate data integrity, and export to structured formats (JSON/CSV) or Google Sheets.

## Features

- **Automated Extraction**: Parses transaction dates, descriptions, and amounts from multiple accounts per PDF.
- **Balance Validation**: Computes the sum of transactions and cross-references them with the starting and ending balances provided in the statement.
- **Strict CLI**: Explicit input file list and mandatory `--output` flag (with `.csv` or `.json` validation).
- **French Format Support**: Handles French number formatting (e.g., `1.234,56` or `1 234,56`).
- **Structured Logging**: Uses the Python `logging` module for clean, professional output and error reporting.
- **Automation**: Includes a `Justfile` for common tasks like `run` and `clean`.
- **Account Mapping**: Support for custom account labels via YAML configuration.
- **Google Sheets Export**: Direct export to a Google Spreadsheet.

## Installation

You can install the extractor directly from PyPI:

```bash
pip install credit_mutuel_pdf_extractor
```

Or using [uv](https://github.com/astral-sh/uv):

```bash
uv tool install credit_mutuel_pdf_extractor
```

## Usage

### Global Command
Once installed, you can use the `cmut_process_pdf` command from anywhere:

```bash
cmut_process_pdf data/*.pdf --output results.csv --config config.yaml
```

### Using Just (Development)
If you have the source code and [just](https://github.com/casey/just) installed:

To process all PDFs in the `data/` directory using the labels defined in `config.yaml` (outputs to `transactions.csv`):

```bash
just run
```

To output in JSON format:

```bash
just run json
```

To clean up all generated files:

```bash
just clean
```

### Configuration

#### Account Mapping
You can map account numbers to custom labels by creating a `config.yaml` file. See `config.example.yaml` for a template.

```yaml
account_mapping:
  21945407: "Crequi"
  21945409: "Prevost"
```

> [!NOTE]
> Account numbers are matched as integers (leading zeros are ignored).

#### Description Mapping
You can automatically rename transactions by adding a `description_mapping` section. If any key is found as a **substring** (case-insensitive) in the transaction description, it will be replaced by the corresponding label.

```yaml
description_mapping:
  "VIR SEPA FROM": "Transfer"
  "NETFLIX": "Entertainment"
  "AMAZON": "Shopping"
```

#### Google Sheets Export
To enable Google Sheets export, add a `google_sheets` section to your `config.yaml`:

```yaml
google_sheets:
  spreadsheet_id: "your-spreadsheet-id"
  sheet_name: "Transactions"
  credentials_file: "credentials.json"
```

**Service Account Setup:**
1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable both **Google Sheets API** and **Google Drive API**.
3. Create a **Service Account** (APIs & Services > Credentials > Create Credentials > Service Account).
4. Create a **JSON Key** for that service account and download it.
5. Save the key as `credentials.json` (or any path specified in your `config.yaml`).
6. **Permission**: Share your Google Spreadsheet with the service account email (found in the JSON) with **Editor** access. (No broad IAM roles are needed if shared directly).

### Command Line Interface

You can explicitly specify files, the output format, and enable Google Sheets export:

```bash
uv run credit-mutuel-extractor data/*.pdf --output results.csv --config config.yaml
```
Or run it directly using `uvx`:

```bash
uvx --from credit-mutuel-pdf-extractor cmut_process_pdf data/*.pdf --output results.csv --config config.yaml --gsheet --include-source-file
```

**Requirements:**
- At least one input PDF file.
- The `--output` flag is mandatory and must end in `.csv` or `.json`.

## Technical Details

- **Account Identification**: Uses vertical Y-coordinate mapping to associate tables with the correct account number headers.
- **Data Normalization**: Amounts are cleaned and converted to standard floats.
- **Validation**: If `Starting Balance + Σ(Transactions) != Ending Balance`, the script will report a `CRITICAL` error and halt execution.
- **Modular Design**: Utility functions are separated into `utils.py` for maintainability.

## Security & Publishing

### Secret Leak Prevention
This project uses `pre-commit` and `detect-secrets` to prevent accidental commits of sensitive data.
Before committing, the hooks will scan for potential secrets.

### Publishing to PyPI
Publishing is automated via the `Justfile` and integrated with **1Password** for security.

1.  **Store your PyPI Token**: Create a "Login" or "Password" item in 1Password.
2.  **Add Environment Variable**: Add a field named `UV_PUBLISH_TOKEN` containing your PyPI API token.
3.  **Publish**:
    ```bash
    just publish
    ```
    This uses `op run` to securely inject the token into the `uv publish` command without it ever being stored in plain text or history.

### Encrypted Configuration
Keep your `config.yaml` and `secrets/credentials.json` synced across machines using 1Password:

1.  **Initial Setup**: Create the documents in your vault:
    ```bash
    just secrets-setup
    ```
2.  **Pull Changes**: On a new machine:
    ```bash
    just secrets-pull
    ```
3.  **Push Changes**: After updating your local config:
    ```bash
    just secrets-push
    ```

> [!NOTE]
> These commands use the titles `"CMut Config"` and `"CMut Google Credentials"`. You can change these in the `Justfile` if needed.
