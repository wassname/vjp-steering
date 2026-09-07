"""Offline source/seed evidence audit, including every raw judge quote and token delivery."""
import json
from pathlib import Path
import statistics
import sys
sys.path[:0]=['scripts','scripts/scratch','src']
import judge
from vjp_steering.results_dev import sha

folder=Path(sys.argv[1]);data=json.loads((folder/'generation.json').read_text())
assert len(data['records'])==90 and len(data['identity_controls'])==2
sampler=json.loads(Path('slop/logs/20260907_j_lens_matched_random/sampler.json').read_text())
assert data['sampler_sha256']==sha('slop/logs/20260907_j_lens_matched_random/sampler.json')
summary={'seed':data['seed'],'runtime':data['runtime'],'groups':{},'identities':2,'judgments':180,'cost_usd':0,'equal_anomalies':[]}
lines=['# Complete random-seed audit: all outputs and raw judge evidence']
for alpha in (1,2,4):
    js=[json.loads(l) for l in (folder/f'alpha{alpha}'/'judgments.jsonl').read_text().splitlines()]
    assert len(js)==60 and len({(j['vignette'],j['side'],j['order']) for j in js})==60
    summary['cost_usd']+=sum(j['cost_usd'] for j in js)
    for side in ('+C','-C'):
        rs=[r for r in data['records'] if r['alpha']==alpha and r['side']==side]
        ms=[m for r in rs for m in r['measurements']]
        for r in rs:
            bare=next(b for b in data['reused_records'] if b['scenario']==r['scenario'] and b['condition']=='bare')
            assert r['input_ids']==bare['input_ids'] and r['rendered']==bare['rendered'] and all(r['attention_mask'])
            assert len(r['measurements'])==len(r['generated_ids'])
            assert [m['sequence_length'] for m in r['measurements']]==[len(r['input_ids'])]+[1]*(len(r['generated_ids'])-1)
            lines += [f"## alpha{alpha} {side} {r['scenario']}", '```text\n'+r['rendered']+'\n```','Baseline: '+bare['text'],'Random: '+r['text']]
            for j in [j for j in js if (j['vignette'],j['side'])==(r['scenario'],side)]:
                row=dict(bare=bare['text'],steered=r['text'],prompt=r['prompt'],vignette=r['scenario'],side=side,
                         run=j['run'],method=r['method'],source=j['source'])
                assert judge.judge_prompt(row,j['order'])==j['prompt'] and judge.cache_key(row,j['order'],0)==j['cache_key']
                assert j['raw_attempts'][-1]==j['raw']
                record={k:j[k] for k in ('order','exported_effect','cache_key','raw')}
                lines.append(json.dumps(record,ensure_ascii=False))
                if bare['text']==r['text'] and j['exported_effect']!=0:
                    assert bare['generated_ids']==r['generated_ids']
                    summary['equal_anomalies'].append(dict(alpha=alpha,side=side,scenario=r['scenario'],**record))
        wanted=alpha*sampler['requested_base_norm']
        for m in ms:
            assert m['nonfinal_exact'] and m['next_block_exact'] and m['actual_norm']>0 and m['direction_cosine']>.99
            assert abs(m['desired_norm']-wanted)<1e-6 and m['signed_alpha']==alpha*(1 if side=='+C' else -1)
            assert m['rounding_error_norm']<=m['rounding_bound']
        effects={o:statistics.mean(j['exported_effect'] for j in js if j['side']==side and j['order']==o) for o in ('AB','BA')}
        summary['groups'][f'{alpha}{side}']=dict(calls=len(ms),requested_norm=wanted,actual_min=min(m['actual_norm'] for m in ms),
            actual_median=statistics.median(m['actual_norm'] for m in ms),actual_max=max(m['actual_norm'] for m in ms),
            max_relative_error=max(m['norm_error']/wanted for m in ms),AB=effects['AB'],BA=effects['BA'],paired=(effects['AB']+effects['BA'])/2,
            health={k:sum(r['health'][0][k] for r in rs) for k in ('unfinished','role_leaks','repeated')})
for r in data['identity_controls']:
    bare=next(b for b in data['reused_records'] if b['scenario']==r['scenario'] and b['condition']=='bare')
    assert r['identity_exact'] and r['generated_ids']==bare['generated_ids'] and all(m['actual_norm']==0 for m in r['measurements'])
(folder/'audit.json').write_text(json.dumps(summary,indent=2)+'\n')
(folder/'audit.md').write_text('\n\n'.join(lines)+'\n')
print('RANDOM_AUDIT_PASS',json.dumps(summary))
