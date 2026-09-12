"""Inspect existing cache by content keys only. Author: PI/gpt-6-astra."""

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import export
import judge


runs = [
    'run_20260827T090901_vjp_mlp_up_shrink_s0_c4p0',
    'run_20260828T095615_vjp_mlp_up_shrink_s0_+c4p0',
    'j-lens-components-empirical-candor-full-v1',
]
required = {}
rows_by_run = {}
for run in runs:
    if run.startswith('run_'):
        records = [json.loads(line) for line in (Path('outputs') / run / 'moral_demos.jsonl').read_text().splitlines()]
        scenarios = defaultdict(dict)
        for record in records:
            scenarios[record['scenario']][record['steer_direction'] or 'bare'] = record
        rows = [{'run': run, 'method': 'vjp_mlp_up_shrink', 'side': '+C', 'vignette': scenario, 'prompt': group['bare']['prompt'], 'bare': group['bare']['text'], 'steered': group['+C']['text']} for scenario, group in scenarios.items()]
        passes = 2
    else:
        rows = judge.experiment_rows(run, 'full', side_filter='+C', coefficient_filter=0.5, all_generated=True)
        passes = 1
    rows_by_run[run] = rows
    required[run] = judge.required_cells(rows, ('AB', 'BA'), passes)
keys = set().union(*(set(values) for values in required.values()))
content_runs = defaultdict(set)
for run in runs[:2]:
    for row in rows_by_run[run]:
        content_runs[(row['vignette'], row['bare'], row['steered'])].add(run)
cache = {}
models = Counter()
legacy = defaultdict(dict)
lines = 0
for lines, line in enumerate(judge.CACHE.open(), 1):
    record = json.loads(line)
    models[(record.get('model'), record.get('rubric_version'))] += 1
    if record.get('side') == '+C' and 'Response A:\n' in record['prompt'] and '\n\nResponse B:\n' in record['prompt'] and judge.valid(record.get('judgment', {})):
        response_a, response_b = record['prompt'].split('Response A:\n', 1)[1].split('\n\nResponse B:\n', 1)
        bare, steered = (response_a, response_b) if record['order']=='AB' else (response_b, response_a)
        for matched_run in content_runs.get((record['vignette'],bare,steered), ()):
            legacy[(matched_run, record.get('model'), record.get('rubric_version'))].setdefault(record['cache_key'], (lines, record))
    if record['cache_key'] in keys and judge.valid(record.get('judgment', {})):
        cache.setdefault(record['cache_key'], (lines, record))
print('CACHE_RECORDS', lines, 'bytes', judge.CACHE.stat().st_size)
print('CACHE_MODEL_RUBRIC_COUNTS', sorted((str(k),v) for k,v in models.items()))
print('REQUIRED_FOUND', len(keys), len(cache))
trace = []
for identity, records in legacy.items():
    by_scenario = defaultdict(list)
    for line_number, record in records.values():
        by_scenario[record['vignette']].append(record)
        if record['vignette'] == rows_by_run[identity[0]][0]['vignette']:
            trace.append({'requested_run':identity[0], 'cache_file':str(judge.CACHE), 'line':line_number, 'record':record})
    changes = [mean(export.score_cell(record)[1] for record in group) for group in by_scenario.values()]
    print('LEGACY_RUN_RUBRIC', identity, 'scenarios',len(by_scenario), 'pass_counts', dict(Counter(map(len,by_scenario.values()))), 'mean_abs_scenario_change',mean(map(abs,changes)), 'abs_mean_scenario_change',abs(mean(changes)), 'effect',mean(mean(export.score_cell(record)[0] for record in group) for group in by_scenario.values()))
for run, required_cells in required.items():
    print('RUN_KEY_COVERAGE', run, len(required_cells), len(set(required_cells) & set(cache)))
    by_scenario = defaultdict(list)
    for key, (row, order, pass_index) in required_cells.items():
        if key in cache:
            line_number, record = cache[key]
            by_scenario[row['vignette']].append(record)
            if row['vignette'] == rows_by_run[run][0]['vignette']:
                trace.append({'requested_run':run, 'cache_file':str(judge.CACHE), 'line':line_number, 'record':record})
    if by_scenario:
        signed_changes = [mean(export.score_cell(record)[1] for record in records) for records in by_scenario.values()]
        print('RUN_DAMAGE', run, 'scenarios',len(by_scenario),'pass_counts',dict(Counter(map(len,by_scenario.values()))), 'mean_abs_scenario_change',mean(map(abs,signed_changes)),'abs_mean_scenario_change',abs(mean(signed_changes)))
        print('RUN_EFFECT',run,mean(export.signed_axis_effect('candidness' if run==runs[-1] else '+C',[export.score_cell(record) for record in records]) for records in by_scenario.values()))
        print('RUN_REVERSALS',run,sum(export.judge_diagnostics(records)[0] for records in by_scenario.values()))
Path('slop/reviews/20260912_results_review_raw_samples.json').write_text(json.dumps(trace,ensure_ascii=False,indent=2)+'\n')
print('CACHE_REVIEW_COMPLETE raw samples saved verbatim')
