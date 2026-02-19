import re
import pandas as pd

def parse_amount(amount_str):
    if not amount_str or pd.isna(amount_str):
        return 0.0
    # Clean up French number formatting:
    # 1. Remove thousands separator (dots)
    # 2. Replace decimal separator (comma) with dot
    # Example: "1.234,56" -> "1234.56"
    clean = str(amount_str).replace('.', '').replace(' ', '').replace(',', '.')
    try:
        return float(clean)
    except ValueError:
        return 0.0

def find_account_headers(page):
    headers = []
    # Use regex to find account numbers and their positions
    text = page.extract_text()
    if not text:
        return []

    # We'll use extract_words to get coordinates
    words = page.extract_words()
    # Pattern for account numbers: 11 digits or digits with dots
    acc_pattern = re.compile(r'\d{9,11}(\.\.\.)?')

    for i, word in enumerate(words):
        if acc_pattern.search(word['text']):
            # Check if preceded by "N°" or "Nº"
            if i > 0 and 'N' in words[i-1]['text'].upper():
                headers.append({
                    "account": word['text'].replace('...', ''),
                    "top": word['top']
                })
    return sorted(headers, key=lambda x: x['top'])

def format_date(date_str):
    """
    Standardize date format to YYYY-MM-DD.
    Assumes input format DD/MM/YYYY or similar.
    """
    if not date_str or not isinstance(date_str, str):
        return date_str

    # Try to find DD/MM/YYYY or DD/MM/YY
    match = re.search(r'(\d{2})/(\d{2})/(\d{2,4})', date_str)
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = "20" + year # Assume 20xx
        return f"{year}-{month}-{day}"

    return date_str
