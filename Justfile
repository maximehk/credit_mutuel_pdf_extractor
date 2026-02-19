list:
    just --list

# Run the extraction on all PDFs in the data directory
[group('run tool')]
run format="csv":
    uv run cmut_process_pdf data/*.pdf --config config.yaml --output transactions.{{format}}

# Run the extraction and export to Google Sheets
[group('run tool')]
gsheet:
    uv run cmut_process_pdf data/*.pdf --config config.yaml --gsheet

# Clean all generated files
[group('misc')]
clean:
    rm -f *.csv *.json *.txt

# Build the package
[group('packaging')]
build:
    uv build

# Publish to PyPI
[group('packaging')]
publish: build
    uv publish

# Install the script locally
[group('dev')]
install:
    uv tool install .

# Uninstall the script locally
[group('dev')]
uninstall:
    uv tool uninstall credit-mutuel-pdf-extractor

# Run pre-commit checks on all files
[group('dev')]
check:
    uv run pre-commit run --all-files

# Download secrets from 1Password
[group('secrets')]
secrets-pull:
    op document get "CMUT Config" --output config.yaml
    mkdir -p secrets
    op document get "CMUT Google Credentials" --output secrets/credentials.json

# Upload current secrets to 1Password (updates existing)
[group('secrets')]
secrets-push:
    op document edit "CMUT Config" config.yaml
    op document edit "CMUT Google Credentials" secrets/credentials.json

# Initial setup: create secret documents in 1Password
[group('secrets')]
secrets-setup:
    #!/bin/bash
    set -o pipefail

    if ! op item get "CMUT Config" > /dev/null 2>&1; then
      op document create config.yaml --title "CMUT Config"
    else
      echo "Error: An item with the name 'CMUT Config' already exists. Use 'just secrets-push' to update it."
    fi

    if ! op item get "CMUT Google Credentials" > /dev/null 2>&1; then
      op document create secrets/credentials.json --title "CMUT Google Credentials"
    else
      echo "Error: An item with the name 'CMUT Google Credentials' already exists. Use 'just secrets-push' to update it."
    fi
