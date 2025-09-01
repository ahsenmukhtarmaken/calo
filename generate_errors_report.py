import os
import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOGS_EXTRACTED_DIR = BASE_DIR / "logs_extracted"
REPORTS_DIR = BASE_DIR / "reports"
REPORT_FILE = REPORTS_DIR / "errors_report.csv"

# Regex to match timestamp at beginning of log line
TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

def extract_errors():
    rows = []

    for log_file in LOGS_EXTRACTED_DIR.glob("**/*"):
        if log_file.is_file():
            with log_file.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "ERROR" in line or "Error" in line:
                        # Extract timestamp
                        match = TIMESTAMP_PATTERN.match(line)
                        date = match.group(0) if match else ""
                        rows.append([log_file.name, date, line.strip()])

    return rows

def write_csv(rows):
    REPORTS_DIR.mkdir(exist_ok=True)

    # Overwrite if exists
    with REPORT_FILE.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["sourceFile", "Date", "Errors"])
        writer.writerows(rows)

def main():
    errors = extract_errors()
    write_csv(errors)
    print(f"[OK] Error report generated: {REPORT_FILE}")

if __name__ == "__main__":
    main()
