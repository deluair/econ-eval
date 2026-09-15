"""Emit the 30 "daily work" tasks added 2026-09-15 as tasks/*.yaml.

Every number below is copied from scripts/build_references_daily.py output of
2026-09-15 (BACI via TradeWeave parquet, FinObservatory ACM parquet) or is an
author-defined input whose reference that script computes. Re-run this file only
after re-verifying those numbers; the yamls are the tracked artifact.
"""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "tasks"
REF = "scripts/build_references_daily.py, 2026-09-15"
TW = f"~/tradeweave/data/parquet (BACI HS22 via TradeWeave, thousands USD; {REF})"


def block(s: str, indent: int) -> str:
    pad = " " * indent
    return "\n".join(pad + line if line else "" for line in s.strip("\n").splitlines())


def emit(task: dict) -> None:
    g = task["grader"]
    lines = [f"id: {task['id']}", f"track: {task['track']}", "prompt: |", block(task["prompt"], 2), "grader:",
             f"  type: {g['type']}"]
    if g["type"] == "numeric":
        lines += [f"  reference: {g['reference']}", f"  tolerance_pct: {g['tolerance_pct']}"]
    elif g["type"] == "code_exec":
        lines += ["  assertions: |", block(g["assertions"], 4), f"  timeout_s: {g.get('timeout_s', 20)}"]
    elif g["type"] == "judge":
        lines += ["  rubric:"] + [f'    - "{p}"' for p in g["rubric"]]
    lines += [f'source: "{task["source"]}"', "samples: 5", ""]
    (OUT / f"{task['id']}.yaml").write_text("\n".join(lines))


NUM = "Reply with a single number on a line beginning \"ANSWER:\"."

