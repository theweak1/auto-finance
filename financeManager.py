#!/usr/bin/env python3

# Import required modules
import csv
import gspread  # For Google Sheets API
import time
import shutil
import os
import json
import calendar
import logging
from datetime import date
from tqdm import tqdm  # Progress bar

# Configure logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("financeManager.log"), logging.StreamHandler()],
)

# Get current year and current working directory
current_year = date.today().year
source = os.getcwd()
PROCESSED_LOG = "processed_files.json"  # File to track processed CSVs

# Load configuration from JSON file
config = {}
try:
    with open("config.json", "r") as config_file:
        config = json.load(config_file)
except json.JSONDecodeError as e:
    logging.error(f"Error loading config.json: {e}")
    exit(1)
except FileNotFoundError as e:
    logging.error(f"{e}")

# Load categorization rules and ignored files from config
CATEGORIZATION_RULES = config.get("CATEGORIZATION_RULES", [])
IGNOREFILES = set(config.get("IGNORE_FILES", []))


def load_processed_files(next_filename=None):
    """
    Load the set of processed filenames from a JSON log.
    If all months have been processed and the next file is January, reset the log.
    """
    months = set(
        calendar.month_name[1:]
    )  # Set of month names (no empty string at index 0)

    if os.path.exists(PROCESSED_LOG):
        with open(PROCESSED_LOG) as f:
            processed = set(json.load(f))

        # Extract the month from each processed filename
        processed_months = {
            name.split("_")[1].split(".")[0].lower()
            for name in processed
            if name.startswith("BANK_")
        }

        # Reset the log if all months have been processed and next file is January
        if (
            processed_months == {m.lower() for m in months}
            and next_filename
            and next_filename.lower().startswith("BANK_january")
        ):
            logging.info(
                "ðŸ”„ All months processed. Starting new year. Resetting processed log."
            )
            processed.clear()
            with open(PROCESSED_LOG, "w") as f:
                json.dump([], f)

        return processed

    return set()


def save_processed_file(filename):
    """Add a filename to the processed log."""
    processed = load_processed_files()
    processed.add(filename)
    with open(PROCESSED_LOG, "w") as f:
        json.dump(list(processed), f)


def categorize_transaction(name, category, rules, amount=None):
    """
    Match a transaction against the categorization rules.
    Returns a custom category if a rule matches; otherwise returns the original category.
    """
    name = name.strip().lower()
    category = category.strip().lower()
    amnt = amount

    for rule in rules:
        match = rule.get("match", {})
        match_any = rule.get("match_any", False)

        # Normalize rule match values
        name_subs = [sub.strip().lower() for sub in match.get("name_contains", [])]
        cat_equals = [c.strip().lower() for c in match.get("category_equals", [])]
        amt_equals = match.get("amount_equals",[])

        # Compute individual matches
        name_match = any(sub in name for sub in name_subs) if name_subs else None
        cat_match = category in cat_equals if cat_equals else None

        if amt_equals:
            if amnt is None:
                amt_match = False
            else:
                try:
                    amt_match = any(float(a) == float(amnt) for a in amt_equals)
                except (typeError, ValueError):
                    amt_match = False
        else:
            amt_match = None
       
        if match_any:
            if any(m is True for m in [name_match, cat_match, amt_match]):
                return rule["category"]
        else:
            if (
                (name_match is not False)
                and (cat_match is not False)
                and (amt_match is not False)
            ):
                return rule["category"]

    return category  # Fallback to original category


def process_bank_file(file_path):
    """
    Read the bank CSV file, categorize each transaction, and return them as a list.
    """
    transactions = []
    try:
        with open(file_path, mode="r", newline="") as csv_file:
            csv_reader = csv.reader(csv_file)
            next(csv_reader, None)  # Skip header

            # Parse each row: (date, name, category, amount)
            transactions = [
                (
                    row[0],  # Date
                    row[1],  # Name
                    categorize_transaction(
                        row[1], row[2], CATEGORIZATION_RULES, float(row[3])
                    ),  # Updated category
                    float(row[3]),  # Amount
                )
                for row in csv_reader
                if len(row) >= 4
            ]
    except Exception as e:
        logging.error(f"Error processing bank file {file_path}: {e}", exc_info=True)
        raise
    return transactions


