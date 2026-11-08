"""Print experiment 2's held-back results and decisions in plain words (reads outputs/exp02 only)."""
import json
from pathlib import Path
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "outputs" / "exp02"
METRICS = ["annual_avg_temp", "total_precip_in", "cdd", "hottest_day_temp"]
METHODS = [("avg", "plain average"), ("line", "plain line"), ("hybrid", "hybrid")]
COLS = ["1998", "2004", "2011", "average"]
res = pd.read_csv(OUT / "heldout_results.csv", dtype={"origin": str})
dec = json.loads((OUT / "decision.json").read_text())

print("HELD-BACK RESULTS (origins 1998, 2004, 2011; skill is vs the plain average)")
for m in METRICS:
    print(f"\n{m}")
    t = res[res.metric == m]
    rows = []
    for k, name in METHODS:
        r = t[t.method == k].set_index("origin")
        rows.append([name, *[f"{r.mae[c]:.3f}" for c in COLS], *[f"{r.skill[c]:+.3f}" for c in COLS]])
    hdr = pd.MultiIndex.from_tuples([("", "method")] + [("MAE", c) for c in COLS] + [("skill", c) for c in COLS])
    print(pd.DataFrame(rows, columns=hdr).to_string(index=False))

print("\nDECISIONS")
NAME = {"avg": "plain average", "line": "plain line", "hybrid": "hybrid"}
for m in METRICS:
    d = dec[m]; sk = d["avg_skill"]; per = d["per_origin_skill"]
    if d["plan"] == "decide":
        best = "line" if sk["line"] >= sk["avg"] else "avg"
        ref = max(sk["line"], sk["avg"])
        print(f"\n{m}: chosen = {NAME[d['method']]}" + (" (hybrid dropped)" if d["hybrid_dropped"] else " (hybrid kept)"))
        ck = d["checks"]
        r1 = ck["avg_skill_higher_than_line_and_avg"]
        print(f"  Rule 1, average skill above both line and average: {'PASS' if r1 else 'FAIL'} "
              f"(hybrid {sk['hybrid']:+.4f} vs best other {ref:+.4f} [{NAME[best]}], short by {ref - sk['hybrid']:.4f})" if not r1 else
              f"  Rule 1, average skill above both line and average: PASS (hybrid {sk['hybrid']:+.4f} vs {ref:+.4f})")
        r2 = ck["beats_both_in_at_least_2_of_3_origins"]
        det = ", ".join(f"{o}: hybrid {per['hybrid'][o]:+.3f} vs line {per['line'][o]:+.3f}" for o in per["hybrid"])
        print(f"  Rule 2, beats both in at least 2 of 3 origins:     {'PASS' if r2 else 'FAIL'} (won {d['origins_won']} of 3; {det})")
        r3 = ck[next(k for k in ck if k.startswith('margin'))]
        print(f"  Rule 3, beats the better one by at least 0.02:     {'PASS' if r3 else 'FAIL'} "
              f"(margin achieved {d['margin_achieved']:+.4f}; needed +0.0200, short by {0.02 - d['margin_achieved']:.4f})")
    else:
        print(f"\n{m}: chosen = {NAME[d['method']]} (fixed by METRIC_PLAN, no decision rule). "
              f"Held-back skill: plain line {sk['line']:+.3f}, hybrid {sk['hybrid']:+.3f}")

print("\nPRECIPITATION: plain average vs plain line on held-back years (report only, method not changed)")
t = res[(res.metric == "total_precip_in") & res.method.isin(["avg", "line"])].pivot(index="origin", columns="method", values="mae").loc[COLS]
t["better"] = t.apply(lambda r: "plain average" if r.avg < r.line else "plain line", axis=1)
t["avg"], t["line"] = t.avg.map("{:.3f}".format), t.line.map("{:.3f}".format)
print(t.rename(columns={"avg": "MAE plain average", "line": "MAE plain line"}).to_string())
