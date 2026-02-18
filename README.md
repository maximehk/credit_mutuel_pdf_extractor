# Crédit Mutuel PDF Extractor

A robust Python utility to extract transaction data from Crédit Mutuel bank statement PDFs, validate data integrity, and export to structured formats (JSON/CSV).

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

Ensure you have [uv](https://github.com/astral-sh/uv) installed.

```bash
uv sync
```

## Usage

### Using Just (Recommended)

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
uv run main.py data/*.pdf --output results.csv --config config.yaml --gsheet
```

**Requirements:**
- At least one input PDF file.
- The `--output` flag is mandatory and must end in `.csv` or `.json`.

## Technical Details

- **Account Identification**: Uses vertical Y-coordinate mapping to associate tables with the correct account number headers.
- **Data Normalization**: Amounts are cleaned and converted to standard floats.
- **Validation**: If `Starting Balance + Σ(Transactions) != Ending Balance`, the script will report a `CRITICAL` error and halt execution.
- **Modular Design**: Utility functions are separated into `utils.py` for maintainability.
