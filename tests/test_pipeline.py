import os
import subprocess
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TRANSACTIONS_FILE = os.path.join(BASE_DIR, "transactions.csv")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

def run_script(script_name):
    """Run a Python script and raise if it fails."""
    result = subprocess.run(
        ["python", os.path.join(BASE_DIR, script_name)],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{script_name} failed!\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

def test_end_to_end_pipeline():
    # 1. Run logsProcessor.py → should generate transactions.csv
    run_script("logsProcessor.py")
    assert os.path.exists(TRANSACTIONS_FILE), "transactions.csv not generated"

    # 2. Run generate_overdrawn_reports.py → should generate reports
    run_script("generate_overdrawn_reports.py")

    # 3. Check that overdrawn reports exist + non-empty
    reports = {
        "overdrawn_transactions_report.csv": [
            "sourcefile","date","transaction_id","userId","currency","amount","Overdrawn",
            "vat","oldBalance","newBalance","type","source","action",
            "paymentBalance","updatePaymentBalance","metadata"
        ],
        "overdrawn_daily.csv": ["date","userId","amount"],
        "overdrawn_weekly.csv": ["year","month","week","userId","amount"],
        "overdrawn_monthly.csv": ["year","month","userId","amount"],
        "overdrawn_yearly.csv": ["year","userId","amount"],
    }

    for report, expected_cols in reports.items():
        path = os.path.join(REPORTS_DIR, report)
        assert os.path.exists(path), f"{report} missing"

        df = pd.read_csv(path)
        assert not df.empty, f"{report} is empty"
        assert list(df.columns) == expected_cols, f"{report} columns mismatch"

def test_overdrawn_flag_consistency():
    """Check that Overdrawn flag in overdrawn_transactions_report.csv matches newBalance < 0"""
    df = pd.read_csv(os.path.join(REPORTS_DIR, "overdrawn_transactions_report.csv"))
    for _, row in df.iterrows():
        expected_flag = "Y" if row["newBalance"] < 0 else "N"
        assert row["Overdrawn"] == expected_flag, f"Inconsistent Overdrawn flag for txn {row['transaction_id']}"

def test_errors_report():
    """Run generate_errors_report.py and check errors_report.csv exists + structure"""
    run_script("generate_errors_report.py")

    path = os.path.join(REPORTS_DIR, "errors_report.csv")
    assert os.path.exists(path), "errors_report.csv missing"

    df = pd.read_csv(path)
    assert not df.empty, "errors_report.csv is empty"

    expected_cols = ["sourceFile", "Date", "Errors"]
    assert list(df.columns) == expected_cols, "errors_report.csv columns mismatch"
