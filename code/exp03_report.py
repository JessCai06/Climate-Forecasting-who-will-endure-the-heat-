"""Print experiment 3's held-back results and decisions in plain words (reads outputs/exp03 only)."""
import json
from pathlib import Path
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "outputs" / "exp03"
METRICS = ["annual_avg_temp", "total_precip_in", "hottest_day_temp", "cdd"]
NAME = {"avg": "A plain average", "line": "B own line", "shared": "C shared slope", "half": "D half slope"}
COLS = ["1998", "2004", "2011", "average"]
res = pd.read_csv(OUT / "heldout_results.csv", dtype={"origin": str})
dec = json.loads((OUT / "decision.json").read_text())

print("HELD-BACK RESULTS (origins 1998, 2004, 2011; skill is vs the plain average)")
for m in METRICS:
    print(f"\n{m}")
    rows = []
    for k, name in NAME.items():
        r = res[(res.metric == m) & (res.method == k)].set_index("origin")
        rows.append([name, *[f"{r.mae[c]:.3f}" for c in COLS], *[f"{r.skill[c]:+.3f}" for c in COLS]])
    hdr = pd.MultiIndex.from_tuples([("", "idea")] + [("MAE", c) for c in COLS] + [("skill", c) for c in COLS])
    print(pd.DataFrame(rows, columns=hdr).to_string(index=False))

print("\nDECISIONS")
for m in METRICS:
    d = dec[m]
    sk = d["avg_skill"]
    print(f"\n{m}: chosen = {NAME[d['method']]}")
    print(f"  ranking by average skill: " + ", ".join(f"{NAME[k]} {sk[k]:+.4f}" for k in d["ranked_by_avg_skill"]))
    print(f"  highest = {NAME[d['highest']]}; lead over runner-up ({NAME[d['runner_up']]}) = {d['lead_over_runner_up']:.4f} (close-call threshold 0.01)")
    print(f"  origins beating the plain average (of 3): " + ", ".join(f"{NAME[k]} {v}" for k, v in d["origins_beating_plain_average"].items() if k != "avg"))
    print(f"  why: {d['reason']}")
