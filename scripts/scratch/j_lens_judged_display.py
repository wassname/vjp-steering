"""Trace retained additive DEV judgments into an explicit renderer input; no API calls."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from vjp_steering.results_dev import load_points, sha

ROOT = Path('slop/logs/20260907_j_lens_judged_display')
RANDOM = Path('slop/logs/20260907_j_lens_matched_random')


def build():
    ROOT.mkdir(parents=True, exist_ok=True)
    items = []
    for alpha in (1,2,4):
        folder = Path('slop/logs/20260907_j_lens_additive_concepts'+('' if alpha==1 else f'_alpha{alpha}'))
        items.append(dict(method='named-GP additive', seed=None, generation=str(folder/'generation.json'), judgments=str(folder/'judgments.jsonl')))
    for seed in range(10):
        expected = [RANDOM/f'seed{seed}'/f'alpha{alpha}'/'judgments.jsonl' for alpha in (1,2,4)]
        if not all(path.exists() and len(path.read_text().splitlines())==60 for path in expected):
            continue  # A seed counts as judged only when every predeclared dose has both orders.
        for alpha in (1,2,4):
            folder = RANDOM/f'seed{seed}'/f'alpha{alpha}'
            if (folder/'judgments.jsonl').exists():
                rows = (folder/'judgments.jsonl').read_text().splitlines()
                if len(rows)==60:
                    items.append(dict(method='matched random', seed=seed, generation=str(folder/'generation.json'), judgments=str(folder/'judgments.jsonl')))
    for item in items:
        item.update({key+'_sha256':sha(item[key]) for key in ('generation','judgments')})
    manifest = {'status':'incomplete, uncalibrated DEV; eligibility unknown', 'artifacts':items}
    path = ROOT/'manifest.json'
    path.write_text(json.dumps(manifest, indent=2)+'\n')
    _, points = load_points(path)
    (ROOT/'points.json').write_text(json.dumps(points, indent=2)+'\n')
    cost = 0
    lines = ['# Complete retained judgments and response evidence', 'No raw score replacement; no coherence acceptance inferred.']
    for item in items:
        data=json.loads(Path(item['generation']).read_text())
        js=[json.loads(line) for line in Path(item['judgments']).read_text().splitlines()]
        if item['seed'] is not None or data['fixed_alpha'] != 1:
            cost += sum(j['cost_usd'] for j in js)
        bare={r['scenario']:r for r in data['reused_records'] if r['condition']=='bare'}
        for r in data['records']:
            b=bare[r['scenario']]
            lines.extend([f"## {item['method']} seed={item['seed']} alpha={data['fixed_alpha']} {r['scenario']} {r['side']}",
                '```text\n'+r['rendered']+'\n```', 'Baseline: '+b['text'], 'Steered: '+r['text'],
                json.dumps({'text_equal':b['text']==r['text'],'token_equal':b['generated_ids']==r['generated_ids'],'health':r['health']})])
            for j in js:
                if (j['vignette'],j['side'])==(r['scenario'],r['side']):
                    lines.append(json.dumps({k:j[k] for k in ('order','cache_key','exported_effect','raw')},ensure_ascii=False))
    (ROOT/'responses-and-judgments.md').write_text('\n\n'.join(lines)+'\n')
    print('JUDGED_DISPLAY_PASS',json.dumps({'points':len(points),'new_API_cost':cost,'manifest':str(path),'primary_csv_sha256':sha('data/results.csv')}))

if __name__=='__main__':build()
