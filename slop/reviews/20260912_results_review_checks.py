"""Read-only CPU reproductions for the results review. Author: PI/gpt-6-astra."""

import asyncio
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from math import isclose
from statistics import mean
from unittest.mock import AsyncMock, patch

import export
import judge
import render_dev_comparison as dev
from vjp_steering import results as r


methods, seeds = r.primary_methods()
rows = r._rows(methods=methods, method_seeds=seeds)
print('INPUT_SHA256', {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [r.DATA, Path('results/dev-comparison.csv'), Path('results/plot.png'), Path('results/plot_pareto.png')]})
export.self_test()
try:
    r._summary(rows, methods, seeds)
except KeyError as error:
    assert error.args == ('random',)
    print('PRIMARY_SUMMARY_FAIL', repr(error))
else:
    raise AssertionError('expected missing random seed map')

record = {'order': 'AB', 'pass': 0, 'judgment': {'on_axis_A': 0, 'on_axis_B': 1, 'off_axis_A': 0, 'off_axis_B': 0}}
try:
    export.judge_diagnostics([export.score_cell(record)])
except TypeError as error:
    print('LEGACY_EXPORT_FAIL', repr(error))
else:
    raise AssertionError('expected wrong diagnostics argument type')

print('SUMMARY_WITH_ONLY_RANDOM_MAP_SUPPLIED', json.dumps(r._summary(rows, methods, {**seeds, 'random': set(range(10))})))
print('ROW_COUNTS', dict(Counter(x['method'] for x in rows)))
counts = Counter((x['method'], x['seed'], x['C'], x['side']) for x in rows)
print('DUPLICATE_METHOD_SEED_DOSE_SIDE', sum(n > 1 for n in counts.values()), 'max_repeats', max(counts.values()))
scenario_rows = list(csv.DictReader(open('data/judged_scenarios.csv')))
scenario_groups = Counter((x['source_run'], x['C'], x['side']) for x in scenario_rows)
print('PRIMARY_SCENARIO_COVERAGE', len(scenario_rows), dict(Counter(scenario_groups.values())))
run_names = ['run_20260827T090901_vjp_mlp_up_shrink_s0_c4p0', 'run_20260828T095615_vjp_mlp_up_shrink_s0_+c4p0']
run_records = [{(record['scenario'], record['steer_direction'] or 'bare'): record['text'] for line in (Path('outputs') / name / 'moral_demos.jsonl').read_text().splitlines() if (record := json.loads(line))} for name in run_names]
for side in ['bare', '+C']:
    print('DUPLICATE_RUN_IDENTICAL_TEXTS', side, sum(run_records[0][key] == value for key, value in run_records[1].items() if key[1] == side), 'of', sum(key[1] == side for key in run_records[1]))
print('CURRENT_SORTED_COHORT_HASH', export.cohort_hash())

controls = [{'effect': 0., 'off_axis_perturbation': 0.}, {'effect': 1., 'off_axis_perturbation': 0.1}, {'effect': 2., 'off_axis_perturbation': 1.}]
xs, ys = r._smooth_anchors(controls)
print('SMOOTH_THREE_ANCHORS', controls, 'curve_at_middle_x', (xs[len(xs)//2], ys[len(ys)//2]))
assert xs[len(xs)//2] == 1 and isclose(ys[len(ys)//2], 0.3)
means = r._means(rows, methods, seeds)
for method in methods:
    if method == 'random':
        continue
    for side, sign in [('+C', 1), ('-C', -1)]:
        points = sorted([p for p in means if p['method'] == method and p['side'] == side], key=lambda p: p['C'])
        if points:
            peak = max(points, key=lambda p: sign*p['effect'])
            print('ENDPOINT_VS_TABLE_PEAK', method, side, {'endpoint_C': points[-1]['C'], 'endpoint_effect': points[-1]['effect'], 'endpoint_damage': points[-1]['off_axis_perturbation'], 'peak_C': peak['C'], 'peak_effect': peak['effect'], 'peak_damage': peak['off_axis_perturbation']})

random = [x for x in rows if x['method'] == 'random']
for dose in sorted({x['C'] for x in random}):
    at = [x for x in random if x['C'] == dose]
    both = {seed for seed in range(10) if sum(x['admissible'] for x in at if x['seed'] == seed) == 2}
    print('RANDOM_SURVIVORS', dose, 'both', sorted(both), 'by_side', {side: sum(x['admissible'] for x in at if x['side'] == side) for side in ['+C', '-C']})

raw_dev = list(csv.DictReader(open('results/dev-comparison.csv')))
dev_rows = [{**x, 'seed': int(x['seed']), 'C': float(x['C']), 'effect': float(x['effect']), 'off_axis_perturbation': float(x['off_axis_perturbation']), 'admissible': x['admissible'] == 'True', 'normalized_dose_id': int(x['normalized_dose_id']) if x['normalized_dose_id'] else None} for x in raw_dev]
calibrated_dose_groups = r.calibrated_random_rungs([x for x in dev_rows if x['method']=='random'], set(range(5)))
fractions = json.loads(Path('slop/logs/20260909_j_lens_dev/dev-comparison-provenance.json').read_text())['calibration_grid']['fractions']
print('DEV_RANDOM_POLYGON_ORDER', {side: [(x['rung'], fractions[x['rung']], x['off_axis_perturbation']) for x in values] for side, values in calibrated_dose_groups.items()})
dev_methods = tuple(sorted({x['method'] for x in dev_rows}))
dev_seeds = {method: set(range(5)) if method=='random' else {0} for method in dev_methods}
original_anchors = r._pareto_curve_anchors

def capture_anchors(points, side):
    anchors = original_anchors(points, side)
    rejected = [(p['method'], p['C'], p['effect'], p['off_axis_perturbation']) for p in anchors if 'C' in p and not p['admissible']]
    if rejected:
        print('ACTUAL_PLOT_REJECTED_PARETO_ANCHORS', side, rejected)
    return anchors

with patch.object(r, '_pareto_curve_anchors', side_effect=capture_anchors):
    figure = r.plot(dev_rows, dev_methods, dev_seeds, pareto=True, include_rejected=True, random_region='calibrated_rung', damage_headroom=1.2)
for trace in figure.data:
    if trace.name == 'mean_diff +C Pareto path':
        print('ACTUAL_DEV_MEAN_DIFF_CURVE_END', trace.x[-1], trace.y[-1])
    if trace.hovertemplate and 'mean_diff (baseline) final admissible dose' in trace.hovertemplate:
        print('ACTUAL_DEV_MEAN_DIFF_SELECTED_MARKER', trace.x, trace.y, trace.hovertemplate)


class Http500(Exception):
    status_code = 500
    body = {}

class StopProbe(Exception):
    pass

async def retry_probe():
    request = AsyncMock(side_effect=[Http500(), Http500(), Http500(), Http500(), StopProbe()])
    with patch.object(judge, 'judge_prompt', return_value='fixture'), patch.object(judge, 'request_with_rate_limit', request), patch.object(judge.asyncio, 'sleep', AsyncMock()):
        try:
            await judge.judge_one(None, {}, 'AB', 0)
        except StopProbe:
            print('HTTP500_REQUEST_COUNT_BEFORE_TEST_STOP', request.await_count)
            assert request.await_count == 5
        else:
            raise AssertionError('expected test-owned sentinel')

asyncio.run(retry_probe())
print('CPU_REPRODUCTIONS_COMPLETE no API calls, no GPU, no production writes')
