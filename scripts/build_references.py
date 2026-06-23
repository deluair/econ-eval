"""Recompute the quantitative-track reference values from TradeWeave parquet.

Run: uv run --with duckdb python scripts/build_references.py
Every number printed here is the ground truth a quantitative task grades
against. Source of truth: ~/tradeweave/data/parquet (BACI-derived, thousands
USD). Re-run after any data refresh and re-verify before editing task yamls.
"""
from __future__ import annotations

import os

import duckdb

P = os.path.expanduser("~/tradeweave/data/parquet")
TOTALS = f"{P}/country_year_totals.parquet"
CYP = f"{P}/country_year_product/**/*.parquet"
con = duckdb.connect()


def scalar(sql: str) -> float:
    return con.execute(sql).fetchone()[0]


def main() -> None:
    bgd_exp = scalar(f"SELECT total_exports FROM '{TOTALS}' WHERE country_code=50 AND year=2022")
    bgd_imp = scalar(f"SELECT total_imports FROM '{TOTALS}' WHERE country_code=50 AND year=2022")
    cotton = scalar(f"SELECT export_value FROM read_parquet('{CYP}') WHERE country_code=50 AND year=2022 AND product_code='610910'")
    other = scalar(f"SELECT export_value FROM read_parquet('{CYP}') WHERE country_code=50 AND year=2022 AND product_code='610990'")
    hs6109 = cotton + other
    balance = bgd_exp - bgd_imp
    cotton_share = cotton / hs6109 * 100

    print("Bangladesh 2022, thousands USD (BACI / TradeWeave parquet):")
    print(f"  HS 610910 cotton T-shirts exports : {cotton:,.3f}")
    print(f"  HS 610990 other T-shirts exports  : {other:,.3f}")
    print(f"  HS 6109 heading total (sum)       : {hs6109:,.3f}   <- task quant-hs6109-sum")
    print(f"  total exports                     : {bgd_exp:,.3f}")
    print(f"  total imports                     : {bgd_imp:,.3f}")
    print(f"  trade balance (exp - imp)         : {balance:,.3f}   <- task quant-trade-balance")
    print(f"  cotton share of HS 6109 (%)       : {cotton_share:,.4f}   <- task quant-cotton-share")


if __name__ == "__main__":
    main()
