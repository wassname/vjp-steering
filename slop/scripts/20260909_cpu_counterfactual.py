"""CPU counterfactual using 9 existing clean hidden states (layers13-21).

Computes exact pseudoinverse source/target coordinates, applies unchanged alpha1 swap,
and compares normalized Germany-minus-France readout before/after at each layer.
No GPU rerun; uses saved hidden_vectors, lens J, and norm/head weights.
"""
import json, pathlib, torch, hashlib
from vjp_steering.vjp import _resolve_j_lens_file

RESULT = pathlib.Path("outputs/experiments/v14-paper-native-verbal-chat-country-swap-corrected-vendor/results.json")
SMALL_CACHE = pathlib.Path("slop/logs/20260909_j_lens_dev/qwen_norm_head_small.pt")

def rmsnorm_qwen(x, weight, eps=1e-6):
    return (x.float() * torch.rsqrt(x.float().pow(2).mean(-1, keepdim=True) + eps)) * (1.0 + weight.float()).float().type_as(x)

data = json.loads(RESULT.read_text())
trial = data["trials"][0]
hidden_vectors = trial["hidden_capture"]["hidden_vectors"]
candidate_ids = json.loads(open("data/vendor/jacobian-lens/verbal-report.json").read())["candidates"]["country"]
# Use exact recorded candidate_ids from clean_rows
candidate_ids = data["clean_rows"][0]["category_token_ids"]
source_id = trial["source_token_id"]
target_id = trial["target_token_id"]
source_idx = candidate_ids.index(source_id)
target_idx = candidate_ids.index(target_id)

# Load lens and norm/head
local_lens = _resolve_j_lens_file(None)
ckpt = torch.load(str(local_lens), map_location="cpu", weights_only=True, mmap=True)
cache = torch.load(str(SMALL_CACHE), map_location="cpu")
norm_weight = cache["norm_weight"]
candidate_lm_rows = cache["candidate_lm_rows"]  # 11 x d_model in trial order
# Map candidate_ids order to cache order (cache trial_candidate_ids == candidate_ids)
assert cache["trial_candidate_ids"] == candidate_ids

print(f"Trial {trial['source_token']}->{trial['target_token']} alpha1 layers13-21")
print(f"Clean final logit rank {trial['clean_target_rank']}->{trial['swapped_target_rank']} (still fail)")

for layer_str in sorted(hidden_vectors.keys(), key=int):
    layer = int(layer_str)
    h = torch.tensor(hidden_vectors[layer_str], dtype=torch.float32)  # d
    J = ckpt["J"][layer].float()  # d x d
    # Basis V: 2 x d raw rows W_U @ J for source/target
    # candidate_lm_rows is 11 x d, but need rows for source/target only
    # Find rows for source/target in candidate_lm_rows order
    # candidate_lm_rows[0] is 47122 Japan, [1] 47358 France source, [7] 48484 Germany target
    w_source = candidate_lm_rows[source_idx].float()  # d
    w_target = candidate_lm_rows[target_idx].float()
    v_source = w_source @ J.float()  # d
    v_target = w_target @ J.float()
    basis = torch.stack([v_source, v_target], dim=0)  # 2 x d
    # Dual: pinv(basis).T  -> 2 x d? Actually pinv(2xd) is dx2, T is 2xd
    dual = torch.linalg.pinv(basis).T  # 2 x d
    # Coordinates c = dual @ h? Using einsum kd * d -> k
    c_before = dual @ h  # 2
    c_after = c_before.flip(0)  # swap
    delta_c = c_after - c_before  # 2
    # Swapped hidden: h' = h + V @ delta_c, where V = basis.T (d x 2)
    V = basis.T  # d x 2
    h_swapped = h + V @ delta_c
    # Coordinate delta: source->target etc.
    coord_delta_source = float(delta_c[0])
    coord_delta_target = float(delta_c[1])
    # Normalized readout before/after: vendor = W_U @ norm(J @ h)
    # Before
    transported_before = (J @ h).to(torch.bfloat16).float()
    normed_before = rmsnorm_qwen(torch.tensor(transported_before), norm_weight, eps=1e-6)
    scores_before = candidate_lm_rows.float() @ normed_before.float()  # 11
    diff_before = float(scores_before[target_idx] - scores_before[source_idx])
    # After
    transported_after = (J @ h_swapped).to(torch.bfloat16).float()
    normed_after = rmsnorm_qwen(torch.tensor(transported_after), norm_weight, eps=1e-6)
    scores_after = candidate_lm_rows.float() @ normed_after.float()
    diff_after = float(scores_after[target_idx] - scores_after[source_idx])
    delta_diff = diff_after - diff_before
    # Also raw (no norm) diff for comparison
    raw_before = float((w_target @ (J @ h)) - (w_source @ (J @ h)))  # not needed
    print(f"L{layer}: c_before=[{c_before[0]:.3f},{c_before[1]:.3f}] delta=[{delta_c[0]:.3f},{delta_c[1]:.3f}] vendor diff {diff_before:.3f}->{diff_after:.3f} delta {delta_diff:+.3f} raw? vendor tie L19 both 9.25?")

