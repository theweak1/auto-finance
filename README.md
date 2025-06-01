# Auto Finance Processor

This script automates the classification and uploading of bank transaction CSVs into a structured Google Sheets document, categorized by month and custom rules.

---

## 📊 Overview

The tool processes monthly bank statements in CSV format (e.g., `BANK_January.csv`), applies categorization rules defined in `config.json`, and uploads the transactions to your Google Sheet—one worksheet per month.

It also:

- Prevents reprocessing previously handled files via `processed_files.json`
- Automatically updates yearly summaries
- Archives processed files into a `Completed/<year>` folder
- Categorizes transactions based on custom rules using name, amount, and category conditions

---

## ⚙️ Requirements

- Python 3.6+
- Google Service Account JSON (`service_account.json`)
- A Google Sheet named **"Personal Finances"** with:

  - Tabs for each month (e.g., "January", "February", ...)
  - A tab named `SUMMARY`
  - A tab named `YEARLY SUMMARY`

- `config.json` file for categorization rules

---

## 🚀 Setup

### 1. Clone the Repository

```bash
git clone https://github.com/theweak1/auto-finance.git
cd auto-finance
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

- gspread — to access the Google Sheets API

- tqdm — for progress bars during transaction upload

### 3. 📂 Expected Files

- Save your **Google Sheets API credentials** as `service_account.json` in the root folder.
- `BANK_<Month>.csv` — monthly CSV files to process
- `config.json` — contains transaction categorization rules and ignored files
- `processed_files.json` — automatically generated log of processed files

---

## 📚 Configuration: `config.json`

The `config.json` defines how transactions should be categorized. Example template:

```json
{
	"CATEGORIZATION_RULES": [
		{
			"match": {
				"name_contains": ["EXAMPLE_KEYWORD"],
				"category_equals": ["SomeCategory"]
			},
			"match_any": true,
			"category": "*CUSTOM_CATEGORY*"
		},
		{
			"match": {
				"name_contains": ["example keyword"],
				"amount_equals": 100.0
			},
			"category": "*EXAMPLE CATEGORY*"
		}
	],

	"IGNORE_FILES": [
		"service_account.json",
		"config.json",
		"financeManager.py",
		"Completed",
		"processed_files.json"
	]
}
```

> Transactions are matched using substring matching on name, category, and/or amount. `match_any` allows partial rule matches.

---

## 🚩 Important Notes

- **Prefix**: The script expects CSV files to start with `BANK_`. You can change this string inside the `is_valid_file()` function in `financeManager.py`.
- **Monthly Files**: Each file must be named like `BANK_January.csv`, `BANK_February.csv`, etc.
- **Header**: CSV files must have at least 4 columns: `date`, `name`, `category`, `amount`.
- **Google Sheets Layout**:

  - Rows start at line 7 in each monthly sheet
  - Summary totals for the year are pulled from `SUMMARY` and placed into `YEARLY SUMMARY`
  - The yearly summary is updated with totals pulled from cell A19 in the SUMMARY sheet.

---

## ▶️ Running the Script

```bash
python financeManager.py
```

- Logs will be printed to the console and saved to `financeManager.log`
- Parses eligible files
- Categorizes each transaction
- Uploads them to the appropriate Google Sheet tab
- Updates yearly summary (on January uploads)
- Processed files will be archived in `Completed/<year>/Entered_<original_filename>`

---

## 🚀 Future Improvements (Ideas)

- Add CLI arguments for dry runs, specific months, or preview mode
- Support different banks or prefixes (currently expects `BANK_`)
- Add summary report generation

---

## 🔒 Security

Your config.json and service_account.json files are listed in .gitignore to avoid accidental exposure.

---

## 🌟 Credits

Developed to automate personal finance tracking using Google Sheets and Python. Contributions and suggestions are welcome!
