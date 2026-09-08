"""Offline publication/history checks for the bounded post-mediation synthesis.

Only verification.json is written. No model imports, network, judging or scoring edits.
"""
import gzip
import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path
import subprocess

ROOT = Path('slop/logs/20260908_j_lens_post_mediation_synthesis')
MEDIATION = Path('slop/logs/20260907_j_lens_layer18_mediation')
COMMIT = 'd16d9bfb40b6c28b176cc9dd266f081fe72574cb'
REVIEW = Path('/home/code/.pi/agent/sessions/--workspace-2026-jspace-j-steer_pub--/subagent-artifacts/outputs/696e8637-774e-49e4-9e32-739e08cbbec8/slop/reviews/j_lens_v10_layer18_interpretation.md')


def git(*args):
    return subprocess.check_output(['git', *args])


def sha(content):
    return hashlib.sha256(content).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


assert not git('diff', '--cached', '--name-only').strip(), 'unrelated staged files'
for ref in ('HEAD', 'origin/dev3'):
    subprocess.run(['git', 'merge-base', '--is-ancestor', COMMIT, ref], check=True)
assert REVIEW.read_bytes() == (ROOT/'review.md').read_bytes()
tracked = git('ls-tree', '-r', '--name-only', COMMIT, str(MEDIATION)).decode().splitlines()
assert tracked
for path in tracked:
    assert Path(path).read_bytes() == git('show', f'{COMMIT}:{path}'), path

archive = (MEDIATION/'generation.json.gz').read_bytes()
raw = gzip.decompress(archive)
assert sha(archive) == '90ba0e53f0f9122e03c74411c09b2726573f3fd68dd45333cd7df48bdacf2679'
assert sha(raw) == 'dc27049ac878f66b67aa0c1f97cc1290c96b651d35ae9e94997f30a4004e842c'
assert archive[4:8] == bytes(4)
generation = json.loads(raw)
records = {(r['scenario'], r['condition']): r for r in generation['records']}
assert len(records) == 24
scenarios = sorted({s for s, _ in records})
assert len(scenarios) == 3
activity = []
for scenario in scenarios:
    for context, opposite in [('B', 'D'), ('D', 'B')]:
        control = records[scenario, context+'0']
        identity = records[scenario, context+'-self']
        cross = records[scenario, context+'-cross']
        other = records[scenario, opposite+'0']
        for field in ('generated_ids', 'first_logits', 'final_states', 'full_prefill_cache_sha256', 'final_decode_cache_sha256'):
            assert identity[field] == control[field], (scenario, field)
        assert cross['final_states']['18'] == other['final_states']['18']
        assert cross['mixer_after'] == other['mixer_before']
        assert cross['prefill_cache_through18_sha256'] == control['prefill_cache_through18_sha256']
        assert cross['final_states']['19'] != other['final_states']['19']
        norm = math.sqrt(sum((a-b)**2 for a,b in zip(cross['mixer_after'], cross['mixer_before'])))
        assert abs(norm-cross['mixer_update_norm']) < 1e-10
        activity.append({'scenario': scenario, 'condition': context+'-cross', 'norm': norm,
                         'endpoint18_exact': True, 'diverges19': True,
                         'same_control_ids': cross['generated_ids'] == control['generated_ids']})
for r in records.values():
    assert r['gates_pass'] and r['cache_at_hook_unchanged'] and r['positions_masks_unchanged']
    assert r['h17_nonfinal_exact'] and r['mixer_nonfinal_exact']
    assert len(r['first_logits']) == 248320 and all(map(math.isfinite, r['first_logits']))
judgments = [json.loads(line) for line in (MEDIATION/'judgments.jsonl').read_text().splitlines()]
assert len(judgments) == 18
pairs = {}
for j in judgments:
    scores = json.loads(j['raw'])
    assert all(j['judgment'][key] == value for key,value in scores.items())
    assert j['side'] == '-C' and j['order'] in ('AB', 'BA')
    b,t = ('A','B') if j['order'] == 'AB' else ('B','A')
    effect = scores['on_axis_'+b] - scores['on_axis_'+t]
    assert abs(effect-j['exported_effect']) < 1e-12
    pairs.setdefault((j['vignette'], j['condition']), {})[j['order']] = effect
assert len(pairs) == 9 and all(set(p) == {'AB','BA'} for p in pairs.values())
assert sum(p['AB']*p['BA'] < 0 for p in pairs.values()) == 6

history = load('slop/logs/20260907_j_lens_native_readout_comparison/reuse.json')
for path, digest in history['hashes'].items():
    assert sha(Path(path).read_bytes()) == digest, path
assert history['span_cells'] == 12528 and history['prior_native']['successes'] == 13
assert all(count == 0 for sides in history['span_summary']['eligibility'].values() for count in sides.values())
persona = []
for version in ('components-source-v13', 'components-source-v15', 'full-components-source-v16'):
    path = Path('outputs/experiments/j-lens-persona-'+version+'/extraction/metadata.json')
    meta = load(path)
    persona.append({'path': str(path), 'sha256': sha(path.read_bytes()),
                    **{k: meta[k] for k in ('operator', 'representation_source', 'source_fit_count',
                       'source_holdout_count', 'extraction_mask', 'application_mask', 'model_revision')},
                    'instructions': {k:v for k,v in meta['spec'].items() if k.endswith('instruction')}})
preflight = load(MEDIATION/'preflight.json')
protected = preflight['protected_hashes']
for path, digest in protected.items():
    assert sha(Path(path).read_bytes()) == digest, path
budget = load(MEDIATION/'budget.json')
assert budget['unreserved_usd'] == '5.72509672744' and budget['allocation_retained']
assert Decimal(budget['metered_Modal_usd']) + Decimal(budget['judge_usd']) == Decimal('0.19603838')

out = {'evidence_commit': COMMIT, 'present_in_HEAD_and_origin_dev3': True,
       'committed_mediation_files_exact': len(tracked), 'review_source': str(REVIEW),
       'review_sha256': sha(REVIEW.read_bytes()), 'published_review_exact': True,
       'generation_sha256': sha(raw), 'gzip_sha256': sha(archive),
       'responses': len(records), 'raw_judgments_checked': len(judgments), 'order_reversals': 6,
       'activity': activity, 'persona_history': persona, 'native_history_hashes': history['hashes'],
       'native_successes': 13, 'native_trials': 18, 'corrected_span_cells': history['span_cells'],
       'fixed_DEV_eligibility': history['span_summary']['eligibility'],
       'protected_hashes': protected, 'unreserved_usd': budget['unreserved_usd'],
       'new_reservation_usd': '0', 'paid_calls': 0, 'both_goals_open': True}
(ROOT/'verification.json').write_text(json.dumps(out, indent=2)+'\n')
print('POST_MEDIATION_SYNTHESIS_PASS', json.dumps({k:v for k,v in out.items() if k not in
      ('activity','persona_history','native_history_hashes','protected_hashes')}))