TASKS = [
    # ---------------- quantitative (BACI via TradeWeave) ----------------
    dict(id="quant-cagr-decade", track="quantitative", prompt=f"""
Bangladesh total merchandise exports (BACI, thousands USD): 32,146,279.163 in
2013 and 57,695,013.137 in 2023. Compute the compound annual growth rate over
the ten years, in percent. {NUM}""",
         grader=dict(type="numeric", reference=6.0232, tolerance_pct=0.5), source=TW),
    dict(id="quant-growth-year", track="quantitative", prompt=f"""
Bangladesh total merchandise exports (BACI, thousands USD): 65,871,533.408 in
2022 and 57,695,013.137 in 2023. Compute the 2023 growth rate in percent,
with its sign. {NUM}""",
         grader=dict(type="numeric", reference=-12.4128, tolerance_pct=0.5), source=TW),
    dict(id="quant-rmg-share-change", track="quantitative", prompt=f"""
Bangladesh exports (BACI, thousands USD). 2013: ready-made garments (HS
chapters 61 and 62) 26,381,097.079 out of total exports 32,146,279.163. 2023:
garments 49,656,452.203 out of total exports 57,695,013.137. By how many
percentage points did the garment share of total exports change between 2013
and 2023? {NUM}""",
         grader=dict(type="numeric", reference=4.0014, tolerance_pct=1.0), source=TW),
    dict(id="quant-bilateral-india", track="quantitative", prompt=f"""
BACI 2023, thousands USD: Bangladesh exports to India 2,007,784.364;
India exports to Bangladesh 12,344,787.099. Compute Bangladesh's bilateral
merchandise trade balance with India in MILLIONS of US dollars, with its
sign. {NUM}""",
         grader=dict(type="numeric", reference=-10337.003, tolerance_pct=0.5), source=TW),
    dict(id="quant-rca-pick", track="quantitative", prompt=f"""
BACI 2023, thousands USD. Bangladesh total exports 57,695,013.137; world total
exports 22,960,416,672.717. Bangladesh and world exports by HS6 product:
610910 (cotton T-shirts) 7,413,218.568 and 33,707,566.444;
620342 (cotton trousers) 6,199,887.454 and 23,664,155.856;
530310 (raw jute) 155,601.933 and 196,005.822;
640399 (other leather footwear) 256,958.588 and 32,456,627.478.
Compute the Balassa revealed comparative advantage index for each product and
report the HIGHEST index value. {NUM}""",
         grader=dict(type="numeric", reference=315.9276, tolerance_pct=1.0), source=TW),
    dict(id="quant-tariff-weighted", track="quantitative", prompt=f"""
Bangladesh applied MFN tariffs (ad valorem, percent, 2024 schedule) and
Bangladesh's 2023 imports of the same lines (BACI, thousands USD):
HS 100630 rice 25.0 percent, imports 149,196.922;
HS 300490 medicaments 8.75 percent, imports 47,192.055;
HS 870323 motor cars 1500-3000cc 20.7143 percent, imports 73,816.86.
Compute the import-weighted average tariff across the three lines, in
percent. {NUM}""",
         grader=dict(type="numeric", reference=20.9911, tolerance_pct=0.5),
         source=f"~/tradeweave/data/parquet/applied_mfn_hs6.parquet (WTO tariff profiles, BGD 2024) and BACI 2023 imports; {REF}"),
    # ---------------- finance ----------------
    dict(id="fin-srisk", track="finance", prompt=f"""
A bank has market value of equity 150, book value of debt 1,200 (both in
billions USD) and a long-run marginal expected shortfall (LRMES) of 40 percent
in a crisis. Using the Brownlees and Engle (2017) SRISK definition with
prudential capital ratio k = 8 percent, compute SRISK in billions USD. {NUM}""",
         grader=dict(type="numeric", reference=13.2, tolerance_pct=1.0),
         source=f"Brownlees and Engle (2017, RFS) SRISK = k*D - (1-k)*(1-LRMES)*E; author-defined inputs, reference computed by {REF}"),
    dict(id="fin-eisenberg-noe", track="finance", prompt=f"""
Three banks A, B, C. Nominal interbank liabilities (row owes column): A owes B
40 and C 10; B owes A 20 and C 30; C owes A 10 and B 10. External (non-bank)
assets: A 15, B 5, C 20. Under the Eisenberg and Noe (2001) clearing mechanism
(limited liability, absolute priority, pro-rata sharing), what total payment
does bank A make to the other banks? {NUM}""",
         grader=dict(type="numeric", reference=45.0, tolerance_pct=0.5),
         source=f"Eisenberg and Noe (2001, Management Science) fictitious-default algorithm; author-defined network, reference computed by {REF}"),
    dict(id="fin-cet1", track="finance", prompt=f"""
A bank reports: common equity tier 1 capital 42.5, additional tier 1 capital
6.5, tier 2 capital 12.0, risk-weighted assets 380.0 (all billions USD).
Compute the CET1 capital ratio as defined under Basel III, in percent. {NUM}""",
         grader=dict(type="numeric", reference=11.1842, tolerance_pct=0.5),
         source=f"Basel III CET1 ratio = CET1 capital / RWA; author-defined inputs, reference computed by {REF}"),
    dict(id="fin-term-premium", track="finance", prompt=f"""
Adrian, Crump and Moench (ACM) model, 10-year maturity, 2026-07-31: fitted
zero-coupon yield 4.8230 percent, model-implied average expected short rate
over the ten years 3.9854 percent. Compute the 10-year term premium in
percentage points. {NUM}""",
         grader=dict(type="numeric", reference=0.8376, tolerance_pct=1.0),
         source=f"~/finobservatory/data/parquet/acm_term_premia.parquet (NY Fed ACM, monthly, 2026-07-31 row; {REF})"),
    dict(id="fin-real-rate", track="finance", prompt=f"""
A one-year deposit pays a nominal rate of 12.5 percent and inflation over the
year is 9.9 percent. Compute the exact ex post real interest rate from the
Fisher relation (not the linear approximation), in percent. {NUM}""",
         grader=dict(type="numeric", reference=2.3658, tolerance_pct=1.0),
         source=f"Fisher relation (1+i) = (1+r)(1+pi); author-defined inputs, reference computed by {REF}"),
    # ---------------- coding ----------------
    dict(id="code-hs-normalize", track="coding", prompt="""
Write a Python function normalize_hs(code) that returns a canonical six-character
HS6 code string. Input may be an int or a str. Rules: remove spaces and dots;
codes that lost leading zeros when stored as integers must be left-padded with
zeros to six digits; raise ValueError if the cleaned code has more than six
digits or contains a non-digit. Standard library only. Return only the code.""",
         grader=dict(type="code_exec", assertions="""
assert normalize_hs(10121) == "010121"
assert normalize_hs("6109.10") == "610910"
assert normalize_hs(" 620342 ") == "620342"
assert normalize_hs("0306.17") == "030617"
assert normalize_hs(3004) == "003004"
try:
    normalize_hs("6109101")
    raise SystemExit("expected ValueError")
except ValueError:
    pass
try:
    normalize_hs("61O910")
    raise SystemExit("expected ValueError")
except ValueError:
    pass"""), source="deterministic unit test; BACI product_code convention (six-digit strings; author-defined, 2026-09-15)"),
    dict(id="code-pct-consistency", track="coding", prompt="""
Write a Python function flag_inconsistent(rows, tol=0.1) for checking a
report's growth figures. rows is a list of (old, new, reported_pct_change)
tuples. The true percent change is (new / old - 1) * 100. Return the list of
indices (in order) where the absolute difference between the true change and
the reported change exceeds tol percentage points. Standard library only.
Return only the code.""",
         grader=dict(type="code_exec", assertions="""
assert flag_inconsistent([(7.7, 9.6, 23.7), (100, 110, 10.0), (50, 40, -20.0)]) == [0]
assert flag_inconsistent([(7.7, 9.6, 24.7)]) == []
assert flag_inconsistent([]) == []
assert flag_inconsistent([(200, 210, 5.0), (200, 210, 5.2), (200, 210, 4.95)], tol=0.1) == [1]"""),
         source="deterministic unit test; internal-consistency check from the owner's quality gate (9.6 from 7.7 is +24.7 percent, not +23.7; author-defined, 2026-09-15)"),
    dict(id="code-sqlite-top3", track="coding", prompt="""
A SQLite table exports(country TEXT, year INTEGER, hs6 TEXT, value_kusd REAL)
holds export values in thousands USD. Write Python code that defines a string
variable QUERY containing one SQL statement returning the three largest hs6
lines for country 'BGD' in year 2023, columns hs6 and value_kusd, ordered by
value_kusd descending. Return only the code (just the QUERY assignment).""",
         grader=dict(type="code_exec", assertions="""
import sqlite3
con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE exports(country TEXT, year INTEGER, hs6 TEXT, value_kusd REAL)")
con.executemany("INSERT INTO exports VALUES (?,?,?,?)", [
    ("BGD", 2023, "610910", 7413218.568), ("BGD", 2023, "620342", 6199887.454),
    ("BGD", 2023, "530310", 155601.933), ("BGD", 2023, "640399", 256958.588),
    ("BGD", 2022, "610910", 8000000.0), ("VNM", 2023, "610910", 9000000.0)])
rows = con.execute(QUERY).fetchall()
assert [r[0] for r in rows] == ["610910", "620342", "640399"], rows
assert abs(rows[2][1] - 256958.588) < 1e-6"""),
         source="deterministic unit test on an in-memory SQLite table; values from BACI 2023 via TradeWeave (author-defined, 2026-09-15)"),
    dict(id="code-eisenberg-noe", track="coding", prompt="""
Write a Python function clearing_vector(L, e) implementing the Eisenberg and
Noe (2001) clearing payment vector. L is an n x n list of lists of nominal
interbank liabilities (L[i][j] is what bank i owes bank j, zero diagonal) and e
is the list of external assets. Use the fictitious-default algorithm or fixed
point iteration on p_i = min(pbar_i, max(0, e_i + sum_j Pi_ji * p_j)) with
pro-rata shares Pi. Return the list of clearing payments. Standard library
only. Return only the code.""",
         grader=dict(type="code_exec", assertions="""
L = [[0, 40, 10], [20, 0, 30], [10, 10, 0]]
e = [15, 5, 20]
p = clearing_vector(L, e)
assert all(abs(a - b) < 1e-6 for a, b in zip(p, [45.0, 50.0, 20.0])), p
p2 = clearing_vector([[0, 10], [5, 0]], [100, 100])
assert all(abs(a - b) < 1e-6 for a, b in zip(p2, [10.0, 5.0])), p2
assert clearing_vector([[0]], [3.0]) == [0] or abs(clearing_vector([[0]], [3.0])[0]) < 1e-9""",
                     timeout_s=30),
         source=f"Eisenberg and Noe (2001) definition; reference vector [45, 50, 20] computed by {REF}"),
    dict(id="code-kusd-format", track="coding", prompt="""
Write a Python function fmt_kusd(x) that formats a value given in THOUSANDS of
US dollars for a chart label. Rules: absolute value at least 1,000,000 (i.e. a
billion dollars or more) prints as billions with one decimal, e.g. "$65.9B";
absolute value at least 1,000 prints as millions with one decimal, e.g.
"$149.2M"; smaller values print as whole thousands, e.g. "$850K"; negative
values put the minus sign before the dollar sign, e.g. "-$10.3B". Use Python's
built-in rounding. Standard library only. Return only the code.""",
         grader=dict(type="code_exec", assertions="""
assert fmt_kusd(65871533.408) == "$65.9B"
assert fmt_kusd(149196.922) == "$149.2M"
assert fmt_kusd(850.4) == "$850K"
assert fmt_kusd(-10337002.735) == "-$10.3B"
assert fmt_kusd(1000) == "$1.0M"
assert fmt_kusd(0) == "$0K\""""),
         source="deterministic unit test; TradeWeave chart-label convention (BACI thousands USD; author-defined, 2026-09-15)"),
    # ---------------- reasoning (numeric) ----------------
    dict(id="reason-terms-of-trade", track="reasoning", prompt=f"""
Over a year a country's export price index rises 5 percent and its import
price index rises 8 percent. By what percent do its terms of trade change,
with sign? {NUM}""",
         grader=dict(type="numeric", reference=-2.7778, tolerance_pct=1.0),
         source=f"terms of trade = Px/Pm; author-defined inputs, reference computed by {REF}"),
    dict(id="reason-real-depreciation", track="reasoning", prompt=f"""
The taka depreciates 10 percent against the dollar in nominal terms (taka per
dollar rises 10 percent). Over the same year US prices rise 3 percent and
Bangladeshi prices rise 9.5 percent. Compute the exact percent change in the
real exchange rate defined as e * P_us / P_bd (a rise is a real
depreciation), not the linear approximation. {NUM}""",
         grader=dict(type="numeric", reference=3.4703, tolerance_pct=0.5),
         source=f"real exchange rate q = e*P*/P; author-defined inputs, reference computed by {REF}"),
    dict(id="reason-remittance-fx", track="reasoning", prompt=f"""
Sending 500 US dollars to Bangladesh. Option A: exchange rate 122.5 taka per
dollar with a 1.5 percent fee deducted from the dollar amount before
conversion. Option B: exchange rate 121.0 taka per dollar with no fee. How
many more taka does the better option deliver than the other? {NUM}""",
         grader=dict(type="numeric", reference=168.75, tolerance_pct=0.5),
         source=f"author-defined inputs (owner's monthly remittance planning), reference computed by {REF}"),
    dict(id="reason-hysa-interest", track="reasoning", prompt=f"""
A high-yield savings account advertises a 4.25 percent APY (annual percentage
yield, which already includes compounding). 10,000 dollars is deposited and
left for exactly nine months with no other activity. How many dollars of
interest are earned, using the APY definition (fractional-year compounding)
rather than a simple pro-rata of the annual rate? {NUM}""",
         grader=dict(type="numeric", reference=317.0859, tolerance_pct=0.5),
         source=f"APY definition: balance * ((1+APY)^(t/12) - 1); author-defined inputs, reference computed by {REF}"),
    dict(id="reason-gravity-coef", track="reasoning", prompt=f"""
A gravity regression of log bilateral exports on a dummy for a regional trade
agreement gives a coefficient of 0.42. Compute the implied percent effect of
the agreement on exports, using the exact transformation rather than the
approximation that reads the coefficient as a percent. {NUM}""",
         grader=dict(type="numeric", reference=52.1962, tolerance_pct=0.5),
         source=f"semi-elasticity of a dummy in a log-linear model: 100*(exp(b)-1); author-defined input, reference computed by {REF}"),
    # ---------------- review (judge) ----------------
    dict(id="review-consistency", track="review", prompt="""
You are checking a draft policy note before it ships. Find every internal
inconsistency or unit error in the passage below, quote the wrong figure,
and give the corrected value. Do not flag figures that are correct. Under 120
words.

"Bangladesh's export growth rose to 9.6 percent from 7.7 percent, a 23.7
percent increase in the growth rate (1.9 percentage points). BACI records
2023 exports of 57,695,013 thousand USD, that is 57.7 billion USD. Imports
from India were 12,344,787 thousand USD, or 12.3 million USD, so the
bilateral deficit with India remains large." """,
         grader=dict(type="judge", rubric=[
             "Flags 23.7 percent as wrong and gives about 24.7 percent (9.6/7.7 - 1) as the correction",
             "Flags 12.3 million USD as a unit error and corrects it to about 12.3 billion USD",
             "Does not flag the 1.9 percentage points or the 57.7 billion USD, which are correct",
             "Quotes the wrong figures verbatim and stays under 120 words with no filler"]),
         source="owner's quality-gate example (9.6 from 7.7 = +24.7 percent) and BACI 2023 figures via TradeWeave; author-defined passage, 2026-09-15"),
    dict(id="review-referee-comment", track="review", prompt="""
Write one referee comment, under 150 words, on this abstract for an economics
journal. Be specific about the identification problem and propose one
concrete fix.

"Using ordinary least squares on a panel of 45 developing countries over
2000 to 2020, we regress log GDP per capita on log merchandise exports with
year dummies. We find that a 10 percent increase in exports raises GDP per
capita by 3.2 percent, and conclude that export promotion is a first-order
growth policy." """,
         grader=dict(type="judge", rubric=[
             "Identifies reverse causality or simultaneity between exports and income as the core identification problem",
             "Proposes a concrete fix (instrumental variables such as gravity-predicted trade, country fixed effects with a credible shock, or a quasi-experimental design)",
             "Notes that the 3.2 percent figure is a correlational elasticity and that the policy conclusion does not follow from it as stated",
             "Referee register: specific, courteous, no filler, under 150 words"]),
         source="rubric authored from standard trade-and-growth identification critique (Frankel and Romer 1999 instrument); author-defined abstract, 2026-09-15"),
    dict(id="review-agent-brief", track="review", prompt="""
Write a work brief for a cheap coding model that will implement one feature
without asking questions. Feature: add GET /api/hhi?country=ISO3&year=YYYY to
an existing FastAPI app; it returns the Herfindahl-Hirschman index of a
country's export concentration across HS6 products for that year, computed
with DuckDB from a parquet file with columns country_code, year, product_code,
export_value (thousands USD). Under 250 words. Include a fenced acceptance
block of shell commands that must pass.""",
         grader=dict(type="judge", rubric=[
             "States the HHI definition precisely (sum of squared product shares of total exports) and the scale used (0 to 1 or 0 to 10,000)",
             "Scopes the change: names the file(s) to touch and says what not to touch",
             "Specifies the error behaviour for a missing country or year (a 404 or 422 with a message)",
             "Includes a fenced acceptance block with at least one runnable check (curl, pytest, or python) that a runner could execute",
             "Under 250 words, imperative, no filler"]),
         source="owner's dcode loop brief format (docs/briefs with an acceptance block); rubric author-defined, 2026-09-15"),
    dict(id="review-systemd-timer", track="review", prompt="""
Write a systemd user timer and service pair that runs
/home/dulal/dotfiles/bin/weekly-ledger.sh every Monday at 21:30 New York
time, catching up a missed run after the machine was off. Give both unit
files and the commands to install and enable them. Under 200 words.""",
         grader=dict(type="judge", rubric=[
             "Timer uses OnCalendar with Monday 21:30 and the America/New_York time zone (or an equivalent explicit zone)",
             "Timer sets Persistent=true for catch-up after downtime",
             "Service is Type=oneshot with the given ExecStart path; timer has WantedBy=timers.target",
             "Gives the user-level install commands: place or link units under ~/.config/systemd/user, daemon-reload, enable --now the timer"]),
         source="systemd.timer(5) and systemd.service(5) semantics; the owner's own ledger-weekly.timer (dotfiles/systemd), 2026-09-15"),
    # ---------------- writing (judge) ----------------
    dict(id="write-x-post", track="writing", prompt="""
Write one post for X (formerly Twitter), at most 280 characters, from these
facts and nothing else: Bangladesh merchandise exports were 57.7 billion USD
in 2023, down 12.4 percent from 65.9 billion in 2022; garments were 86.1
percent of the 2023 total; source BACI. One clear takeaway, no emojis, at
most one hashtag.""",
         grader=dict(type="judge", rubric=[
             "At most 280 characters",
             "Uses the given figures correctly (57.7 billion, down 12.4 percent, 86.1 percent) and invents no other number",
             "Names BACI as the source",
             "One clear takeaway or hook, no emojis, at most one hashtag, no filler"]),
         source="~/tradeweave/data/parquet (BACI 2022-2023 via TradeWeave); the owner's daily X post routine; rubric author-defined, 2026-09-15"),
    dict(id="write-cover-paragraph", track="writing", prompt="""
Write the opening paragraph (90 to 120 words) of a cover letter for a Trade
Economist position at an international financial institution. Use only these
facts: PhD in economics (2020); international trade economist; built
TradeWeave, a trade analytics platform covering 238 countries and 30 years of
BACI data; works in Python and DuckDB. Do not invent employers, publications,
or degrees. Do not open with "I am writing to apply".""",
         grader=dict(type="judge", rubric=[
             "90 to 120 words",
             "Uses only the given facts; invents no employer, publication, degree, or metric",
             "Opens with value or fit, not with 'I am writing to apply'",
             "Names the role, professional register, no clichés or filler"]),
         source="the owner's job-application answer sheet facts; rubric author-defined, 2026-09-15"),
    dict(id="write-bangla-plain-remittance", track="writing", prompt="""
Write 100 to 140 words in plain, everyday Bengali (spoken register, not formal
or literary) explaining to a family member which remittance option is better
and why: Option A converts 500 dollars at 122.5 taka per dollar after a 1.5
percent fee; Option B converts at 121.0 taka per dollar with no fee. Option B
delivers 168.75 taka more. State the winner and the taka difference.""",
         grader=dict(type="judge", rubric=[
             "Written in Bengali script throughout, plain spoken register (no formal or literary verb forms)",
             "States that Option B (121.0, no fee) wins and gives the difference as about 168.75 taka",
             "Explains the reason: the 1.5 percent fee costs more than the better rate gains",
             "100 to 140 words, no filler"]),
         source=f"author-defined inputs, difference computed by {REF}; plain-Bengali register rule from the owner's writing guidance"),
    dict(id="write-abstract-150", track="writing", prompt="""
Write a 130 to 160 word abstract from these findings only. Study: simulated
effect of Bangladesh's scheduled graduation from least developed country
status on garment exports to the European Union. Method: Armington partial
equilibrium model, elasticity of substitution 4, HS6 tariff lines. Inputs:
duty-free access under the EU Everything But Arms scheme ends three years
after graduation; the applicable MFN duties on the main garment lines are 9.6
to 12 percent. Result: garment exports to the EU fall 5.7 percent in the
central case, 3.9 to 8.1 percent across elasticity values 3 to 6. Policy point:
the GSP+ scheme would preserve most of the access if its conditions are met.""",
         grader=dict(type="judge", rubric=[
             "130 to 160 words, single paragraph",
             "States the question, method (Armington PE, sigma 4, HS6), headline result (5.7 percent, range 3.9 to 8.1) and the GSP+ implication",
             "Invents no number, scheme, or finding beyond the given ones",
             "Working-paper register: precise, no hedging filler, no 'in conclusion'"]),
         source="author-defined findings (illustrative, not a published estimate) in the owner's working-paper style; rubric author-defined, 2026-09-15"),
    dict(id="write-recruiter-reply", track="writing", prompt="""
A recruiter emailed offering a 30-minute screening call for an Economist role
this week. Write the reply in 60 to 80 words: accept, propose two specific
time slots in Eastern Time, and ask exactly one question about the role.""",
         grader=dict(type="judge", rubric=[
             "60 to 80 words",
             "Accepts and proposes two specific time slots that name Eastern Time",
             "Asks exactly one question about the role",
             "Warm, professional, no filler or apology"]),
         source="the owner's daily job-pipeline email routine; rubric author-defined, 2026-09-15"),
]

if __name__ == "__main__":
    for t in TASKS:
        emit(t)
    print(f"wrote {len(TASKS)} tasks to {OUT}")
