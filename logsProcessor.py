#!/usr/bin/env python3
"""
logsProcessor.py

Step 1: Recursively scan ./logs for .gz archives, extract each archive, find the inner raw log file
(often named '000000'), and move it into ./logs_extracted/<source_folder>__000000.log

Step 2: Clear ./logs_extracted before extraction to ensure fresh logs.

Step 3: Parse all extracted log files for "transaction: {...}" blocks and write them into
transactions.csv. Adds a new first column "sourcefile" while keeping all transaction fields.
"""

import os
import re
import tarfile
import gzip
import shutil
import tempfile
import csv
from pathlib import Path

# ------------------------------
# Helpers for extraction
# ------------------------------

def safe_extract_tar(tar: tarfile.TarFile, path: Path):
    """Safely extract tar archive into path, preventing path traversal."""
    for member in tar.getmembers():
        member_path = path.joinpath(member.name)
        if not str(member_path.resolve()).startswith(str(path.resolve())):
            raise Exception(f"Unsafe tar member path detected: {member.name}")
    tar.extractall(path=path)

def find_inner_log(root: Path, target_name: str = "000000"):
    """Find inner raw log file (default: '000000')."""
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname == target_name:
                return Path(dirpath) / fname
    return None

def process_gz(gz_path: Path, extracted_root: Path):
    """Extract gz/tar.gz and move final inner log to extracted_root."""
    source_folder = gz_path.parent.name or gz_path.parent.resolve().name
    extracted_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        try:
            if tarfile.is_tarfile(gz_path):
                with tarfile.open(gz_path, "r:*") as tar:
                    safe_extract_tar(tar, tmpdir_path)
            else:
                out_name = gz_path.stem
                out_path = tmpdir_path / out_name
                with gzip.open(gz_path, "rb") as gf, open(out_path, "wb") as out_f:
                    shutil.copyfileobj(gf, out_f)
        except Exception as e:
            print(f"[ERROR] Failed to extract {gz_path}: {e}")
            return

        inner = find_inner_log(tmpdir_path, target_name="000000")
        if inner is None:
            all_files = [p for p in tmpdir_path.rglob("*") if p.is_file()]
            if not all_files:
                print(f"[WARN] No files found inside archive {gz_path}")
                return
            inner = max(all_files, key=lambda p: p.stat().st_size)

        dest_filename = f"{source_folder}__{inner.name}.log"
        dest_path = extracted_root / dest_filename
        shutil.move(str(inner), str(dest_path))
        print(f"[OK] Extracted {gz_path} -> {dest_path}")

# ------------------------------
# Transaction parsing
# ------------------------------

TRANSACTION_RE = re.compile(
    r"transaction:\s*{([^}]*)}",
    re.DOTALL
)

FIELD_RE = re.compile(
    r"(\w+):\s*'?(.*?)'?(?:,|$)"
)

def parse_transactions_from_file(file_path: Path):
    """Parse transaction blocks from a log file and return list of dicts."""
    transactions = []
    text = file_path.read_text(errors="ignore")

    for match in TRANSACTION_RE.finditer(text):
        block = match.group(1)
        fields = dict(FIELD_RE.findall(block))
        # Normalize numeric fields
        for k, v in fields.items():
            if v.replace(".", "", 1).lstrip("-").isdigit():
                try:
                    if "." in v:
                        fields[k] = float(v)
                    else:
                        fields[k] = int(v)
                except Exception:
                    pass
        fields["sourcefile"] = file_path.name  # prepend sourcefile
        transactions.append(fields)

    return transactions

def write_transactions_to_csv(extracted_root: Path, csv_path: Path):
    """Flush old CSV, then parse all logs_extracted and write transactions.csv."""
    if csv_path.exists():
        csv_path.unlink()

    all_transactions = []
    for log_file in extracted_root.glob("*.log"):
        all_transactions.extend(parse_transactions_from_file(log_file))

    if not all_transactions:
        print("[INFO] No transactions found in extracted logs.")
        return

    # Collect all field names dynamically
    fieldnames = ["sourcefile"]
    for txn in all_transactions:
        for k in txn.keys():
            if k != "sourcefile" and k not in fieldnames:
                fieldnames.append(k)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_transactions)

    print(f"[OK] Wrote {len(all_transactions)} transactions to {csv_path}")

# ------------------------------
# Main workflow
# ------------------------------

def main():
    base_dir = Path(__file__).parent.resolve()
    logs_dir = base_dir / "logs"
    extracted_dir = base_dir / "logs_extracted"
    csv_file = base_dir / "transactions.csv"

    # Step 1: clear logs_extracted
    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)
    extracted_dir.mkdir(parents=True, exist_ok=True)

    # Step 2: extract logs
    if not logs_dir.exists():
        print(f"[ERROR] logs/ directory not found at {logs_dir}")
        return

    gz_files = list(logs_dir.rglob("*.gz"))
    if not gz_files:
        print("[INFO] No .gz files found under logs/ (nothing to extract).")
    else:
        print(f"[INFO] Found {len(gz_files)} .gz files. Extracting to {extracted_dir} ...")
        for gz in gz_files:
            process_gz(gz, extracted_dir)

    # Step 3: parse transactions and write CSV
    if csv_file.exists():
        csv_file.unlink()
    write_transactions_to_csv(extracted_dir, csv_file)

    print("[DONE] Processing complete.")

if __name__ == "__main__":
    main()
