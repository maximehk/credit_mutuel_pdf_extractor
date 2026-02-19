import gspread
import pdfplumber
import pandas as pd
import os
import logging
import yaml
import gspread
import argparse
from .utils import parse_amount, find_account_headers, format_date

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Extract bank transactions from Crédit Mutuel PDF statements.')

    parser.add_argument('files', nargs='+', help='PDF files to process')
    parser.add_argument('-o', '--output', help='Output filename (must end in .csv or .json)')
    parser.add_argument('-c', '--config', help='Path to YAML config file for account mapping')
    parser.add_argument('--gsheet', action='store_true', help='Export to Google Spreadsheet (requires google_sheets config)')
    parser.add_argument('--include-source-file', action='store_true', help='Include the SourceFile column in the output')
    args = parser.parse_args()
    
    # Early validation of output format and requirement
    if not args.output and not args.gsheet:
        parser.error("The following arguments are required: -o/--output (unless --gsheet is used)")
        
    if args.output:
        if not (args.output.endswith('.csv') or args.output.endswith('.json')):
            parser.error(f"Output file must end in .csv or .json (got: {args.output})")

    account_mapping = {}
    description_mapping = {}
    gsheet_config = None
    if args.config:
        if not os.path.exists(args.config):
            logger.error(f"Config file not found: {args.config}")
            import sys
            sys.exit(1)
        with open(args.config, 'r') as f:
            config_data = yaml.safe_load(f)
            if config_data:
                if 'account_mapping' in config_data:
                    # Store as int keys for easier matching
                    account_mapping = {int(k): v for k, v in config_data['account_mapping'].items()}
                    logger.info(f"Loaded {len(account_mapping)} account mappings from {args.config}")
                
                if 'description_mapping' in config_data:
                    description_mapping = config_data['description_mapping']
                    logger.info(f"Loaded {len(description_mapping)} description mappings from {args.config}")
                
                if 'google_sheets' in config_data:
                    gsheet_config = config_data['google_sheets']

    pdf_files = args.files
        
    all_transactions = []
    
    for pdf_file in pdf_files:
        if not os.path.exists(pdf_file):
            logger.error(f"File not found: {pdf_file}")
            continue
            
        basename = os.path.basename(pdf_file)
        logger.info(f"Processing {basename}...")
        
        # Track data per account for this specific PDF file
        # account_data = { "acc_id": { "tx_total": 0.0, "balances": [], "tx_list": [] } }
        account_validation = {}
        
        try:
            with pdfplumber.open(pdf_file) as pdf:
                # Use a stateful current_account that persists across pages
                current_account = "Unknown"
                
                for page in pdf.pages:
                    headers = find_account_headers(page)
                    # Use find_tables to get geometry
                    table_objs = page.find_tables()
                    
                    # Sort tables by vertical position
                    table_objs = sorted(table_objs, key=lambda t: t.bbox[1])
                    
                    for t_obj in table_objs:
                        # Find the last header above this table
                        applicable_header = None
                        for h in headers:
                            if h['top'] < t_obj.bbox[1]:
                                applicable_header = h
                            else:
                                break
                        
                        if applicable_header:
                            new_acc = applicable_header['account']
                            if new_acc != current_account:
                                current_account = new_acc
                        
                        # Apply mapping if available
                        display_account = current_account
                        try:
                            acc_int = int(current_account.lstrip('0'))
                            if acc_int in account_mapping:
                                display_account = account_mapping[acc_int]
                        except (ValueError, TypeError):
                            pass

                        if current_account not in account_validation:
                            account_validation[current_account] = {"tx_total": 0.0, "balances": [], "tx_list": []}

                        table_data = t_obj.extract()
                        if not table_data: continue
                        
                        header_row = [str(h).replace('\n', ' ').strip() for h in table_data[0] if h is not None]
                        
                        try:
                            if not any('Date' in h for h in header_row): continue
                            if not any('Débit' in h for h in header_row) and not any('Crédit' in h for h in header_row):
                                continue

                            date_idx = next(i for i, h in enumerate(header_row) if 'Date' in h)
                            debit_idx = next((i for i, h in enumerate(header_row) if 'Débit' in h), -1)
                            credit_idx = next((i for i, h in enumerate(header_row) if 'Crédit' in h), -1)
                            desc_idx = next((i for i, h in enumerate(header_row) if 'Opération' in h or 'Libellé' in h), 2)
                        except StopIteration:
                            continue

                        for row in table_data[1:]:
                            if len(row) != len(header_row): continue
                            date_str = row[date_idx]
                            if not date_str: continue
                            
                            is_balance = 'SOLDE' in str(date_str).upper()
                            
                            amount = 0.0
                            if debit_idx != -1 and row[debit_idx]:
                                amount -= parse_amount(row[debit_idx])
                            if credit_idx != -1 and row[credit_idx]:
                                amount += parse_amount(row[credit_idx])
                                
                            if is_balance:
                                account_validation[current_account]["balances"].append({
                                    "amount": amount,
                                    "label": str(date_str).strip()
                                })
                                continue
                            
                            if 'RÉF' in str(date_str).upper() or 'TOTAL' in str(date_str).upper():
                                continue
                                
                            if amount == 0.0: continue

                            desc = str(row[desc_idx]).replace('\n', ' ').strip() if desc_idx < len(row) else ""
                            
                            # Apply description mapping (Simple String)
                            final_desc = desc
                            for pattern, label in description_mapping.items():
                                if pattern.upper() in desc.upper():
                                    final_desc = label
                                    break

                            tx = {
                                "Account": display_account,
                                "Date": format_date(date_str),
                                "Description": desc,
                                "Comment": final_desc if final_desc != desc else "",
                                "Amount": round(amount, 2),
                            }
                            if args.include_source_file:
                                tx["SourceFile"] = basename
                            
                            all_transactions.append(tx)
                            account_validation[current_account]["tx_total"] += amount

        except Exception as e:
            logger.error(f"Error reading {pdf_file}: {e}")
            continue

        # Validate accounts for this PDF
        for acc, data in account_validation.items():
            if acc == "Unknown": continue
            balances = data["balances"]
            if len(balances) < 2: continue
            
            # Use the first and last balance found for this account in this PDF
            start_bal = balances[0]["amount"]
            end_bal = balances[-1]["amount"]
            tx_sum = data["tx_total"]
            
            if abs((start_bal + tx_sum) - end_bal) > 0.01:
                logger.critical(f"Balance validation failed for account {acc} in {basename}")
                logger.critical(f"  Starting Balance: {start_bal:>10.2f} ({balances[0]['label']})")
                logger.critical(f"  Sum of Transactions: {tx_sum:>10.2f}")
                logger.critical(f"  Expected Ending: {start_bal + tx_sum:>10.2f}")
                logger.critical(f"  Actual Ending:   {end_bal:>10.2f} ({balances[-1]['label']})")
                logger.critical(f"  Difference:      {(start_bal + tx_sum) - end_bal:>10.2f}")
                import sys
                sys.exit(1)
            else:
                logger.info(f"  ✓ Account {acc} validated.")

    # Export results
    if all_transactions:
        df = pd.DataFrame(all_transactions)
        
        # Sort by Date and Account
        if 'Date' in df.columns:
            df = df.sort_values(by=['Date', 'Account'], ascending=[False, True])
            
        logger.info(f"Total extracted transactions: {len(df)}")
        
        outputs = []
        if args.output:
            if args.output.endswith('.json'):
                outputs.append(('json', args.output))
            else:
                outputs.append(('csv', args.output))
        elif not args.gsheet:
            # Default to both if no output and no gsheet specified
            outputs = [('json', 'transactions.json'), ('csv', 'transactions.csv')]

        for fmt, path in outputs:
            if fmt == 'json':
                df.to_json(path, orient="records", indent=2, force_ascii=False)
                logger.info(f"Saved {path}")
            elif fmt == 'csv':
                df.to_csv(path, index=False)
                logger.info(f"Saved {path}")
        
        if args.gsheet:
            if not gsheet_config:
                logger.error("Google Sheets configuration not found in config file.")
                import sys
                sys.exit(1)
            export_to_gsheet(df, gsheet_config)
    else:
        logger.warning("No transactions found.")

