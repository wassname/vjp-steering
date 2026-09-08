"""Explicit compressed-artifact verification of fixed layer18 mediation; no calls."""
import argparse
import csv
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
sys.path[:0] = ['scripts/scratch', 'scripts', 'src']
import torch
import j_lens_layer18_mediation as run
import judge
import export

parser = argparse.ArgumentParser()
parser.add_argument('--generation', type=Path, required=True, help='Explicit published .json.gz path')
parser.add_argument('--generation-only', action='store_true')
args = parser.parse_args()
assert args.generation.suffixes[-2:] == ['.json', '.gz']
root = run.ROOT
packed = args.generation.read_bytes()
raw = gzip.decompress(packed)
publication = run.load(root/'publication.json')
assert hashlib.sha256(raw).hexdigest() == publication['raw_sha256']
assert hashlib.sha256(packed).hexdigest() == publication['gzip_sha256']
data = json.loads(raw)
del raw, packed
reference, factorial = run.load(run.REFERENCE), run.load(run.DONOR_REFERENCE)
preflight = run.load(root/'preflight.json')
assert data['api']['sha256'] == run.API_HASHES
assert data['model_revision'] == run.gap.REVISION
assert data['source_hashes'] == run.HASHES
assert hashlib.sha256(subprocess.check_output(['git', 'show', data['source_revision']+':scripts/scratch/j_lens_layer18_mediation.py'])).hexdigest() == data['implementation_sha256'] == preflight['implementation_sha256']
assert all(run.gap.sha(p) == h for p, h in preflight['protected_hashes'].items())
rows = run.judge_rows(data)
activity = []
text = ['# Complete layer18 mediation response and judgment audit',
        'All24 full responses,18 judgments. Diagnostic only; no DEV point or historical score change.',
        'Full raw generation including first logits is published losslessly as generation.json.gz.']
for scenario in run.gap.SCENARIOS:
    rs = {r['condition']: r for r in data['records'] if r['scenario'] == scenario}
    old = {r['condition']: r for r in reference['records'] if r['scenario'] == scenario}
    neither = next(r for r in factorial['records'] if r['scenario'] == scenario and r['condition'] == 'neither')
    prior = {}
    text += ['## '+scenario]
    for arm in run.ARMS:
        r = rs[arm]
        run.check_arm(arm, r, prior, old, neither)
        assert set(r['hook_calls'].values()) == {1}
        for key in ('h17_nonfinal_exact', 'block18_input_exact', 'mixer_nonfinal_exact', 'cache_at_hook_unchanged',
                    'cache_written_before_hook', 'positions_masks_unchanged', 'residual_exact', 'block19_input_exact',
                    'cache_preserved_through_prefill', 'inputs_unchanged', 'gates_pass'):
            assert r[key]
        x = torch.tensor(r['h17_after'], dtype=torch.bfloat16)
        m = torch.tensor(r['mixer_after'], dtype=torch.bfloat16)
        residual = torch.tensor(r['receiving_residual'], dtype=torch.bfloat16)
        mlp = torch.tensor(r['mlp18_output'], dtype=torch.bfloat16)
        assert torch.equal(x+m, residual)
        assert (residual+mlp).float().tolist() == r['final_states']['18']
        measured = float((torch.tensor(r['mixer_after'], dtype=torch.float64)-torch.tensor(r['mixer_before'], dtype=torch.float64)).norm())
        assert abs(measured-r['mixer_update_norm']) < 1e-12
        if arm.endswith('cross'):
            base = rs[arm[0]+'0']
            endpoint = rs[('D' if arm[0] == 'B' else 'B')+'0']
            logits, baseline = (torch.tensor(t['first_logits'], dtype=torch.float64) for t in (r, base))
            lp, lq = logits.log_softmax(-1), baseline.log_softmax(-1)
            item = {'scenario': scenario, 'arm': arm, 'mixer_norm': measured,
                'h18_endpoint_distance': 0., 'cache_through18_same_context_exact': r['prefill_cache_through18_sha256'] == base['prefill_cache_through18_sha256'],
                'full_prefill_cache_equal_to_same_context': r['full_prefill_cache_sha256'] == base['full_prefill_cache_sha256'],
                'decode_cache_equal_to_same_context': r['final_decode_cache_sha256'] == base['final_decode_cache_sha256'],
                'same_context_text_identical': r['text'] == base['text'],
                'same_context_ids_identical': r['generated_ids'] == base['generated_ids'],
                'first_logit_max_abs_change': float((logits-baseline).abs().max()),
                'first_token_KL_from_same_context': float((lq.exp()*(lq-lp)).sum()),
                'h19_distance_from_opposite_endpoint': float((torch.tensor(r['final_states']['19'], dtype=torch.float64)-torch.tensor(endpoint['final_states']['19'], dtype=torch.float64)).norm()),
                'h31_distance_from_opposite_endpoint': float((torch.tensor(r['final_states']['31'], dtype=torch.float64)-torch.tensor(endpoint['final_states']['31'], dtype=torch.float64)).norm())}
            assert item['cache_through18_same_context_exact']
            activity.append(item)
        prior[arm] = r
        text += ['### '+arm, '```text', r['rendered'], '```', r['text'], 'Health: '+json.dumps(r['health']),
                 'Hook calls: '+json.dumps(r['hook_calls']), 'Mixer update norm: '+str(measured)]
summary = {'responses': len(data['records']), 'real_gates': True, 'source_hashes': data['source_hashes'],
    'api_hashes': data['api']['sha256'], 'protected_files': len(preflight['protected_hashes']),
    'self_identity_pairs': 6, 'cross_endpoints_exact': 6, 'activity': activity, 'runtime': data['runtime'],
    'published_generation': str(args.generation), 'generation_sha256': publication['raw_sha256']}