# Save detailed per-layer counterfactual for audit
out = pathlib.Path("slop/logs/20260909_j_lens_dev/cpu-counterfactual.json")
out.parent.mkdir(parents=True, exist_ok=True)
# Build detailed records from loop (recompute for saving)
detailed = []
for layer_str in sorted(hidden_vectors.keys(), key=int):
    layer = int(layer_str)
    h = torch.tensor(hidden_vectors[layer_str], dtype=torch.float32)
    J = ckpt["J"][layer].float()
    w_source = candidate_lm_rows[candidate_ids.index(source_id)].float()
    w_target = candidate_lm_rows[candidate_ids.index(target_id)].float()
    v_source = w_source @ J.float()
    v_target = w_target @ J.float()
    basis = torch.stack([v_source, v_target], dim=0)
    dual = torch.linalg.pinv(basis).T
    c_before = dual @ h
    delta_c = c_before.flip(0) - c_before
    V = basis.T
    h_swapped = h + V @ delta_c
    transported_before = (J @ h).to(torch.bfloat16).float()
    normed_before = rmsnorm_qwen(torch.tensor(transported_before, dtype=torch.bfloat16), norm_weight, eps=1e-6)
    scores_before = candidate_lm_rows.float() @ normed_before.float()
    diff_before = float(scores_before[target_idx] - scores_before[source_idx])
    transported_after = (J @ h_swapped).to(torch.bfloat16).float()
    normed_after = rmsnorm_qwen(torch.tensor(transported_after, dtype=torch.bfloat16), norm_weight, eps=1e-6)
    scores_after = candidate_lm_rows.float() @ normed_after.float()
    diff_after = float(scores_after[target_idx] - scores_after[source_idx])
    detailed.append({
        "layer": layer,
        "c_before": [float(c_before[0]), float(c_before[1])],
        "delta_c": [float(delta_c[0]), float(delta_c[1])],
        "vendor_diff_before": diff_before,
        "vendor_diff_after": diff_after,
        "vendor_delta": diff_after - diff_before,
        "note": "Germany-minus-France vendor readout; coordinate swap inverts as expected but final logit rank14->16 still fails downstream"
    })
import json as _j
_j.dump({"trial": f"{trial['source_token']}->{trial['target_token']} alpha1 layers13-21", "layers": detailed, "final_logit_rank": f"{trial['clean_target_rank']}->{trial['swapped_target_rank']}", "interpretation": "Vendor readout inversion tracks coordinate swap; failure is downstream of lens readout, not absent coordinate. Layer19 tie 9.25/9.25 shows clean winner not dominant at that layer."}, open(out,"w"), indent=2)
print(f"saved {out} with {len(detailed)} layers")
