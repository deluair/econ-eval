"""Reference values for the 2026-09-15 "daily work" tasks, from the same parquet the
platforms serve. Run: uv run --no-project --with duckdb python scripts/build_references_daily.py
Every number printed here is copied into a task yaml prompt or reference; re-run
after a data refresh and re-verify before editing the yamls.
"""
from __future__ import annotations

import math
import os

import duckdb

P = os.path.expanduser("~/tradeweave/data/parquet")
F = os.path.expanduser("~/finobservatory/data/parquet")
TOTALS = f"{P}/country_year_totals.parquet"
CYP = f"{P}/country_year_product/**/*.parquet"
BIL = f"{P}/bilateral_product/**/*.parquet"
MFN = f"{P}/applied_mfn_hs6.parquet"
BGD, IND = 50, 699
con = duckdb.connect()


def q(sql: str):
    return con.execute(sql).fetchall()


def scalar(sql: str) -> float:
    return q(sql)[0][0]


def trade() -> None:
    print("== TradeWeave parquet (BACI, thousands USD) ==")
    e13 = scalar(f"SELECT total_exports FROM '{TOTALS}' WHERE country_code={BGD} AND year=2013")
    e22 = scalar(f"SELECT total_exports FROM '{TOTALS}' WHERE country_code={BGD} AND year=2022")
    e23 = scalar(f"SELECT total_exports FROM '{TOTALS}' WHERE country_code={BGD} AND year=2023")
    cagr = (e23 / e13) ** (1 / 10) - 1
    print(f"BGD exports 2013 {e13:,.3f}  2022 {e22:,.3f}  2023 {e23:,.3f}")
    print(f"  CAGR 2013-2023 (%): {cagr*100:.4f}   <- quant-cagr-decade")
    print(f"  growth 2022-2023 (%): {(e23/e22-1)*100:.4f}   <- quant-growth-year")
    rmg13 = scalar(f"SELECT sum(export_value) FROM read_parquet('{CYP}') WHERE country_code={BGD} AND year=2013 AND (product_code LIKE '61%' OR product_code LIKE '62%')")
    rmg23 = scalar(f"SELECT sum(export_value) FROM read_parquet('{CYP}') WHERE country_code={BGD} AND year=2023 AND (product_code LIKE '61%' OR product_code LIKE '62%')")
    s13, s23 = rmg13 / e13 * 100, rmg23 / e23 * 100
    print(f"RMG (HS61+62) exports 2013 {rmg13:,.3f} share {s13:.4f}%; 2023 {rmg23:,.3f} share {s23:.4f}%")
    print(f"  share change (pp): {s23-s13:+.4f}   <- quant-rmg-share-change")
    x = scalar(f"SELECT sum(value_kusd) FROM read_parquet('{BIL}') WHERE exporter={BGD} AND importer={IND} AND year=2023")
    m = scalar(f"SELECT sum(value_kusd) FROM read_parquet('{BIL}') WHERE exporter={IND} AND importer={BGD} AND year=2023")
    print(f"BGD->IND 2023 {x:,.3f}; IND->BGD 2023 {m:,.3f}; balance {x-m:,.3f}; cover ratio {x/m:.4f}   <- quant-bilateral-india")
    prods = ["610910", "620342", "530310", "640399"]
    wt = scalar(f"SELECT sum(total_exports) FROM '{TOTALS}' WHERE year=2023")
    print(f"world exports 2023 {wt:,.3f}")
    best = None
    for p in prods:
        bx = scalar(f"SELECT coalesce(sum(export_value),0) FROM read_parquet('{CYP}') WHERE country_code={BGD} AND year=2023 AND product_code='{p}'")
        wx = scalar(f"SELECT coalesce(sum(export_value),0) FROM read_parquet('{CYP}') WHERE year=2023 AND product_code='{p}'")
        rca = (bx / e23) / (wx / wt)
        print(f"  {p}: BGD {bx:,.3f} world {wx:,.3f} RCA {rca:.4f}")
        if best is None or rca > best[1]:
            best = (p, rca)
    print(f"  highest RCA: {best[0]} {best[1]:.4f}   <- quant-rca-pick")
    # 852872 dropped: zero BGD imports in BACI 2023, a weighted average needs positive weights
    rows = q(f"SELECT hs6, applied_mfn, applied_year FROM '{MFN}' WHERE economy_iso3='BGD' AND hs6 IN ('870323','100630','300490') ORDER BY hs6")
    print("BGD applied MFN (WTO tariff profiles via TradeWeave):", rows)
    imp = {}
    for hs6, _, _ in rows:
        imp[hs6] = scalar(f"SELECT coalesce(sum(import_value),0) FROM read_parquet('{CYP}') WHERE country_code={BGD} AND year=2023 AND product_code='{hs6}'")
    print("  BGD 2023 imports by line:", {k: round(v, 3) for k, v in imp.items()})
    if rows and all(imp.values()):
        simple = sum(r[1] for r in rows) / len(rows)
        weighted = sum(r[1] * imp[r[0]] for r in rows) / sum(imp.values())
        print(f"  simple avg {simple:.4f}  import-weighted avg {weighted:.4f}   <- quant-tariff-weighted")


