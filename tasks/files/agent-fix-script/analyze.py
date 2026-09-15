"""Bangladesh-India bilateral merchandise trade balance, millions USD.

data.csv holds values in THOUSANDS of USD. Balance = exports - imports,
converted to millions USD, written to RESULT.txt.
"""
import csv

with open("data.csv") as f:
    rows = list(csv.DictReader(f))

row = rows[0]
exports = float(row["exports"])
imports = float(row["imports_kusd"])
balance_musd = (exports - imports) / 1_000_000

with open("RESULT.txt", "w") as f:
    f.write(f"{balance_musd:.3f}\n")

print("wrote RESULT.txt:", balance_musd)
