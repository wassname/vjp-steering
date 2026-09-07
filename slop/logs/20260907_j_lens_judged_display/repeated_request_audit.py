"""Offline repeated-request reliability check; PI/OpenAI Codex."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

root = Path('slop/logs/20260907_j_lens_judged_display')
manifest = json.loads((root / 'manifest.json').read_text())
groups = defaultdict(list)
for artifact in manifest['artifacts']:
    path = Path(artifact['judgments'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact['judgments_sha256']
    for line in path.read_text().splitlines():
        row = json.loads(line)
        j = row['judgment']
        effect = (j['on_axis_B'] - j['on_axis_A']) * (1 if row['order'] == 'AB' else -1) * (1 if row['side'] == '+C' else -1)
        groups[(row['cache_key'], row['prompt'])].append({'path': str(path), 'scenario': row['vignette'], 'order': row['order'], 'side': row['side'], 'effect': effect, 'raw': row['raw']})
repeats = []
for (key, prompt), rows in groups.items():
    if len(rows) < 2:
        continue
    effects = [r['effect'] for r in rows]
    signs = {0 if abs(e) < 1e-12 else (1 if e > 0 else -1) for e in effects}
    repeats.append({'cache_key': key, 'prompt': prompt, 'records': rows, 'range': max(effects)-min(effects), 'varies': max(effects)-min(effects)>1e-12, 'bitwise_varies': max(effects) != min(effects), 'strict_reversal': -1 in signs and 1 in signs, 'tie_disagreement': 0 in signs and len(signs)>1})
points = json.loads((root / 'points.json').read_text())
if isinstance(points, dict):
    points = points['points']
source = [p for p in points if p['method'] == 'named-GP additive']
summary = {'judgments': sum(map(len, groups.values())), 'unique_request_groups': len(groups), 'repeated_groups': len(repeats), 'varying_groups': sum(r['varies'] for r in repeats), 'bitwise_varying_groups': sum(r['bitwise_varies'] for r in repeats), 'strict_reversal_groups': sum(r['strict_reversal'] for r in repeats), 'tie_disagreement_groups': sum(r['tie_disagreement'] for r in repeats), 'maximum_range': max(r['range'] for r in repeats), 'median_range': median(r['range'] for r in repeats), 'source_effects': [{'alpha': p['alpha'], 'side': p['side'], 'effect': p['effect']} for p in source], 'limits': 'Observed repeat groups are selected by exact request reuse, not independent samples or a calibrated noise distribution. Group ranges are single-scenario effects; source effects are cohort means, not directly interchangeable uncertainty measures. Strict reversals and tie disagreements can overlap. Raw scores unchanged.'}
assert summary['judgments'] == 1080 and summary['repeated_groups'] == 92
(root / 'repeated-request-audit.json').write_text(json.dumps({'summary': summary, 'groups': repeats}, indent=2))
print('REPEATED_REQUEST_AUDIT_PASS', json.dumps(summary))
