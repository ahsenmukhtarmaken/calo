import os
import pandas as pd

def main():
    # Paths
    transactions_file = "transactions.csv"
    reports_dir = "reports"

    # Ensure reports directory exists & flush old files
    if os.path.exists(reports_dir):
        for f in os.listdir(reports_dir):
            os.remove(os.path.join(reports_dir, f))
    else:
        os.makedirs(reports_dir)

    # Load transactions
    df = pd.read_csv(transactions_file)

    # Ensure date is parsed properly
    if "date" not in df.columns:
        raise ValueError("transactions.csv must have a 'date' column (derived from sourcefile).")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Add time breakdown columns
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["week"] = df["date"].dt.isocalendar().week

    # Flag overdraft transactions
    df["Overdrawn"] = df["newBalance"] < 0
    df["Overdrawn"] = df["Overdrawn"].map({True: "Y", False: "N"})

    # --- 1. Full Overdrawn Transactions Report ---
    overdrawn_transactions = df[df["Overdrawn"] == "Y"].copy()
    overdrawn_transactions = overdrawn_transactions[
        [
            "sourcefile", "date", "id", "userId", "currency", "amount",
            "Overdrawn", "vat", "oldBalance", "newBalance",
            "type", "source", "action", "paymentBalance",
            "updatePaymentBalance", "metadata"
        ]
    ]
    overdrawn_transactions.rename(columns={"id": "transaction_id"}, inplace=True)
    overdrawn_transactions.to_csv(os.path.join(reports_dir, "overdrawn_transactions_report.csv"), index=False)

    # --- 2. Daily Overdrawn Report ---
    daily = (
        df[df["Overdrawn"] == "Y"]
        .groupby(["date", "userId"], as_index=False)["amount"]
        .sum()
    )
    daily.to_csv(os.path.join(reports_dir, "overdrawn_daily.csv"), index=False)

    # --- 3. Weekly Overdrawn Report ---
    weekly = (
        df[df["Overdrawn"] == "Y"]
        .groupby(["year", "month", "week", "userId"], as_index=False)["amount"]
        .sum()
    )
    weekly.to_csv(os.path.join(reports_dir, "overdrawn_weekly.csv"), index=False)

    # --- 4. Monthly Overdrawn Report ---
    monthly = (
        df[df["Overdrawn"] == "Y"]
        .groupby(["year", "month", "userId"], as_index=False)["amount"]
        .sum()
    )
    monthly.to_csv(os.path.join(reports_dir, "overdrawn_monthly.csv"), index=False)

    # --- 5. Yearly Overdrawn Report ---
    yearly = (
        df[df["Overdrawn"] == "Y"]
        .groupby(["year", "userId"], as_index=False)["amount"]
        .sum()
    )
    yearly.to_csv(os.path.join(reports_dir, "overdrawn_yearly.csv"), index=False)

    print("[OK] Reports generated in: /apps/", reports_dir)


if __name__ == "__main__":
    main()
