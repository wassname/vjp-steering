"""Shared production helper for vendor-normalized J-lens readout.

Exact Qwen3_5RMSNorm semantics: x * rsqrt(mean(x^2)+eps) * (1+weight), float32 compute.
Used by scripts/reproduce_paper_j_lens.py and tests.
"""
import torch

def qwen_rmsnorm(x: torch.Tensor, weight: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    # Mirrors transformers.models.qwen3_5.modeling_qwen3_5.Qwen3_5RMSNorm
    normed = x.float() * torch.rsqrt(x.float().pow(2).mean(-1, keepdim=True) + eps)
    out = normed * (1.0 + weight.float())
    return out.type_as(x)

def vendor_lens_scores(hidden: torch.Tensor, J: torch.Tensor, norm_weight: torch.Tensor, lm_head_weight: torch.Tensor, candidate_ids: list[int], eps: float = 1e-6, dtype=torch.bfloat16) -> torch.Tensor:
    """Production vendor readout: W_U @ norm(J @ hidden) for candidate vocab subset."""
    # hidden: [d_model] float32, J: [d_model, d_model], norm_weight: [d_model], lm_head_weight: [vocab, d_model]
    transported = (J @ hidden.float()).to(dtype).float()  # bf16 roundtrip as in production
    # Need to handle norm on correct device/dtype; assume weight on same device as hidden
    normed = qwen_rmsnorm(torch.tensor(transported, dtype=dtype), norm_weight, eps)
    # lm_head: vocab x d_model @ d_model -> vocab, then select candidates
    # For efficiency, only compute candidate rows: candidate_lm_rows @ normed
    candidate_rows = lm_head_weight[candidate_ids].float()  # [n_cand, d_model]
    scores = candidate_rows @ normed.float()
    return scores
