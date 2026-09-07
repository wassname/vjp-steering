"""Request-coupled paired-scenario sensitivity, saved observations only.

PI/OpenAI Codex. Bounds couple exact (cache_key, prompt) requests globally.
They are deterministic observed-repeat envelopes, not confidence intervals.
"""
import hashlib
import json
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path

ROOT = Path('slop/logs/20260907_j_lens_request_sensitivity')
DISPLAY = Path('slop/logs/20260907_j_lens_judged_display')
RANDOM = Path('slop/logs/20260907_j_lens_matched_random')


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def close(a, b):
    assert abs(float(a) - float(b)) < 1e-10, (a, b)


def effect(row):
    assert row['order'] in ('AB', 'BA') and row['side'] in ('+C', '-C')
    j = row['judgment']
    a, b = F(str(j['on_axis_A'])), F(str(j['on_axis_B']))
    value = (b - a) * (1 if row['order'] == 'AB' else -1) * (1 if row['side'] == '+C' else -1)
    close(value, row['exported_effect'])
    raw = json.loads(row['raw'])
    for axis in ('on_axis_A', 'on_axis_B', 'off_axis_A', 'off_axis_B'):
        close(j[axis], raw[axis])
    return value


def bounds(appearances, intervals):
    """Combine coefficients before using intervals; shared requests cancel."""
    weights = defaultdict(F)
    for key, weight in appearances:
        weights[key] += weight
    weights = {k: w for k, w in weights.items() if w}
    lower = sum(min(w * intervals[k][0], w * intervals[k][1]) for k, w in weights.items())
    upper = sum(max(w * intervals[k][0], w * intervals[k][1]) for k, w in weights.items())
    return lower, upper, weights


def self_test():
    assert bounds([('a', F(1)), ('a', F(-1))], {'a': (F(-8), F(9))}) == (0, 0, {})
    assert bounds([('a', F(-2)), ('b', F(3))], {'a': (F(-1), F(4)), 'b': (F(2), F(5))})[:2] == (-2, 17)
    assert bounds([('a', F(2))], {'a': (F(3), F(3))})[:2] == (6, 6)
    bad = {'order': 'AB', 'side': '+C', 'judgment': {'on_axis_A': 1, 'on_axis_B': 2}, 'exported_effect': 9}
    try:
        effect(bad)
    except AssertionError:
        pass
    else:
        raise AssertionError('Corrupt reconstruction did not fail')
    print('SYNTHETIC_PASS shared_request_cancellation sign_weight_bounds singleton_point reconstruction_failfast')


