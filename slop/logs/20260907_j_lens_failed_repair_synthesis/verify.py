"""Offline evidence inventory and candidate geometry; no model/API calls or writes to inputs."""
import hashlib
import json
from pathlib import Path
from statistics import mean
import torch

ROOT = Path('slop/logs/20260907_j_lens_failed_repair_synthesis')
LOGS = Path('slop/logs')
def path(name):
    return LOGS / ('20260907_j_lens_' + name)
def load(p):
    return json.loads(p.read_text())
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def decomposition(new, old, order):
    b, t = ('A', 'B') if order == 'AB' else ('B', 'A')
    baseline = new['on_axis_' + b] - old['on_axis_' + b]
    steered = old['on_axis_' + t] - new['on_axis_' + t]
    effect = new['on_axis_' + b] - new['on_axis_' + t]
    old_effect = old['on_axis_' + b] - old['on_axis_' + t]
    assert abs(effect - old_effect - baseline - steered) < 1e-12
    return dict(baseline=baseline, steered=steered, change=effect-old_effect, effect=effect)

# Synthetic AB/BA baseline-only, treatment-only, identity controls.
for order in ('AB', 'BA'):
    b, t = ('A', 'B') if order == 'AB' else ('B', 'A')
    zero = {'on_axis_A': 0., 'on_axis_B': 0.}
    assert decomposition(zero, zero, order)['change'] == 0
    for field, expected in ((b, 1.), (t, -1.)):
        changed = dict(zero, **{'on_axis_' + field: 1.})
        assert decomposition(changed, zero, order)['change'] == expected

protected = [Path(p) for p in ('results/plot.png', 'results/plot_pareto.png', 'results/index.md',
    'results/index.html', 'data/results.csv', 'scripts/scratch/j_lens_transfer_probe.py',
    'scripts/scratch/j_lens_additive_concepts.py')]
protected += [path(n)/'generation.json' for n in ('transfer_probe', 'named_concepts', 'single_concept', 'projection_removal')]
protected += [path(n)/'judgments.jsonl' for n in ('single_concept', 'projection_removal')]
protected += [path('projection_removal')/'budget.json']
before = {str(p): sha(p) for p in protected}
projection = load(path('projection_removal')/'generation.json')
old = load(path('single_concept')/'generation.json')
assert projection['reused_records'] == old['reused_records']
new_j = [json.loads(x) for x in (path('projection_removal')/'judgments.jsonl').read_text().splitlines()]
old_j = {(x['vignette'], x['order']): x for x in map(json.loads,
    (path('single_concept')/'judgments.jsonl').read_text().splitlines()) if x['side']=='-C'}
assert len(new_j) == len({(j['vignette'],j['order']) for j in new_j}) == 30
cells = []
for j in new_j:
    old_row = old_j[j['vignette'],j['order']]
    n, p = json.loads(j['raw']), json.loads(old_row['raw'])
    assert all(j['judgment'][k] == v for k,v in n.items())
    assert all(old_row['judgment'][k] == v for k,v in p.items())
    cells.append({'scenario':j['vignette'], 'order':j['order'], **decomposition(n,p,j['order'])})
summary = {k:mean(c[k] for c in cells) for k in ('baseline','steered','change','effect')}

