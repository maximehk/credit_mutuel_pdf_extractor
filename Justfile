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