if args.generation_only:
    run.save(root/'generation-check.json', summary)
    print('LAYER18_GENERATION_CHECK_PASS', json.dumps(summary))
    raise SystemExit(0)

js = [json.loads(line) for line in (root/'judgments.jsonl').read_text().splitlines()]
transport = [json.loads(line) for line in (root/'judge-transport.jsonl').read_text().splitlines()]
assert len(js) == len(transport) == 18
assert len({(j['vignette'], j['condition'], j['order']) for j in js}) == 18
cells, pairs, repeated = [], [], []
old_js = [json.loads(line) for line in (run.donor.ROOT/'judgments.jsonl').read_text().splitlines()]
api_cost = Decimal('0')
for r in rows:
    pair = []
    text += ['## Judgments: '+r['vignette']+' / '+r['condition'], 'Baseline full response:', r['bare'], 'Treatment full response:', r['steered']]
    for order in ('AB', 'BA'):
        j = next(j for j in js if (j['vignette'], j['condition'], j['order']) == (r['vignette'], r['condition'], order))
        t = next(t for t in transport if (t['scenario'], t['condition'], t['order']) == (r['vignette'], r['condition'], order))
        assert j['prompt'] == judge.judge_prompt(r, order) and j['cache_key'] == judge.cache_key(r, order, 0)
        assert j['model'] == judge.MODEL and j['rubric_version'] == judge.RUBRIC
        raw_score = json.loads(j['raw'])
        assert all(j['judgment'][k] == v for k, v in raw_score.items())
        assert j['raw_attempts'] == [j['raw']]
        assert t['response']['choices'][0]['message']['content'] == j['raw']
        assert t['request'] == {'model': judge.MODEL, 'messages': [{'role': 'user', 'content': j['prompt']}],
            'temperature': .7, 'max_tokens': 1024, 'response_format': judge.FORMAT,
            'extra_body': {'reasoning': {'enabled': False}, 'provider': judge.provider_route(0)}}
        b, s = ('A', 'B') if order == 'AB' else ('B', 'A')
        effect = raw_score['on_axis_'+b] - raw_score['on_axis_'+s]
        assert abs(effect-j['exported_effect']) < 1e-12
        assert abs(effect-export.signed_axis_effect('-C', [export.score_cell(j)])) < 1e-12
        item = {'scenario': r['vignette'], 'pair': r['condition'], 'order': order, 'effect': effect,
            'baseline_on': raw_score['on_axis_'+b], 'treated_on': raw_score['on_axis_'+s],
            'damage_difference': raw_score['off_axis_'+s]-raw_score['off_axis_'+b],
            'identical_text': r['bare'] == r['steered'], 'cache_key': j['cache_key']}
        cells.append(item); pair.append(effect)
        api_cost += Decimal(str(t['response']['usage']['cost']))
        if r['condition'] == 'sensitivity':
            p = next(p for p in old_js if (p['vignette'], p['condition'], p['order']) == (r['vignette'], 'neither', order))
            assert p['prompt'] == j['prompt'], 'Repeated sensitivity pair changed request content'
            previous = json.loads(p['raw'])
            baseline_change = raw_score['on_axis_'+b]-previous['on_axis_'+b]
            treatment_change = previous['on_axis_'+s]-raw_score['on_axis_'+s]
            old_effect = previous['on_axis_'+b]-previous['on_axis_'+s]
            assert abs(effect-old_effect-baseline_change-treatment_change) < 1e-12
            repeated.append({'scenario': r['vignette'], 'order': order, 'old_effect': old_effect,
                'new_effect': effect, 'baseline_rescoring_contribution': baseline_change,
                'unchanged_treatment_rescoring_contribution': treatment_change})
        text += ['### '+order, 'Mapped: '+json.dumps(item), 'Complete raw request:', '```text', j['prompt'], '```',
                 'Complete raw judgment:', '```json', j['raw'], '```']
    pairs.append({'scenario': r['vignette'], 'pair': r['condition'], 'AB': pair[0], 'BA': pair[1],
                  'mean': statistics.mean(pair), 'strict_reversal': pair[0]*pair[1] < 0})
# Baseline D0 is itself also scored as treatment in sensitivity; preserve within-run scoring disagreements.
within_run = []
for scenario in run.gap.SCENARIOS:
    for order in ('AB', 'BA'):
        sensitivity = next(c for c in cells if (c['scenario'], c['pair'], c['order']) == (scenario, 'sensitivity', order))
        necessity = next(c for c in cells if (c['scenario'], c['pair'], c['order']) == (scenario, 'necessity', order))
        within_run.append({'scenario': scenario, 'order': order, 'D0_as_treatment': sensitivity['treated_on'],
                           'D0_as_baseline': necessity['baseline_on'],
                           'same_response_score_change': necessity['baseline_on']-sensitivity['treated_on']})
summary.update(judgments=18, paired_scores=pairs, judge_cost_usd=str(api_cost),
    judgments_sha256=run.gap.sha(root/'judgments.jsonl'), prior_sensitivity_rescoring=repeated,
    same_run_D0_rescoring=within_run, identical_answer_cells=[c for c in cells if c['identical_text']])
for name, records in (('scores', cells), ('pairs', pairs), ('activity', activity), ('repeated-sensitivity', repeated), ('within-run-rescoring', within_run)):
    with (root/(name+'.csv')).open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
run.save(root/'audit.json', summary)
(root/'complete-response-audit.md').write_text('\n\n'.join(text)+'\n')
print('LAYER18_AUDIT_PASS', json.dumps(summary))