def finance() -> None:
    print("\n== FinObservatory parquet ==")
    rows = q(f"SELECT date, maturity_yr, fitted_yield_pct, term_premium_pct, exp_short_rate_pct FROM '{F}/acm_term_premia.parquet' WHERE freq='monthly' AND maturity_yr=10 ORDER BY date DESC LIMIT 1")
    print("ACM 10y latest monthly:", rows, "  <- fin-term-premium")
    rows = q(f"SELECT NAME, REPDTE, ASSET_THOUSANDS_USD, composite_score FROM '{F}/bank_scores.parquet' ORDER BY ASSET_THOUSANDS_USD DESC LIMIT 3")
    print("bank_scores top 3 by assets:", rows)


def arithmetic() -> None:
    print("\n== author-defined arithmetic references ==")
    # Eisenberg-Noe clearing vector, 3 banks (fictitious-default algorithm)
    L = [[0, 40, 10], [20, 0, 30], [10, 10, 0]]
    e = [15, 5, 20]
    n = 3
    pbar = [sum(L[i]) for i in range(n)]
    Pi = [[L[i][j] / pbar[i] if pbar[i] else 0 for j in range(n)] for i in range(n)]
    p = pbar[:]
    for _ in range(100):
        inflow = [sum(Pi[j][i] * p[j] for j in range(n)) for i in range(n)]
        new = [min(pbar[i], max(0.0, e[i] + inflow[i])) for i in range(n)]
        if all(abs(new[i] - p[i]) < 1e-12 for i in range(n)):
            break
        p = new
    print(f"Eisenberg-Noe clearing vector: {[round(v, 6) for v in p]}   <- fin-eisenberg-noe, code-eisenberg-noe")
    k, D, E, lrmes = 0.08, 1200.0, 150.0, 0.40
    srisk = k * D - (1 - k) * (1 - lrmes) * E
    print(f"SRISK k={k} D={D} E={E} LRMES={lrmes}: {srisk:.4f}   <- fin-srisk")
    cet1, rwa = 42.5, 380.0
    print(f"CET1 ratio {cet1}/{rwa}: {cet1/rwa*100:.4f}%   <- fin-cet1")
    print(f"Fisher exact real rate 12.5% nominal, 9.9% inflation: {(1.125/1.099-1)*100:.4f}%   <- fin-real-rate")
    print(f"ToT: Px +5%, Pm +8%: {(1.05/1.08-1)*100:.4f}%   <- reason-terms-of-trade")
    print(f"RER: e +10%, P* +3%, P +9.5%: {(1.10*1.03/1.095-1)*100:.4f}%   <- reason-real-depreciation")
    a = 500 * (1 - 0.015) * 122.5
    b = 500 * 121.0
    print(f"remittance A {a:.2f} B {b:.2f} diff B-A {b-a:.2f}   <- reason-remittance-fx")
    print(f"HYSA 10000 at 4.25% APY, 9 months: {10000*(1.0425**0.75-1):.4f}   <- reason-hysa-interest")
    print(f"log-point 0.42 -> percent: {(math.exp(0.42)-1)*100:.4f}   <- reason-gravity-coef")
    print(f"9.6 from 7.7: {(9.6/7.7-1)*100:.4f}% (+{9.6-7.7:.1f} pp)   <- review-consistency, code-pct-consistency")


if __name__ == "__main__":
    trade()
    finance()
    arithmetic()
