"""Temporary check (PI/claude): old walk() at HEAD vs cleaned walk() write identical certificates on fake rungs.
Run: git show 1986fc4:scripts/walk.py > /tmp/walk_old.py && uv run python slop/reviews/20260928_walk_cleanup_equivalence.py
"""
import argparse, hashlib, importlib.util, json, random, sys, tempfile
from pathlib import Path
from unittest.mock import MagicMock

# walk() uses no torch/model code; stub heavy imports so the check runs in seconds
for name in ("torch", "transformers", "steering_lite", "steering_lite.calibrate", "steering_lite.data",
             "vjp_steering", "vjp_steering.j_lens_concept", "vjp_steering.vjp"):
    sys.modules[name] = MagicMock()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def u(*key):  # deterministic uniform in [0,1) from a key
    return int(hashlib.sha256(repr(key).encode()).hexdigest()[:8], 16) / 2**32


def make_fake(root: Path, scenario: dict):
    def adopted(method, seed, c, model, max_new_tokens, walk_id):
        stats, reasons = {}, {}
        for side in ("+C", "-C"):
            onset = scenario[side]
            noisy = u(scenario["name"], side, round(c, 10)) < scenario["noise"]
            broken = c >= onset or noisy
            trips = c >= onset * scenario["trip_frac"] or (noisy and scenario["noise_trips"])
            reasons[side] = ["repetition"] if broken else []
            stats[side] = {"repeated": 30 if trips else 0, "unfinished": 0, "role_leaks": 0}
        run_dir = root / "outputs" / f"run_{c:.10f}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir, {"breakdown_reasons": reasons, "demo_stats": stats}
    return adopted


def run(mod, scenario, refine):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "outputs").mkdir()
        mod.ROOT = root
        mod.adopted_rung = make_fake(root, scenario)
        args = argparse.Namespace(method="m", seed=0, walk_id="w", refine_around_cstar=refine, limit=100,
                                  status="RESULT", dry_run=False, model="x", max_new_tokens=512, device="cpu",
                                  dtype="float32", n_pairs=2, batch_size=2, extract_batch_size=2, max_length=128)
        try:
            mod.walk(args)
            outcome = "complete"
        except RuntimeError as error:
            outcome = f"raise:{error}"
        cert = json.loads((root / "outputs" / "walk_m_s0.json").read_text())
    return outcome, cert


old = load("walk_old", "/tmp/walk_old.py")
new = load("walk_new", "scripts/walk.py")
rng = random.Random(0)
scenarios = [
    {"name": "clean", "+C": 2.0, "-C": 8.0, "noise": 0.0, "trip_frac": 1.0, "noise_trips": False},
    {"name": "early_trip", "+C": 4.0, "-C": 4.0, "noise": 0.0, "trip_frac": 0.7, "noise_trips": False},
    {"name": "trip_from_start", "+C": 1.0, "-C": 3.0, "noise": 0.0, "trip_frac": 0.0, "noise_trips": False},
    {"name": "never_breaks", "+C": 1e9, "-C": 1e9, "noise": 0.0, "trip_frac": 1.0, "noise_trips": False},
    {"name": "one_side_never", "+C": 1.0, "-C": 1e9, "noise": 0.0, "trip_frac": 1.0, "noise_trips": False},
]
for i in range(40):
    scenarios.append({"name": f"rand{i}", "+C": 2 ** rng.uniform(-4, 10), "-C": 2 ** rng.uniform(-4, 10),
                      "noise": rng.choice([0.0, 0.1, 0.3]), "trip_frac": rng.choice([0.5, 0.9, 1.0, 1.1]),
                      "noise_trips": rng.random() < 0.5})
n_same = 0
for scenario in scenarios:
    for refine in (False, True):
        a, b = run(old, scenario, refine), run(new, scenario, refine)
        same = a == b
        n_same += same
        print(f"{scenario['name']:16s} refine={refine!s:5s} same={same} outcome={a[0][:40]} rungs={len(a[1]['rungs'])} c_star={a[1].get('c_star')}")
        assert same, (scenario, refine)
print(f"SHOULD all identical: {n_same}/{2 * len(scenarios)} identical")
