"""Saved-source-only single-concept feasibility check. No model/API calls."""
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path[:0] = [str(REPO / 'scripts/scratch'), str(REPO / 'scripts'), str(REPO / 'src')]
import torch
import j_lens_additive_concepts as additive


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stats(values):
    return dict(min=min(values), median=statistics.median(values), max=max(values))


def cosine(a, b):
    return float(torch.nn.functional.cosine_similarity(a.double(), b.double(), dim=0))


source, old = additive.source_contrast()  # Actual pinned hash + independent FP64 weights @ rows checks.
c = source['construction']
assert source['settings']['layer'] == 17 and len(c['source_states']) == 102
states = torch.tensor(c['source_states'], dtype=torch.bfloat16)
assert states.shape == (102, 2560) and torch.isfinite(states).all()
p, n = [torch.tensor(c['components'][k]['component'], dtype=torch.float32) for k in ('positive', 'negative')]
v = p * old.norm() / p.norm()
assert torch.isfinite(v).all() and v.norm() > 0
full = torch.tensor(c['full_signals'], dtype=torch.float32)
# Verify mean subtraction and record ordering, rather than trusting field labels alone.
assert [r['concept'] for r in c['source_records'][:2]] == ['sycophancy', 'skepticism']
original_states = torch.tensor(c['source_states'], dtype=torch.float32)
mean = original_states[2:].mean(0)
torch.testing.assert_close(mean, torch.tensor(c['baseline_mean']), atol=1e-6, rtol=1e-5)
torch.testing.assert_close(full, original_states[:2]-mean, atol=1e-6, rtol=1e-5)
reconstructions = {}
for name in ('positive', 'negative'):
    part = c['components'][name]
    weights = torch.tensor(part['weights'], dtype=torch.float64)
    rows = torch.tensor(part['dictionary_rows'], dtype=torch.float64)
    if len(weights) != len(rows):
        weights = weights[part['nonzero_ids']]
    independent = weights @ rows
    component = torch.tensor(part['component'], dtype=torch.float64)
    torch.testing.assert_close(component, independent, atol=1e-5, rtol=1e-4)
    reconstructions[name] = dict(max_absolute_error=float((component-independent).abs().max()), component_norm=float(component.norm()), nonzero_weights=int((weights != 0).sum()))
# Prior named norm-matched and own-full gap operators use normalized basis differences.
directions = {'named_raw_GP_difference_alpha1_2_4': old,
              'named_positive_GP_component': p, 'named_negative_GP_component': n,
              'named_GP_unit_basis_gap': torch.tensor(c['basis'])[0]-torch.tensor(c['basis'])[1],
              'named_full_unit_basis_gap': torch.tensor(c['full_basis'])[0]-torch.tensor(c['full_basis'])[1],
              'named_full_raw_difference_reference': full[0]-full[1]}
comparisons = {name: dict(cosine_to_proposal=cosine(v, direction), norm=float(direction.norm()), source=str(additive.SOURCE), source_sha256=sha(additive.SOURCE)) for name, direction in directions.items()}
prior_sources = {}
for name, dirname, expected_sha, field in (
    ('persona_GP_v15', 'j-lens-persona-components-source-v15', 'db8d2ebf1fb4370888aac03583789930a8f42d22113898994c3661a61dfb7d40', 'gp_component'),
    ('persona_full_v16', 'j-lens-persona-full-components-source-v16', 'aa054e789557b9ca4c79c52c93dd3ef8880212f1793c786932a91145bfc4321d', 'full_signal'),
):
    path = Path('outputs/experiments')/dirname/'extraction/metadata.json'
    assert sha(path) == expected_sha
    meta = json.loads(path.read_text())
    parts = torch.tensor([meta['layers']['17']['decomposition'][key][field] for key in ('positive', 'negative')])
    basis = parts / parts.norm(dim=1, keepdim=True)
    prior_sources[name] = dict(path=str(path), sha256=expected_sha, source_prompts=meta['source_prompts'], source_ids=meta['source_ids'], field=field, layer=17)
    for suffix, direction in [('positive', parts[0]), ('negative', parts[1]), ('unit_basis_gap', basis[0]-basis[1])]:
        comparisons[name+'_'+suffix] = dict(cosine_to_proposal=cosine(v, direction), norm=float(direction.norm()), source=str(path), source_sha256=expected_sha)
rows = []
for side, sign in (('+C', 1), ('-C', -1)):
    for index, h in enumerate(states):
        after, metrics = additive.additive_patch(h[None], v, sign*4)
        prior_after, prior_metrics = additive.additive_patch(h[None], old, sign*4)
        independent = (h.double()+(sign*4*v).to(h).double()).to(h)
        assert torch.equal(after[0], independent)
        actual = after[0].float()-h.float()
        prior_actual = prior_after[0].float()-h.float()
        assert torch.equal(additive.additive_patch(h[None], v, 0)[0], h[None])
        rows.append(dict(side=side, source_index=index, concept=c['source_records'][index]['concept'], **metrics,
                         prior_actual_norm=prior_metrics['actual_norm'], actual_update_difference_norm=float((actual-prior_actual).norm()),
                         actual_update_cosine_to_prior=cosine(actual, prior_actual), identical_to_prior=torch.equal(after, prior_after)))
summary = {}
for side in ('+C', '-C'):
    group = [r for r in rows if r['side'] == side]
    summary[side] = dict(cases=len(group), zero_updates=sum(r['actual_norm']==0 for r in group),
        identical_to_prior=sum(r['identical_to_prior'] for r in group), requested_norm=group[0]['desired_norm'],
        delivered_norm=stats([r['actual_norm'] for r in group]), norm_error=stats([r['norm_error'] for r in group]),
        max_relative_norm_error=max(r['norm_error']/r['desired_norm'] for r in group),
        actual_update_difference_norm=stats([r['actual_update_difference_norm'] for r in group]),
        actual_update_cosine_to_prior=stats([r['actual_update_cosine_to_prior'] for r in group]),
        cosine_to_requested=stats([r['direction_cosine'] for r in group]))
result = dict(scope='102 saved named source states only, not DEV delivery or behavioral proof', alpha=4,
    source_path=str(additive.SOURCE), source_sha256=sha(additive.SOURCE), model_revision=source['model_revision'],
    layer=17, source_revision=source['source_revision'], source_tokenizer_sha256=c['source_tokenizer_sha256'],
    inventory_source_sha256=c['inventory']['source_sha256'], lens_sha256=c['lens_sha256'],
    additive_path=additive.__file__, additive_sha256=sha(additive.__file__), script_sha256=sha(__file__),
    torch_version=torch.__version__, dtype='bfloat16', reconstruction=reconstructions,
    raw_prior_norm=float(old.norm()), positive_GP_norm=float(p.norm()), proposal_norm=float(v.norm()),
    proposal_vector=v.tolist(), comparison_directions=comparisons, prior_sources=prior_sources, signs=summary, rows=rows,
    limitation='Named unit-basis gaps are fixed axes of state-dependent previously tested operators, not their full per-step updates. Named raw full difference is a reference, not claimed an executed additive direction. Persona GP-v15/full-v16 metadata is hash-verified against the previously tested bridge; their unit-basis gaps are axes, not full state-dependent updates. No exhaustive novelty claim.')
(ROOT/'check.json').write_text(json.dumps(result, indent=2)+'\n')
print('SOURCE_RECONSTRUCTION_PASS', json.dumps(reconstructions))
print('DIRECTION_COMPARISONS', json.dumps(comparisons))
print('SINGLE_CONCEPT_SOURCE_BF16_PASS', json.dumps(summary))