# Actual frozen current direction and OLD task-matched donor states, not fresh inference.
transfer = load(path('transfer_probe')/'generation.json')
assert transfer['model_revision'] == projection['model_revision']
u = torch.tensor(projection['contrast'], dtype=torch.float64)
u /= u.norm()
assert abs(float(u.norm())-1) < 1e-12
geometry = []
for scenario in sorted({r['scenario'] for r in transfer['records']}):
    records = {r['condition']: r for r in transfer['records'] if r['scenario']==scenario}
    assert set(records) == {'bare','direct_minus','identity_minus','donor_identity_minus','full_minus','projected_minus','gap_minus'}
    bare, donor = records['bare'], records['direct_minus']
    h_b = torch.tensor(bare['patch']['after'], dtype=torch.float64)
    h_d = torch.tensor(donor['patch']['after'], dtype=torch.float64)
    delta = h_d - h_b
    p = u * (u @ delta)
    q = delta - p
    assert torch.allclose(p+q,delta,atol=1e-12,rtol=0)
    assert abs(float(p @ q)) < 1e-12
    assert records['full_minus']['patch']['after'] == donor['patch']['after']
    assert records['full_minus']['input_ids'] == bare['input_ids']
    assert records['donor_identity_minus']['input_ids'] == donor['input_ids']
    assert records['donor_identity_minus']['identity_exact']
    assert donor['input_ids'] != bare['input_ids']
    # Saved-state BF16 feasibility only; no replay of downstream computation.
    u32 = u.float()
    hb32, hd32 = h_b.float(), h_d.float()
    pd32 = u32 * (u32 @ (hd32-hb32))
    parallel_only = (hb32+pd32).bfloat16().double()
    complement_only = (hd32-pd32).bfloat16().double()
    assert not torch.equal(parallel_only,h_b) and not torch.equal(complement_only,h_d)
    geometry.append({'scenario':scenario, 'bare_coordinate':float(u@h_b), 'donor_coordinate':float(u@h_d),
        'task_delta_coordinate':float(u@delta), 'task_delta_norm':float(delta.norm()),
        'parallel_norm':float(p.norm()), 'complement_norm':float(q.norm()),
        'parallel_energy_fraction':float(p.square().sum()/delta.square().sum()),
        'BF16_parallel_only_difference_from_bare':float((parallel_only-h_b).norm()),
        'BF16_complement_only_difference_from_donor':float((complement_only-h_d).norm()),
        'BF16_parallel_arm_error':float((parallel_only-(h_b+p)).norm()),
        'BF16_complement_arm_error':float((complement_only-(h_d-p)).norm()),
        'bare_tokens':len(bare['input_ids']), 'donor_tokens':len(donor['input_ids']),
        'conditions_in_donor_context':[c for c,r in records.items() if r['input_ids']==donor['input_ids']],
        'full_donor_copy_exact':True, 'donor_identity_exact':True})

# Schema audit: confirms what inspected records save, not global absence across all disks.
state_inventory = {
    'transfer_record_keys':sorted(transfer['records'][0]),
    'transfer_saved_final_layers':sorted(transfer['records'][0]['final_states'],key=int),
    'transfer_first_token_keys':sorted(transfer['records'][0]['first_token']),
    'projection_record_keys':sorted(projection['records'][0]),
    'projection_measurement_keys':sorted(projection['records'][0]['measurements'][0]),
    'no_serialized_KV_or_recurrent_state_in_these_schemas':True,
}
for r in transfer['records'] + projection['records']:
    assert not any(k in r for k in ('past_key_values','cache','recurrent_states','conv_states','key_cache','value_cache'))
steps = [m for r in projection['records'] for m in r['measurements']]
assert len(steps)==1069 and all(m['actual_norm']>0 and m['next_block_exact'] and m['nonfinal_exact'] for m in steps)
assert before == {str(p):sha(p) for p in protected}
budget = load(path('projection_removal')/'budget.json')
assert budget['unreserved_usd'] == 2.01988872744 and budget['outstanding_reserves_released_usd']==0
cost = {'unreserved_usd':budget['unreserved_usd'], 'new_reservation_usd':0,
    'proposal_only_cap_usd':1.20, 'timeout_seconds':360, 'GPU_runtime_upper_estimate_usd':360*.001097,
    'startup_and_non_GPU_allowance_usd':.70508, 'judge_allowance_usd':.10,
    'if_separately_authorized_remaining_usd':budget['unreserved_usd']-1.20,
    'invoice_is_available':False, 'generation_count':15, 'judge_count':18}
assert abs(cost['GPU_runtime_upper_estimate_usd']+cost['startup_and_non_GPU_allowance_usd']+cost['judge_allowance_usd']-1.20)<1e-12
out = dict(raw_attribution_cells=cells, raw_attribution_summary=summary, task_donor_geometry=geometry,
    schema_inventory=state_inventory, protected_hashes=before, cost_proposal=cost,
    online_treatment_calls=len(steps), goals_open=True, paid_calls=0)
(ROOT/'verification.json').write_text(json.dumps(out,indent=2)+'\n')
print('FAILED_REPAIR_SYNTHESIS_PASS',json.dumps({'raw_cells':len(cells),'attribution':summary,
    'donor_geometry':geometry,'protected_files':len(before),'online_calls':len(steps),'paid_calls':0,'cost':cost}))