def export_to_gsheet(df, config):
    """
    Export the DataFrame to a Google Spreadsheet.
    """
    try:
        creds_file = config.get('credentials_file', 'credentials.json')
        spreadsheet_id = config.get('spreadsheet_id')
        sheet_name = config.get('sheet_name', 'Transactions')

        if not spreadsheet_id:
            logger.error("spreadsheet_id missing in google_sheets config.")
            return

        logger.info(f"Exporting to Google Spreadsheet {spreadsheet_id}...")
        
        gc = gspread.service_account(filename=creds_file)
        sh = gc.open_by_key(spreadsheet_id)
        
        try:
            worksheet = sh.worksheet(sheet_name)
            # Read existing data
            existing_data = worksheet.get_all_records()
            df_existing = pd.DataFrame(existing_data)
            logger.info(f"Read {len(df_existing)} existing transactions from '{sheet_name}'.")
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Sheet '{sheet_name}' not found, creating it.")
            worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="10")
            df_existing = pd.DataFrame()

        # Merge and deduplicate
        if not df_existing.empty:
            # Ensure columns match for merging
            # If the sheet was empty or has different columns, we might need to be careful
            # But here we assume the schema is consistent
            df_combined = pd.concat([df_existing, df], ignore_index=True)
        else:
            df_combined = df

        # Deduplicate based on core fields
        initial_count = len(df_combined)
        # We use a subset of columns that define a unique transaction
        # SourceFile is excluded as the same transaction might appear in different files (e.g. overlap in statements)
        dedup_cols = ['Account', 'Date', 'Description', 'Amount']
        # keep='last' ensures that if the same transaction exists in the sheet and new data,
        # the new data (with updated comments/mappings) replaces the old one.
        df_combined = df_combined.drop_duplicates(subset=dedup_cols, keep='last')
        
        # Always sort final combined data by Date and Account
        if 'Date' in df_combined.columns:
            df_combined = df_combined.sort_values(by=['Date', 'Account'], ascending=[True , True])

        final_count = len(df_combined)
        logger.info(f"Merged and deduplicated: {initial_count} -> {final_count} transactions.")

        # Clear existing data
        worksheet.clear()
        
        # Prepare data (headers + rows)
        df_filled = df_combined.fillna('')
        data = [df_filled.columns.values.tolist()] + df_filled.values.tolist()
        
        # Batch update (using values=data to avoid DeprecationWarning)
        worksheet.update(values=data, range_name='A1')
        logger.info(f"✓ Successfully exported {final_count} transactions to Google Sheet '{sheet_name}'.")

    except Exception as e:
        logger.error(f"Failed to export to Google Sheets: {e}")

if __name__ == "__main__":
    main()
