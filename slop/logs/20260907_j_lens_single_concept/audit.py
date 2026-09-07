"""Exact existing-score comparison for the single-component run; no paid calls."""
import hashlib
import json
from pathlib import Path
from statistics import mean
import sys
sys.path[:0]=['src','scripts','scripts/scratch']
import judge
import j_lens_additive_concepts as additive
from vjp_steering.results_dev import load_points,sha

root=Path(__file__).parent
base_manifest=Path('slop/logs/20260907_j_lens_judged_display/manifest.json')
manifest,oldpoints=load_points(base_manifest)
prior_hashes={str(p):sha(p) for p in [Path('data/results.csv'),base_manifest]+[Path(a[k]) for a in manifest['artifacts'] for k in ('generation','judgments')]}
new=dict(method='single sycophancy GP',seed=None,generation=str(root/'generation.json'),judgments=str(root/'judgments.jsonl'))
for k in ('generation','judgments'):new[k+'_sha256']=sha(new[k])
manifest['artifacts'].append(new)
(root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
_,points=load_points(root/'manifest.json');assert points[:-2]==oldpoints and len(points)==38
(root/'points.json').write_text(json.dumps(points,indent=2)+'\n')
data=json.loads((root/'generation.json').read_text());source,v=additive.source_contrast(True)
assert data['single_concept'] and data['contrast']==v.tolist() and data['fixed_alpha']==4
assert data['named_source_sha256']==additive.SOURCE_SHA
assert data['offline_check_sha256']==sha(root/'offline-bf16.json')
assert len(data['identity_controls'])==2
sets=[]
for a in manifest['artifacts']:
    d=json.loads(Path(a['generation']).read_text())
    if d['fixed_alpha']!=4:continue
    js=[json.loads(l) for l in Path(a['judgments']).read_text().splitlines()]
    sets.append((a,d,js))
comparisons=[];lines=['# All15 scenarios, both signs: baseline / old contrast / five randoms / single component','Raw scores unchanged; alpha4 matched requested norms, reused DEV. No frontier.']
newjs=sets[-1][2]
for r in data['records']:
    bare=next(b for b in data['reused_records'] if b['condition']=='bare' and b['scenario']==r['scenario'])
    assert r['input_ids']==bare['input_ids'] and r['rendered']==bare['rendered'] and all(r['attention_mask'])
    lines.extend(['## '+r['scenario']+' '+r['side'],'```text\n'+r['rendered']+'\n```','Baseline: '+bare['text']])
    row=dict(scenario=r['scenario'],side=r['side'],random=[])
    for a,d,js in sets:
        response=next(x for x in d['records'] if (x['scenario'],x['side'])==(r['scenario'],r['side']))
        cells={j['order']:j for j in js if (j['vignette'],j['side'])==(r['scenario'],r['side'])}
        assert set(cells)=={'AB','BA'}
        effect=mean(c['exported_effect'] for c in cells.values())
        if a['method']=='matched random':row['random'].append(effect)
        else:row['new' if a['method']=='single sycophancy GP' else 'old']=effect
        lines.extend([a['method']+' seed='+str(a['seed'])+': '+response['text']])
        for o,c in cells.items():lines.append(json.dumps({'order':o,'effect':c['exported_effect'],'raw':c['raw']}))
    assert len(row['random'])==5
    row.update(random_mean=mean(row['random']),new_minus_old=row['new']-row['old'],new_minus_random=row['new']-mean(row['random']))
    comparisons.append(row)
    for j in [j for j in newjs if (j['vignette'],j['side'])==(r['scenario'],r['side'])]:
        a,b=(bare['text'],r['text']) if j['order']=='AB' else (r['text'],bare['text'])
        assert j['prompt'].endswith('Response A:\n'+a+'\n\nResponse B:\n'+b)
        request={'bare':bare['text'],'steered':r['text'],'prompt':r['prompt'],'vignette':r['scenario'],'side':r['side']}
        assert judge.cache_key(request,j['order'],0)==j['cache_key']
        assert j['raw']==j['raw_attempts'][-1]
    ms=r['measurements'];assert len(ms)==len(r['generated_ids'])
    assert [m['sequence_length'] for m in ms]==[len(r['input_ids'])]+[1]*(len(ms)-1)
    assert all(m['nonfinal_exact'] and m['next_block_exact'] and m['signed_alpha']==(4 if r['side']=='+C' else -4) and abs(m['desired_norm']-2.8864548206329344)<1e-6 and m['actual_norm']>0 for m in ms)
for r in data['identity_controls']:
    b=next(b for b in data['reused_records'] if b['condition']=='bare' and b['scenario']==r['scenario'])
    assert r['identity_exact'] and r['generated_ids']==b['generated_ids'] and all(m['actual_norm']==0 for m in r['measurements'])
summary={'runtime':data['runtime'],'judging_cost':sum(j['cost_usd'] for j in newjs),'groups':{},'all60_request_keys_exact':True,'new_equal_pairs':sum(r['text']==next(b['text'] for b in data['reused_records'] if b['condition']=='bare' and b['scenario']==r['scenario']) for r in data['records']),'raw_attempts':sum(len(j['raw_attempts']) for j in newjs),'primary_sha':sha('data/results.csv'),'immutable_hashes':prior_hashes}
for side in ('+C','-C'):
    cs=[c for c in comparisons if c['side']==side];x={k:mean(c[k] for c in cs) for k in ('new','old','random_mean','new_minus_old','new_minus_random')}
    x['without_TCA']={k:mean(c[k] for c in cs if c['scenario']!='syco_bullshit_v2_sw_pnf_02') for k in ('new','old','new_minus_old','new_minus_random')}
    x['new_minus_old_positive_scenarios']=sum(c['new_minus_old']>1e-12 for c in cs)
    x['new_minus_old_negative_scenarios']=sum(c['new_minus_old']< -1e-12 for c in cs)
    x['health']={k:sum(r['health'][0][k] for r in data['records'] if r['side']==side) for k in ('unfinished','role_leaks','repeated')}
    summary['groups'][side]=x
assert all(sha(p)==h for p,h in prior_hashes.items())
(root/'comparisons.json').write_text(json.dumps({'summary':summary,'per_scenario':comparisons},indent=2)+'\n')
(root/'complete-comparisons.md').write_text('\n\n'.join(lines)+'\n')
print('SINGLE_AUDIT_PASS',json.dumps(summary))
