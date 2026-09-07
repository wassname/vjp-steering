"""Inventory equality in this run only; retain every original score. No API calls."""
import json
from pathlib import Path

root=Path('slop/logs/20260907_j_lens_additive_concepts')
d=json.loads((root/'generation.json').read_text())
js=[json.loads(l) for l in (root/'judgments.jsonl').read_text().splitlines()]
rows=[]
for r in d['records']:
    b=next(b for b in d['reused_records'] if b['scenario']==r['scenario'] and b['condition']=='bare')
    text_equal=r['text']==b['text']
    token_equal=r['generated_ids']==b['generated_ids'] if 'generated_ids' in r and 'generated_ids' in b else None
    for j in [j for j in js if j['vignette']==r['scenario'] and j['condition']==r['condition']]:
        rows.append({'scenario':r['scenario'],'side':r['side'],'order':j['order'],'text_equal':text_equal,'token_equal':token_equal,'effect':j['exported_effect'],'cache_key':j['cache_key']})
assert len(rows)==60
out={'scope':'This existing30pairs/60judgments only; original scores unchanged','rows':rows,'groups':{}}
for side in ('+C','-C'):
    ss=[r for r in rows if r['side']==side];eq=[r for r in ss if r['text_equal']]
    result={'pairs':15,'judgments':len(ss),'text_equal_pairs':len(eq)//2,'token_equal_pairs':sum(r['token_equal'] is True for r in ss)//2,
        'missing_token_pair_fields':sum(r['token_equal'] is None for r in ss)//2,
        'text_equal_nonzero_judgments':sum(r['effect']!=0 for r in eq),'text_equal_nonzero_pairs':len({r['scenario'] for r in eq if r['effect']!=0}),
        'full_paired_mean':sum(r['effect'] for r in ss)/len(ss),
        'text_equal_contribution_to_full_paired_mean':sum(r['effect'] for r in eq)/len(ss)}
    for order in ('AB','BA'):
        group=[r for r in ss if r['order']==order];equal=[r for r in group if r['text_equal']]
        result[order]={'full_mean':sum(r['effect'] for r in group)/len(group),'text_equal_effect_sum':sum(r['effect'] for r in equal),
            'text_equal_contribution_to_full_mean':sum(r['effect'] for r in equal)/len(group)}
    out['groups'][side]=result
(root/'equal-response-inventory.json').write_text(json.dumps(out,indent=2)+'\n')
print('EQUAL_RESPONSE_INVENTORY_PASS',json.dumps(out['groups']))
for r in rows:
    if r['text_equal']:print('EQUAL_PAIR',json.dumps(r))
