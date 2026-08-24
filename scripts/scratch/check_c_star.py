"""Check whether local health signals predict the walk breakdown boundary."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# threshold is a single number on repetition fraction, the cheapest signal
REP_THRESHOLD = 25
UNFINISHED_THRESHOLD = 50
ROLLEAK_THRESHOLD = 25


def c_star(artifact_path: Path, method: str):
    art = json.loads(artifact_path.read_text())
    out = {}
    for side in ("+C", "-C"):
        s = art["demo_stats"][side]
        # the walk's health() fires when any of these three trips; use same cuts
        trip = (
            s["repeated"] >= REP_THRESHOLD
            or s["unfinished"] >= UNFINISHED_THRESHOLD
            or s["role_leaks"] >= ROLLEAK_THRESHOLD
        )
        out[side] = trip
    return out

print(f"SHOULD: each walk has a boundary g where the walk's 2-rung streak fires; "
      f"C* is the first C that trips rep>={REP_THRESHOLD} or unf>={UNFINISHED_THRESHOLD} "
      f"or leak>={ROLLEAK_THRESHOLD}. Gap is C* offset in grid steps.")
print(f"ELSE the cheap rule misses the channel that actually broke.")
print("| method | seed | side | boundary g | C(boundary) | C* g | C(C*) | gap |")
print("| --- | --- | --- | --- | --- | --- | --- | --- |")
misses = 0
for method in ("vjp_delta", "mean_diff", "pca"):
    for seed in (0, 1, 2):
        cert = json.loads((ROOT / f"outputs/walk_{method}_s{seed}.json").read_text())
        for side in ("+C", "-C"):
            boundary = cert["state"][side]["boundary"]
            if boundary is None:
                # never broke within the walked window; nothing to predict
                cstar_g = None
                cstar_c = "-"
                gap = "-"
            else:
                # find first g on this walk+side where the cheap rule would have tripped
                first_trip = None
                for rung in cert["rungs"]:
                    art = json.loads((ROOT / rung["run_dir"] / f"{method}.json").read_text())
                    s = art["demo_stats"][side]
                    rep = s.get("repeated", s.get("repeat_count", 0))
                    if rep >= REP_THRESHOLD or s["unfinished"] >= UNFINISHED_THRESHOLD or s["role_leaks"] >= ROLLEAK_THRESHOLD:
                        first_trip = rung["grid_index"]
                        cstar_c_val = rung["coefficient"]
                        break
                if first_trip is None:
                    cstar_g = "none"
                    cstar_c = "-"
                    gap = "miss"
                    misses += 1
                else:
                    cstar_g = first_trip
                    cstar_c = f"{cstar_c_val:g}"
                    gap = first_trip - boundary
                    if abs(gap) > 1:
                        misses += 1
                b_c = cert["rungs"][boundary]["coefficient"]
                print(f"| {method} | {seed} | {side} | {boundary} | {b_c:g} | {cstar_g} | {cstar_c} | {gap} |")
print(f"\nmisses outside [-1,+1]: {misses}")
