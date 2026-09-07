"""Offline attribution of recorded old/new effects; never adjusts scores."""
import hashlib
import json
from pathlib import Path
from statistics import mean
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / 'scripts'), str(REPO / 'src')]
import judge

ROOT = Path(__file__).resolve().parent
OLD = REPO / 'slop/logs/20260907_j_lens_additive_concepts_alpha4'
NEW = REPO / 'slop/logs/20260907_j_lens_single_concept'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scores(j, order):
    """AB means baseline A / steered B; BA means steered A / baseline B."""
    return (j['on_axis_A'], j['on_axis_B']) if order == 'AB' else (j['on_axis_B'], j['on_axis_A'])


def decompose(old, new, side, order):
    sign = 1 if side == '+C' else -1
    b0, t0 = scores(old, order)
    b1, t1 = scores(new, order)
    baseline = -sign * (b1 - b0)
    steered = sign * (t1 - t0)
    old_effect, new_effect = sign * (t0 - b0), sign * (t1 - b1)
    assert abs(baseline + steered - (new_effect - old_effect)) < 1e-12
    return dict(old_baseline=b0, new_baseline=b1, old_steered=t0, new_steered=t1,
                baseline_contribution=baseline, steered_contribution=steered,
                old_effect=old_effect, new_effect=new_effect, total=new_effect-old_effect)


def synthetic():
    for order in ('AB', 'BA'):
        def encoded(b, t):
            a, c = (b, t) if order == 'AB' else (t, b)
            return dict(on_axis_A=a, on_axis_B=c)
        for side, sign in (('+C', 1), ('-C', -1)):
            r = decompose(encoded(1, 2), encoded(3, 7), side, order)
            assert r['baseline_contribution'] == -2*sign
            assert r['steered_contribution'] == 5*sign and r['total'] == 3*sign
            r = decompose(encoded(1, 2), encoded(3, 2), side, order)
            assert r['baseline_contribution'] == r['total'] == -2*sign and r['steered_contribution'] == 0
            r = decompose(encoded(1, 2), encoded(1, 7), side, order)
            assert r['steered_contribution'] == r['total'] == 5*sign and r['baseline_contribution'] == 0
            r = decompose(encoded(1, 2), encoded(1, 2), side, order)
            assert r['total'] == r['baseline_contribution'] == r['steered_contribution'] == 0
    print('SYNTHETIC_MAPPING_PASS bothsigns_AB_BA baseline_only_steered_only_identity')


