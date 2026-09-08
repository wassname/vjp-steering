"""Approved v2: counterbalance every consumer/label, preserve frozen v1 cues.
Revision is due to internal design defects, not benchmark lexical audit findings.
"""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).parent
V1=ROOT.parent
old=json.loads((V1/'freeze.json').read_text())
assert hashlib.sha256((V1/'corpus.jsonl').read_bytes()).hexdigest()==old['corpus_sha256']
rows=[]
for original in map(json.loads,(V1/'corpus.jsonl').read_text().splitlines()):
    for order in (0,1):
        r=dict(original)
        # New consumer tasks occur only in withheld_source, never calibration.
        if r['split']=='source_calibration' and r['consumer'] in ('storage','notification'):
            replacement={'storage':('routing',['route through gate','route through bypass']),
                         'notification':('allocation',['allocate two counters','allocate zero counters'])}
            r['consumer'],actions=replacement[r['consumer']]
            r['actions_valid_invalid']=actions[::-1] if r['world']%2 else actions
        r['option_order']=order
        r['options']=r['actions_valid_invalid'][::(-1 if order else 1)]
        r['id']=f'tv2_{r["cue_family"]}_{r["world"]}_{r["consumer"]}_o{order}_{int(r["valid"])}'
        r['pair_id']=r['id'].rsplit('_',1)[0]
        r['expected']='AB'[r['options'].index(r['actions_valid_invalid'][0 if r['valid'] else 1])]
        cue=f'{r["rule"]}\n{r["evidence"]}' if r['world']%2==0 else f'{r["evidence"]}\n{r["rule"]}'
        actions=r['actions_valid_invalid'];options=r['options']
        r['prompt']=('This is a self-contained rule world; the stated requirement is the only criterion for this operation.\n'
                     +cue+'\n'+f'When the requirement holds, {actions[0]}; otherwise, {actions[1]}.\n'
                     +f'Which action follows? A: {options[0]}. B: {options[1]}. Reply with one letter only.')
        r['provenance']='PI synthetic rule-world v2; unchanged v1 rules/evidence; order/consumer partition correction'
        r['v1_parent_id']=original['id']
        rows.append(r)
corpus=''.join(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in rows).encode()
if (ROOT/'freeze.json').exists():
    assert (ROOT/'corpus.jsonl').read_bytes()==corpus,'Do not overwrite frozen v2'
else:
    (ROOT/'corpus.jsonl').write_bytes(corpus)
    manifest={'version':2,'author':'PI/OpenAI Codex','rows':len(rows),
        'phase':'frozen before v2 benchmark overlap audit; v1 overlap already known and retained',
        'parent_corpus_sha256':old['corpus_sha256'],
        'corpus_sha256':hashlib.sha256(corpus).hexdigest(),
        'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'revision_reason':'per-consumer answer-position confound and calibration consumer exposure; supervisor approved',
        'split_ids':{s:[r['id'] for r in rows if r['split']==s] for s in old['split_ids']},
        'rule':'No lexical or world-content revision; no row dropped based on benchmark overlap.'}
    (ROOT/'freeze.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('CORPUS_V2_FREEZE_PASS',hashlib.sha256(corpus).hexdigest(),len(rows))
