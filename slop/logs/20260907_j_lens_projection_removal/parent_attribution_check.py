"""PI/OpenAI Codex: independent raw-score attribution, no score changes."""
import json
from pathlib import Path
from statistics import mean
root = Path('slop/logs/20260907_j_lens_projection_removal')
old_root = Path('slop/logs/20260907_j_lens_single_concept')
new = [json.loads(x) for x in (root/'judgments.jsonl').read_text().splitlines()]
old = {(x['vignette'], x['order']): x for x in map(json.loads, (old_root/'judgments.jsonl').read_text().splitlines()) if x['side']=='-C'}
rows = []
for j in new:
    p = old[j['vignette'], j['order']]
    nscore, pscore = json.loads(j['raw']), json.loads(p['raw'])
    assert all(j['judgment'][k] == v for k, v in nscore.items())
    assert all(p['judgment'][k] == v for k, v in pscore.items())
    b, t = ('A','B') if j['order']=='AB' else ('B','A')
    baseline = nscore['on_axis_'+b] - pscore['on_axis_'+b]
    steered = pscore['on_axis_'+t] - nscore['on_axis_'+t]
    effect = nscore['on_axis_'+b] - nscore['on_axis_'+t]
    previous = pscore['on_axis_'+b] - pscore['on_axis_'+t]
    assert abs(effect - previous - baseline - steered)<1e-12
    rows.append((baseline, steered, effect-previous, effect))
assert len(rows)==30
print('PARENT_RAW_ATTRIBUTION_PASS', json.dumps(dict(zip(['baseline','steered','change','new_effect'],map(mean,zip(*rows))))))