def main():
    synthetic()
    manifest = json.loads((NEW / 'manifest.json').read_text())
    immutable = {REPO / p for p in ('results/plot.png', 'results/plot_pareto.png', 'results/index.md', 'results/index.html', 'data/results.csv', 'scripts/judge.py')}
    for a in manifest['artifacts']:
        for name in ('generation', 'judgments'):
            path = REPO / a[name]
            assert sha(path) == a[name+'_sha256']
            immutable.add(path)
    before = {str(p.relative_to(REPO)): sha(p) for p in sorted(immutable)}
    runs = []
    for folder in (OLD, NEW):
        g = json.loads((folder/'generation.json').read_text())
        records = {(r['scenario'], r['side']): r for r in g['records']}
        baseline = {r['scenario']: r for r in g['reused_records'] if r['condition'] == 'bare'}
        js = {}
        for line, text in enumerate((folder/'judgments.jsonl').read_text().splitlines(), 1):
            r = json.loads(text)
            key = (r['vignette'], r['side'], r['order'])
            assert key not in js
            js[key] = (r, f"{(folder/'judgments.jsonl').relative_to(REPO)}#L{line}")
        assert len(js) == 60 and len(records) == 30 and len(baseline) == 15
        runs.append((g, records, baseline, js))
    assert runs[0][0]['reference_sha256'] == runs[1][0]['reference_sha256']
    assert runs[0][0]['model_revision'] == runs[1][0]['model_revision']
    assert runs[0][0]['reused_records'] == runs[1][0]['reused_records']
    assert runs[0][3].keys() == runs[1][3].keys()
    cells, evidence = [], []
    for scenario, side, order in sorted(runs[0][3]):
        paired = []
        for g, records, baselines, judgments in runs:
            b, t = baselines[scenario], records[(scenario, side)]
            r, link = judgments[(scenario, side, order)]
            assert b['input_ids'] == t['input_ids'] and b['rendered'] == t['rendered']
            row = dict(bare=b['text'], steered=t['text'], prompt=t['prompt'], vignette=scenario, side=side)
            assert judge.judge_prompt(row, order) == r['prompt']
            assert judge.cache_key(row, order, r['pass']) == r['cache_key']
            assert r['model'] == judge.MODEL and r['rubric_version'] == judge.RUBRIC
            raw = json.loads(r['raw'])
            assert all(raw[k] == r['judgment'][k] for k in ('on_axis_A', 'on_axis_B', 'off_axis_A', 'off_axis_B', 'evidence'))
            paired.append((b, t, r, link))
        old, new = paired
        assert old[0]['text'] == new[0]['text'] and old[0]['generated_ids'] == new[0]['generated_ids']
        result = decompose(old[2]['judgment'], new[2]['judgment'], side, order)
        for label, item in (('old', old), ('new', new)):
            assert abs(result[label+'_effect'] - item[2]['exported_effect']) < 1e-12
        cells.append(dict(scenario=scenario, side=side, order=order, sign=1 if side=='+C' else -1,
                          baseline_text_equal=True, baseline_tokens_equal=True,
                          old_raw_link=old[3], new_raw_link=new[3], **result))
        if scenario in ('syco_bullshit_v2_phys_pnf_02', 'syco_bullshit_v2_sw_pnf_03'):
            evidence.append(dict(scenario=scenario, side=side, order=order, baseline=old[0]['text'],
                                 old=old[1]['text'], new=new[1]['text'], old_judge_raw=old[2]['raw'],
                                 new_judge_raw=new[2]['raw'], old_link=old[3], new_link=new[3]))
    fields = ('baseline_contribution', 'steered_contribution', 'old_effect', 'new_effect', 'total')
    scenarios = []
    for scenario, side in sorted(runs[0][1]):
        rows = [c for c in cells if c['scenario']==scenario and c['side']==side]
        assert len(rows) == 2
        scenarios.append(dict(scenario=scenario, side=side, **{k:mean(r[k] for r in rows) for k in fields}))
    summary = {}
    for side in ('+C', '-C'):
        rows = [c for c in cells if c['side']==side]
        summary[side] = {k:mean(r[k] for r in rows) for k in fields}
        assert abs(summary[side]['total']-summary[side]['baseline_contribution']-summary[side]['steered_contribution'])<1e-12
    assert all(sha(REPO/p)==digest for p,digest in before.items())
    output = dict(sign_convention='s=+1 for +C, -1 for -C; effect=s*(steered-baseline); new-old=s*delta_steered - s*delta_baseline. Contributions are recorded arithmetic, NOT adjusted scores or causal noise estimates.',
                  immutable_sha256=before, summary=summary, scenarios=scenarios, cells=cells, DNL_CSN=evidence,
                  budget=dict(new_GPU_API_cost=0, unreserved_usd=2.61988872744, outstanding_reserves='unchanged'),
                  limitations='Same baseline is independently rated in different pairs; drift may reflect context and stochastic judging. No provider-wire IDs captured. Both project goals open; no new paid work.')
    (ROOT/'audit.json').write_text(json.dumps(output, indent=2)+'\n')
    lines = ['# All-scenario recorded-score attribution', '', output['sign_convention'], '', '|Scenario|Side|Baseline contribution|Steered contribution|Total new−old|', '|---|---|---:|---:|---:|']
    for r in scenarios:
        lines.append(f"|{r['scenario']}|{r['side']}|{r['baseline_contribution']:+.6f}|{r['steered_contribution']:+.6f}|{r['total']:+.6f}|")
    lines += ['', '## Complete DNL and CSN evidence']
    for r in evidence:
        lines += ['', f"### {r['scenario']} {r['side']} {r['order']}", '', 'Baseline: '+r['baseline'], '', 'Old: '+r['old'], '', 'New: '+r['new'], '', r['old_link'], '```json', r['old_judge_raw'], '```', r['new_link'], '```json', r['new_judge_raw'], '```']
    (ROOT/'scenario-evidence.md').write_text('\n'.join(lines)+'\n')
    print('BASELINE_ATTRIBUTION_PASS', json.dumps(dict(cells=len(cells), scenarios=len(scenarios), baseline_text_and_tokens_equal=True, requests_and_cache_keys_exact=120, immutable_files=len(before), summary=summary)))


if __name__ == '__main__':
    main()