def is_valid_file(filename):
    """
    Check if the file follows the expected naming format (e.g., BANK_january.csv).
    """
    if not filename.startswith("BP_"):
        return False, None
    try:
        month_name = filename.split("_")[1].split(".")[0].lower()
        valid = month_name in {m.lower() for m in calendar.month_name[1:]}
        return valid, month_name if valid else None
    except IndexError:
        return False, None


def delete_previous_entry(worksheet, month):
    """
    Delete previous entries starting from row 7 in the given worksheet.
    """
    logging.info(f"Deleting previous entry for worksheet {month}...")
    while worksheet.acell("A7").value is not None:
        worksheet.delete_rows(7)
        time.sleep(2)
    logging.info(f"Finished deleting previous entry for worksheet {month}...")


def update_yearly_summary(sheet, year):
    """
    Copy total from 'SUMMARY' and insert it into the 'YEARLY SUMMARY' sheet.
    """
    logging.info("Updating yearly summary...")
    wks = sheet.worksheet("SUMMARY")
    year_Total = wks.acell("A19").value
    wks = sheet.worksheet("YEARLY SUMMARY")
    wks.insert_rows([[year - 1, str(year_Total)]], 6)
    logging.info("Finished updating yearly summary...")


def handle_file(file_path, filename, month_name, year):
    """
    Process, upload, and archive a single bank file.
    """
    destination = os.path.join(source, "Completed", str(year))
    new_destination = os.path.join(destination, f"Entered_{filename}")

    transactions = process_bank_file(file_path)

    sa = gspread.service_account(filename="./service_account.json")
    sh = sa.open("Personal Finances")
    wks = sh.worksheet(month_name)

    # Update yearly summary only on January
    if month_name == "january":
        update_yearly_summary(sh, current_year)

    # Delete old data if present
    if wks.acell("A7").value is not None:
        delete_previous_entry(wks, month_name)

    # Upload data to Google Sheet
    logging.info(f"Uploading {len(transactions)} transactions to {month_name}...")
    for i, row in enumerate(
        tqdm(transactions, desc=f"Uploading to {month_name}", unit="txn")
    ):
        wks.insert_row(list(row), 7)
        if i % 5 == 0:
            time.sleep(10)  # Prevent quota issues or request overload

    # Archive the file
    logging.info(f"Finished... moving {filename} to {new_destination}")
    os.makedirs(destination, exist_ok=True)
    shutil.move(file_path, new_destination)
    save_processed_file(filename)


def main():
    """
    Main driver function to scan for files, validate them, process new ones, and log progress.
    """
    processed_files = load_processed_files(next_filename=None)
    any_processed = False

    files = [
        f
        for f in os.listdir(source)
        if os.path.isfile(os.path.join(source, f)) and f not in IGNOREFILES
    ]
    if not files:
        logging.info("No candidate files found in the directory.")

    for filename in files:
        file_path = os.path.join(source, filename)

        valid, month_name = is_valid_file(filename)
        if not valid:
            logging.warning(f"Skipping {filename}: Invalid format")
            continue

        processed_files = load_processed_files(next_filename=filename)

        if filename in processed_files:
            logging.info(f"Skipping {filename}: Already processed")
            continue

        year = current_year - 1 if month_name == "december" else current_year

        try:
            handle_file(file_path, filename, month_name, year)
            any_processed = True
        except Exception as e:
            logging.error(f"Error processing {filename}: {e}", exc_info=True)

    if not any_processed:
        logging.info("No valid file was processed.")


# Run the script
if __name__ == "__main__":
    main()