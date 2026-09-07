"""Offline, fail-fast evidence reuse audit; performs no model or API calls."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPAN = Path('outputs/audits/20260907_j_lens_prompt_span_activity/dev15-corrected-single-v3.json')
BRIDGE = SPAN.with_name('readout-bridge-corrected-dev15-v3.json')
PARITY = SPAN.with_name('primary-padded-parity-controls-v2.json')
NATIVE = Path('outputs/experiments/paper-native-verbal-report-chat-alpha2-v1/results.json')
PROBE = Path('/workspace/2026/jspace/jsteer/docs/vendor/jacobian-lens/data/experiments/probe-swap.json')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text())

span, bridge, parity, native, probe = map(load, (SPAN, BRIDGE, PARITY, NATIVE, PROBE))
assert len(span['records']) == 30 and len(bridge['records']) == 15
assert span['layers'] == bridge['layers'] == list(range(13, 22))
for key in ('model_revision', 'tokenizer_sha256', 'lens_sha256', 'readout'):
    assert span[key] == bridge[key]
assert span['model_revision'] == '851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a'
assert span['execution']['batch_size'] == 1
assert span['summary']['eligibility'] == {c: {'+C': 0, '-C': 0} for c in ('original', 'explicit_validity')}
assert bridge['summary']['answer_seam_matches'] == 15
assert bridge['summary']['emitted_answer_j_lens_prefill_rank1_coverage'] == 0
rows = []
for r in span['records']:
    expected = {(layer, pos) for layer in span['layers'] for pos in r['request_token_positions']}
    assert {(c['layer'], c['token_position']) for c in r['cells']} == expected
    assert len(r['cells']) == len(expected)
    cells = [c for c in r['cells'] if c['layer'] == 17]
    rows.append({'scenario': r['scenario'], 'condition': r['condition'],
                 'request_positions': r['request_token_positions'], 'cell_count': len(r['cells']),
                 'layer17_best_frozen_ranks': {name: min(c['candidates'][name]['rank'] for c in cells) for name in span['token_ids']}})
for r in bridge['records']:
    assert set(r['assistant_prefill_j_lens']) == {str(l) for l in span['layers']}
    assert r['ordinary_matches_emitted_first_token']
cp = bridge['companion_parity']
assert cp['passed']
for layer in cp['layers'].values():
    assert layer['cell_count'] == layer['top1_match_count']
    assert layer['candidate_rank_match_count'] == layer['candidate_rank_comparison_count']
    assert layer['maximum_candidate_score_absolute_difference'] == 0
assert len(native['trials']) == 18
assert sum(t['success_top1'] for t in native['trials']) == native['n_top1'] == 13
assert len(native['clean_rows']) == 14
assert sum(c['clean_is_listed_category_item'] for c in native['clean_rows']) == 8
for t in native['trials']:
    for field in ('zero_hook_calls', 'swap_hook_calls'):
        assert t[field] == {str(l): 1 for l in range(13, 22)}
first10 = probe['items'][:10]
assert len(first10) == 10 and len({r['name'] for r in first10}) == 10
result = {
    'decision': 'REUSE_NO_PAID_RUN',
    'hashes': {str(p): sha(p) for p in (SPAN, BRIDGE, PARITY, NATIVE, PROBE)},
    'model': {k: span[k] for k in ('model', 'model_revision', 'dtype', 'tokenizer_sha256', 'lens_sha256', 'lens_n_prompts')},
    'readout': span['readout'], 'span_summary': span['summary'], 'bridge_summary': bridge['summary'],
    'span_cells': sum(len(r['cells']) for r in span['records']), 'layer17_request_cells': sum(len(r['request_token_positions']) for r in span['records']),
    'parity': {'cells': sum(r['cell_count'] for r in cp['layers'].values()),
               'candidate_ranks': sum(r['candidate_rank_comparison_count'] for r in cp['layers'].values()),
               'max_score_error': 0, 'source_hashes': cp['companion_source_sha256'],
               'scenario': cp['compared_scenario'], 'positions': cp['compared_positions']},
    'per_scenario': rows,
    'bridge_layer17': [{'scenario': r['scenario'], 'position': r['assistant_prefill_position'],
                        'answer': r['control_answer'], 'readout': r['assistant_prefill_j_lens']['17']} for r in bridge['records']],
    'prior_native': {'source_revision': native['source_revision'], 'layers': native['layers'],
                     'coefficient': native['coefficient'], 'trials': 18, 'successes': 13,
                     'categories_total': 14, 'semantic_categories': 8,
                     'categories_with_eligible_targets': sorted({r['category'] for r in native['trials']}),
                     'model_revision': native.get('model_revision'), 'lens_sha256': native.get('lens_sha256'),
                     'clean_rows': native['clean_rows'], 'trials_full': native['trials']},
    'proposed_native10': {'file_items': len(probe['items']), 'rows': first10,
                          'measured_in_this_task': False, 'tokenization_and_correctness': 'not evaluated; no eligibility filtering'},
    'missing_observation': 'Exact current-pinned layer17 normalized clean intermediate ranks on first10 probe-swap implicit prompts; old native study measures eligible verbal-report next-token swaps across layers13–21, not these rows.',
    'budget': {'new_gpu_usd': 0, 'new_api_usd': 0, 'prior_reported_api_usd': 0.89405369412,
               'unreserved_before_task': 15.78873536744, 'conditional_reserve': 1,
               'unreserved_while_reserved': 14.78873536744, 'unreserved_after_release_unused_reserve': 15.78873536744,
               'failed_startup_reserve_usd': 5, 'actual_historical_modal_billing': 'unknown'}
}
(ROOT/'reuse.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print('REUSE_AUDIT_PASS', json.dumps({k: result[k] for k in ('decision','span_cells','layer17_request_cells','parity','budget')}))
