"""Verify one projection-removal run and unchanged AB/BA attribution; no calls."""
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
sys.path[:0]=['scripts','scripts/scratch','src']
import judge
import export

ROOT=Path('slop/logs/20260907_j_lens_projection_removal')
OLD=Path('slop/logs/20260907_j_lens_single_concept')
def load(p):return json.loads(p.read_text())
def lines(p):return [json.loads(l) for l in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
data=load(ROOT/'generation.json');old=load(OLD/'generation.json');js=lines(ROOT/'judgments.jsonl');prior=lines(OLD/'judgments.jsonl')
assert len(data['records'])==15 and len(data['identity_controls'])==1 and len(js)==30
assert len({(j['vignette'],j['order']) for j in js})==30
assert data['projection_removal'] and data['fixed_alpha']==1
executed=subprocess.check_output(['git','show',data['source_revision']+':scripts/scratch/j_lens_additive_concepts.py'])
assert hashlib.sha256(executed).hexdigest()==data['implementation_sha256']
assert data['reused_records']==old['reused_records']
checks=load(ROOT/'offline-bf16.json')
assert checks['source_sha256']==data['named_source_sha256']
assert data['contrast']==checks['vector'] and data['implementation_sha256']==checks['implementation_sha256']
# Publication was separately authorized after the initial immutable-output audit.
# Raw evidence stays immutable; display_check.py verifies the authorized point append.
protected={p:h for p,h in checks['immutable_hashes'].items() if not p.startswith('results/')}
assert all(sha(Path(p))==h for p,h in protected.items())
steps=[];cells=[];pairs=[];equal_anomalies=[]
text=['# Complete projection-removal responses and raw judgments','All15 scenarios retained. Existing scores/public outputs unchanged. Prior subtraction is single-concept alpha4; this removal is fraction1, not norm-matched.']
for r in data['records']+data['identity_controls']:
    bare=next(b for b in data['reused_records'] if b['condition']=='bare' and b['scenario']==r['scenario'])
    ms=r['measurements'];identity=r.get('identity_exact',False)
    assert r['side']=='-C' and r['input_ids']==bare['input_ids'] and r['rendered']==bare['rendered']
    assert len(ms)==len(r['generated_ids'])
    assert [m['sequence_length'] for m in ms]==[len(r['input_ids'])]+[1]*(len(ms)-1)
    for m in ms:
        assert m['operator']=='projection_removal' and m['removal_fraction']==(0 if identity else 1)
        assert m['nonfinal_exact'] and m['next_block_exact'] and m['position']==m['sequence_length']-1
        assert m['rounding_error_norm']<=m['rounding_bound'] and m['orthogonal_change_norm']<=m['rounding_bound']
        if identity:
            assert m['actual_norm']==m['desired_norm']==0 and m['coordinate_before']==m['coordinate_after']
        else:
            assert abs(m['desired_norm']-abs(m['coordinate_before']))<1e-5
            assert abs(m['coordinate_after'])<=m['rounding_bound']
        steps.append({'scenario':r['scenario'],'identity':identity,**m})
    if identity:
        assert r['generated_ids']==bare['generated_ids'] and r['text']==bare['text']
        continue
    previous=next(t for t in old['records'] if t['scenario']==r['scenario'] and t['side']=='-C')
    same = r['text']==bare['text']
    assert (r['generated_ids']==bare['generated_ids'])==same
    text+=['## '+r['scenario'],'```text',r['rendered'],'```','### Baseline',bare['text'],'### Prior constant subtraction alpha4',previous['text'],'### Projection removal fraction1',r['text'],'Health: '+json.dumps(r['health'])]
    found=[]
    for order in ('AB','BA'):
        new=next(j for j in js if j['vignette']==r['scenario'] and j['order']==order)
        previous_j=next(j for j in prior if j['vignette']==r['scenario'] and j['order']==order and j['side']=='-C')
        row={'bare':bare['text'],'steered':r['text'],'prompt':r['prompt'],'vignette':r['scenario'],'side':'-C'}
        assert judge.judge_prompt(row,order)==new['prompt'] and judge.cache_key(row,order,0)==new['cache_key']
        assert len(new['raw_attempts'])==1 and new['raw_attempts'][0]==new['raw']
        effect=export.signed_axis_effect('-C',[export.score_cell(new)])
        assert abs(effect-new['exported_effect'])<1e-12
        b,t=('A','B') if order=='AB' else ('B','A')
        n,p=new['judgment'],previous_j['judgment']
        baseline=n['on_axis_'+b]-p['on_axis_'+b]
        steered=-(n['on_axis_'+t]-p['on_axis_'+t])
        total=effect-previous_j['exported_effect']
        assert abs(total-baseline-steered)<1e-12
        cell={'scenario':r['scenario'],'order':order,'new_effect':effect,'old_effect':previous_j['exported_effect'],
            'baseline_contribution':baseline,'steered_contribution':steered,'new_minus_old':total,
            'new_bare_score':n['on_axis_'+b],'new_steered_score':n['on_axis_'+t],
            'old_bare_score':p['on_axis_'+b],'old_steered_score':p['on_axis_'+t],
            'off_steered_minus_bare':n['off_axis_'+t]-n['off_axis_'+b],
            'new_cache_key':new['cache_key'],'old_cache_key':previous_j['cache_key']}
        cells.append(cell);found.append(cell)
        text+=['Mapped scores/attribution: '+json.dumps(cell),'New raw response: '+new['raw'],'Prior raw response: '+previous_j['raw']]
        if same and abs(effect)>1e-12:equal_anomalies.append({'scenario':r['scenario'],'order':order,'effect':effect,'raw':new['raw']})
    pairs.append({'scenario':r['scenario'],'AB':found[0]['new_effect'],'BA':found[1]['new_effect'],
        'paired':statistics.mean(c['new_effect'] for c in found),'prior_paired':statistics.mean(c['old_effect'] for c in found),
        'damage':abs(statistics.mean(c['off_steered_minus_bare'] for c in found)),
        'baseline_equal':same,'baseline_contribution':statistics.mean(c['baseline_contribution'] for c in found),
        'steered_contribution':statistics.mean(c['steered_contribution'] for c in found)})
active=[m for m in steps if not m['identity']]
def span(k):
    vals=[m[k] for m in active]
    return {'min':min(vals),'median':statistics.median(vals),'max':max(vals)}
summary={'runtime':data['runtime'],'source_revision':data['source_revision'],'judgments':len(js),
    'cost_usd':sum(j['cost_usd'] for j in js),'AB':statistics.mean(p['AB'] for p in pairs),'BA':statistics.mean(p['BA'] for p in pairs),
    'paired':statistics.mean(p['paired'] for p in pairs),'damage':statistics.mean(p['damage'] for p in pairs),
    'baseline_contribution':statistics.mean(c['baseline_contribution'] for c in cells),
    'steered_contribution':statistics.mean(c['steered_contribution'] for c in cells),
    'new_minus_old':statistics.mean(c['new_minus_old'] for c in cells),
    'improved_vs_previous_scenarios':sum(p['paired']<p['prior_paired']-1e-12 for p in pairs),
    'strict_order_reversals':sum(p['AB']*p['BA']<0 for p in pairs),'baseline_equal_scenarios':sum(p['baseline_equal'] for p in pairs),
    'equal_anomalies':equal_anomalies,'treatment_calls':len(active),'identity_calls':len(steps)-len(active),
    'zero_actual_updates':sum(m['actual_norm']==0 for m in active),
    'coordinate_before':span('coordinate_before'),'coordinate_after':span('coordinate_after'),
    'requested_norm':span('desired_norm'),'delivered_norm':span('actual_norm'),
    'max_abs_residual_coordinate':max(abs(m['coordinate_after']) for m in active),
    'max_orthogonal_change_norm':max(m['orthogonal_change_norm'] for m in active),
    'health':{k:sum(r['health'][0][k] for r in data['records']) for k in ('unfinished','role_leaks','repeated')},
    'immutable_files':len(protected), 'public_output_append_check':'display-check.log',
    'limits':'Online coordinates/error metrics are recorded by the tested hook; hidden states were not persisted for independent online FP64 replay. Prior random norms differ. Attribution is arithmetic, not corrected scores.'}
for name,rows in (('steps.csv',steps),('scores.csv',cells),('paired.csv',pairs)):
    with (ROOT/name).open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
(ROOT/'complete-response-audit.md').write_text('\n\n'.join(text)+'\n')
(ROOT/'audit.json').write_text(json.dumps(summary,indent=2)+'\n')
print('PROJECTION_EXECUTION_AUDIT_PASS',json.dumps(summary))
