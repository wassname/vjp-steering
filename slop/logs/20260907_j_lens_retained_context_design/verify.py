"""Read-only saved-state/provenance checks; no torch/model/API imports."""
import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).parent
REVIEW = Path('/home/code/.pi/agent/sessions/--workspace-2026-jspace-j-steer_pub--/subagent-artifacts/outputs/5eabf553-41de-457e-9a94-d06db0970377/slop/reviews/j_lens_v10_donor_context_interpretation.md')
OLD = Path('slop/logs/20260907_j_lens_transfer_probe/generation.json')
NEW = Path('slop/logs/20260907_j_lens_donor_context/generation.json')
CONFIG = Path('/home/code/.cache/huggingface/hub/models--Qwen--Qwen3.5-4B/snapshots/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a/config.json')
MODEL = Path('.venv/lib/python3.13/site-packages/transformers/models/qwen3_5/modeling_qwen3_5.py')
CACHE = MODEL.parents[2]/'cache_utils.py'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def distance(a, b):
    assert len(a) == len(b) == 2560
    return math.sqrt(math.fsum((x-y)**2 for x, y in zip(a, b)))

assert REVIEW.read_bytes() == (ROOT/'review.md').read_bytes()
old, new = (json.loads(p.read_text()) for p in (OLD, NEW))
assert sha(OLD) == 'b69925310ad2b2744e107442b1d283569d106365fda73c5a1ec98f857bf169e9'
assert sha(NEW) == '15a47785bb245ef5ca1eb0388fe013d78036ed12593532875b2cdff3384a2de6'
assert old['model_revision'] == new['model_revision'] == CONFIG.parent.name
assert old['model_config_sha256'] == sha(CONFIG)
config = json.loads(CONFIG.read_text())['text_config']
assert config['layer_types'][17:20] == ['linear_attention', 'linear_attention', 'full_attention']
rows = []
for neither in (r for r in new['records'] if r['condition'] == 'neither'):
    sid = neither['scenario']
    bare = next(r for r in old['records'] if r['scenario'] == sid and r['condition'] == 'bare')
    direct = next(r for r in old['records'] if r['scenario'] == sid and r['condition'] == 'direct_minus')
    assert neither['input_ids'] == direct['input_ids']
    assert len(neither['input_ids']) - len(bare['input_ids']) == 53
    assert neither['final_states']['17'] == bare['final_states']['17']
    assert neither['patch']['next_block_input_exact']
    assert set(neither['hook_calls'].values()) == {1}
    rows.append({'scenario': sid, 'bare_tokens': len(bare['input_ids']), 'donor_tokens': len(neither['input_ids']),
                 'distance': {str(i): distance(neither['final_states'][str(i)], bare['final_states'][str(i)]) for i in (17, 18, 31)},
                 'old_record_keys': sorted(bare), 'new_record_keys': sorted(neither)})
assert len(rows) == 3
protected = [Path(p) for p in ('results/plot.png', 'results/index.md', 'results/index.html', 'data/results.csv')]
cost = Decimal('3.95') * Decimal(360) / Decimal(3600) + Decimal('.955') + Decimal('.150')
assert cost == Decimal('1.50') < Decimal('7.22509672744')
assert 3 * 8 == 24 and 3 * 3 * 2 == 18
result = {'review_bytes_exact': True, 'rows': rows,
          'proposal': {'generations': 24, 'judgments': 18, 'estimated_usd': str(cost),
                       'unreserved_unchanged': '7.22509672744',
                       'remainder_if_authorized': str(Decimal('7.22509672744')-cost),
                       'new_reservation': '0', 'launched': False},
          'layer_types': {str(i): config['layer_types'][i] for i in (17,18,19,31)},
          'source_hashes': {str(p): sha(p) for p in (REVIEW, ROOT/'review.md', OLD, NEW, CONFIG, MODEL, CACHE)},
          'protected_hashes': {str(p): sha(p) for p in protected},
          'scope': 'stdlib-only saved-array arithmetic and installed architecture inspection; no model execution or billing call'}
(ROOT/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
print('RETAINED_CONTEXT_DESIGN_PASS', json.dumps(result))
