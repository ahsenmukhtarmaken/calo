#!/usr/bin/env python3
"""
logsProcessor.py (updated)

Now also adds a 'date' column to transactions.csv, derived from the 'sourcefile' prefix.
"""

import os
import tarfile
import gzip
import shutil
import tempfile
import csv
from pathlib import Path
import re

# ------------------------------
# Helpers for extraction
# ------------------------------

def safe_extract_tar(tar: tarfile.TarFile, path: Path):
    for member in tar.getmembers():
        member_path = path.joinpath(member.name)
        if not str(member_path.resolve()).startswith(str(path.resolve())):
            raise Exception(f"Unsafe tar member path detected: {member.name}")
    tar.extractall(path=path)

def find_inner_log(root: Path, target_name: str = "000000"):
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname == target_name:
                return Path(dirpath) / fname
    return None

def process_gz(gz_path: Path, extracted_root: Path):
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
# Transaction parsing (brace-aware)
# ------------------------------

def _extract_transaction_blocks(text: str):
    blocks = []
    i = 0
    while True:
        start = text.find("transaction:", i)
        if start == -1:
            break
        brace_start = text.find("{", start)
        if brace_start == -1:
            break

        depth = 0
        in_sq = False
        in_dq = False
        esc = False

        for j in range(brace_start, len(text)):
            ch = text[j]
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if not in_dq and ch == "'" :
                in_sq = not in_sq
            elif not in_sq and ch == '"':
                in_dq = not in_dq
            elif not in_sq and not in_dq:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        blocks.append(text[brace_start + 1 : j])
                        i = j + 1
                        break
        else:
            break
    return blocks

def _coerce_value(s: str):
    val = s.strip()
    if val.endswith(","):
        val = val[:-1].rstrip()
    if (len(val) >= 2) and ((val[0] == val[-1]) and val[0] in ("'", '"')):
        val = val[1:-1]
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val

def _parse_block_to_dict(block_text: str):
    out = {}
    for raw in block_text.splitlines():
        line = raw.strip()
        if not line or line in ("{", "}", "},"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = _coerce_value(val)
        out[key] = val
    return out

def _extract_date_from_sourcefile(sourcefile: str) -> str:
    """
    Extract date prefix (YYYY-MM-DD) from sourcefile if present.
    Example: '2025-08-30__000000.log' -> '2025-08-30'
    """
    match = re.match(r"(\d{4}-\d{2}-\d{2})", sourcefile)
    return match.group(1) if match else ""

def parse_transactions_from_file(file_path: Path):
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        text = file_path.read_text(errors="ignore")

    blocks = _extract_transaction_blocks(text)
    txns = []
    for b in blocks:
        d = _parse_block_to_dict(b)
        if d:
            d["sourcefile"] = file_path.name
            d["date"] = _extract_date_from_sourcefile(file_path.name)  # NEW COLUMN
            txns.append(d)
    return txns

def write_transactions_to_csv(extracted_root: Path, csv_path: Path):
    if csv_path.exists():
        csv_path.unlink()

    all_transactions = []
    for log_file in sorted(extracted_root.glob("*.log")):
        all_transactions.extend(parse_transactions_from_file(log_file))

    if not all_transactions:
        print("[INFO] No transactions found in extracted logs.")
        return

    preferred = [
        "date","sourcefile","id","userId","currency","amount","vat",
        "oldBalance","newBalance","type","source","action",
        "paymentBalance","updatePaymentBalance","metadata"
    ]
    keys = set().union(*(t.keys() for t in all_transactions))
    ordered = [c for c in preferred if c in keys] + sorted(k for k in keys if k not in preferred)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, extrasaction="ignore")
        writer.writeheader()
        for row in all_transactions:
            writer.writerow(row)

    print(f"[OK] Wrote {len(all_transactions)} transactions to {csv_path}")

# ------------------------------
# Main workflow
# ------------------------------

def main():
    base_dir = Path(__file__).parent.resolve()
    logs_dir = base_dir / "logs"
    extracted_dir = base_dir / "logs_extracted"
    csv_file = base_dir / "transactions.csv"

    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)
    extracted_dir.mkdir(parents=True, exist_ok=True)

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

    if csv_file.exists():
        csv_file.unlink()
    write_transactions_to_csv(extracted_dir, csv_file)

    print("[DONE] Processing complete, transactions.csv and logs_extracted folder generated.")

if __name__ == "__main__":
    main()