def main():
    self_test()
    manifest = load(DISPLAY / 'manifest.json')
    points = load(DISPLAY / 'points.json')
    comparison = load(RANDOM / 'comparison.json')
    repeat_audit = load(DISPLAY / 'repeated-request-audit.json')
    paths = {DISPLAY / name for name in ('manifest.json', 'points.json', 'repeated-request-audit.json')}
    paths.add(RANDOM / 'comparison.json')
    paths.update(Path(p) for p in ('results/plot.png', 'results/plot_pareto.png', 'results/index.md', 'results/index.html', 'data/results.csv'))
    for item in manifest['artifacts']:
        paths.update(Path(item[k]) for k in ('generation', 'judgments'))
    before = {str(p): sha(p) for p in sorted(paths)}
    cells, requests, responses = {}, defaultdict(list), {}
    scenarios = None
    for item in manifest['artifacts']:
        for k in ('generation', 'judgments'):
            assert sha(item[k]) == item[k + '_sha256']
        data = load(item['generation'])
        alpha = data['fixed_alpha']
        owner = item.get('seed')
        assert (owner is None and item['method'] == 'named-GP additive') or (owner in range(5) and item['method'] == 'matched random')
        treatments = {(r['scenario'], r['side']): (i, r) for i, r in enumerate(data['records'])}
        baselines = {r['scenario']: (i, r) for i, r in enumerate(data['reused_records']) if r['condition'] == 'bare'}
        rows = [json.loads(line) for line in Path(item['judgments']).read_text().splitlines()]
        assert len(rows) == 60
        seen = set()
        for line, row in enumerate(rows, 1):
            scenario, side, order = row['vignette'], row['side'], row['order']
            key = (alpha, side, owner, scenario, order)
            assert key not in cells
            seen.add((scenario, side, order))
            v = effect(row)
            ti, treatment = treatments[scenario, side]
            bi, baseline = baselines[scenario]
            a, b = (baseline, treatment) if order == 'AB' else (treatment, baseline)
            assert row['prompt'].endswith('Response A:\n' + a['text'] + '\n\nResponse B:\n' + b['text'])
            request = (row['cache_key'], row['prompt'])
            record = {'judgment_link': f"{item['judgments']}:{line}", 'generation_link': f"{item['generation']}#/records/{ti}", 'baseline_link': f"{item['generation']}#/reused_records/{bi}", 'effect': float(v), 'effect_exact': str(v), 'order': order, 'side': side, 'alpha': alpha, 'seed': owner, 'scenario': scenario, 'raw': row['raw']}
            requests[request].append(record)
            cells[key] = (v, request, record)
            responses[key] = {'baseline': baseline['text'], 'treatment': treatment['text'], 'text_equal': baseline['text'] == treatment['text'], 'token_equal': baseline['generated_ids'] == treatment['generated_ids']}
        cohort = sorted({s for s, _, _ in seen})
        assert len(cohort) == 15 and seen == {(s, side, order) for s in cohort for side in ('+C', '-C') for order in ('AB', 'BA')}
        if scenarios is None:
            scenarios = cohort
        assert scenarios == cohort
        for side in ('+C', '-C'):
            point = next(p for p in points if p['alpha'] == alpha and p['side'] == side and p['seed'] == owner)
            for order in ('AB', 'BA'):
                close(sum(cells[alpha, side, owner, s, order][0] for s in cohort) / 15, point[order])
            close(sum(cells[alpha, side, owner, s, o][0] for s in cohort for o in ('AB', 'BA')) / 30, point['effect'])
    assert len(cells) == 1080
    repeated = {k for k, rs in requests.items() if len(rs) > 1}
    assert len(repeated) == 92
    assert {(r['cache_key'], r['prompt']) for r in repeat_audit['groups']} == repeated
    intervals = {k: (min(F(r['effect_exact']) for r in rs), max(F(r['effect_exact']) for r in rs)) for k, rs in requests.items()}
    request_ids = {k: hashlib.sha256(json.dumps(k).encode()).hexdigest() for k in requests}
    results = []
    for alpha in (1, 2, 4):
        for side in ('+C', '-C'):
            contributions, appearances = [], []
            for scenario in scenarios:
                ordered = {}
                for order in ('AB', 'BA'):
                    ordered[order] = cells[alpha, side, None, scenario, order][0] - sum(cells[alpha, side, seed, scenario, order][0] for seed in range(5)) / 5
                    for owner in (None, 0, 1, 2, 3, 4):
                        _, request, _ = cells[alpha, side, owner, scenario, order]
                        appearances.append((request, F(1, 30) if owner is None else F(-1, 150)))
                contribution = (ordered['AB'] + ordered['BA']) / 2
                contributions.append({'scenario': scenario, 'AB': float(ordered['AB']), 'BA': float(ordered['BA']), 'paired': float(contribution), 'strict_AB_BA_reversal': ordered['AB'] * ordered['BA'] < 0})
            original = sum(F(str(r['paired'])) for r in contributions) / 15
            saved = next(g for g in comparison['groups'] if g['alpha'] == alpha and g['side'] == side)
            close(original, saved['source_effect'] - saved['random_mean'])
            lower, upper, weights = bounds(appearances, intervals)
            # Independently evaluate attainable endpoints through original appearances.
            for endpoint, minimize in ((lower, True), (upper, False)):
                choices = {k: intervals[k][0 if (w > 0) == minimize else 1] for k, w in weights.items()}
                assert sum(w * choices.get(k, intervals[k][0]) for k, w in appearances) == endpoint
            contributing_repeats = sum(k in repeated for k in weights)
            for row in contributions:
                row['leave_one_out'] = float((15 * original - F(str(row['paired']))) / 14)
            top = sorted(contributions, key=lambda r: (-abs(r['paired']), r['scenario']))[:3]
            top_evidence = []
            for contribution in top:
                scenario = contribution['scenario']
                records = []
                for owner in (None, 0, 1, 2, 3, 4):
                    for order in ('AB', 'BA'):
                        key = (alpha, side, owner, scenario, order)
                        _, request, record = cells[key]
                        records.append({**record, **responses[key], 'request_id': request_ids[request]})
                top_evidence.append({'scenario': scenario, 'paired': contribution['paired'], 'records': records})
            result = {'alpha': alpha, 'side': side, 'source_effect': saved['source_effect'], 'random_mean': saved['random_mean'], 'original_contrast': float(original), 'AB_contrast': sum(r['AB'] for r in contributions) / 15, 'BA_contrast': sum(r['BA'] for r in contributions) / 15, 'observed_repeat_envelope': [float(lower), float(upper)], 'envelope_contains_zero': lower <= 0 <= upper, 'positive_scenarios': sum(r['paired'] > 0 for r in contributions), 'negative_scenarios': sum(r['paired'] < 0 for r in contributions), 'zero_scenarios': sum(r['paired'] == 0 for r in contributions), 'strict_AB_BA_reversal_scenarios': sum(r['strict_AB_BA_reversal'] for r in contributions), 'leave_one_out_range': [min(r['leave_one_out'] for r in contributions), max(r['leave_one_out'] for r in contributions)], 'contributing_requests': len(weights), 'contributing_repeated_requests': contributing_repeats, 'repeat_fraction': contributing_repeats / len(weights), 'cancelled_requests': len({k for k, _ in appearances}) - len(weights), 'singleton_uncertainty_unmeasured': len(weights) - contributing_repeats, 'contributions': contributions, 'weights': [{'request_id': request_ids[k], 'weight_exact': str(w), 'interval': [float(x) for x in intervals[k]]} for k, w in weights.items()], 'largest_absolute_three_scenarios': top_evidence}
            results.append(result)
    after = {str(p): sha(p) for p in sorted(paths)}
    assert before == after
    output = {'scope': 'Offline only; 5/10 random seeds; DEV15 uncalibrated; both goals open.', 'limitations': 'Not a CI or sampling distribution. Singleton repeat uncertainty unmeasured. Bounds use globally observed identical requests and combine coefficients before bounding. Original contrast can lie outside coupled envelope because original repeated observations can disagree. No scores replaced. Top three absolute contributions selected identically per group for inspection, never exclusion.', 'input_output_hashes_unchanged': before, 'synthetic_checks': ['shared_request_cancellation', 'sign_weight_bounds', 'singleton_point', 'reconstruction_failfast'], 'requests': [{'request_id': request_ids[k], 'cache_key': k[0], 'prompt': k[1], 'repeat_count': len(rs), 'observations': rs} for k, rs in requests.items()], 'groups': results, 'paid_cost_usd': 0, 'unreserved_balance_usd': 3.41988872744}
    ROOT.mkdir(exist_ok=True, parents=True)
    (ROOT / 'audit.json').write_text(json.dumps(output, indent=2))
    print('RECONSTRUCTION_PASS 1080 cells; 36 points; 6 paired contrasts; 92 repeated requests; full request/response parity')
    print('IMMUTABLE_HASHES_PASS', len(before))
    for g in results:
        print('GROUP', json.dumps({k: v for k, v in g.items() if k not in ('contributions', 'weights', 'largest_absolute_three_scenarios')}))


if __name__ == '__main__':
    main()
