
list:
    just --list

# Run the extraction on all PDFs in the data directory
run format="csv":
    uv run main.py data/*.pdf --config config.yaml --output transactions.{{format}}

# Run the extraction and export to Google Sheets
gsheet format="csv":
    uv run main.py data/*.pdf --config config.yaml --gsheet --output transactions.{{format}}

# Clean all generated files
clean:
    rm -f *.csv *.json *.txt
