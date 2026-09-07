"""Independent saved-array/raw-judge verification; no inference or scoring changes."""
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from statistics import mean
import subprocess
import sys
import numpy as np
sys.path[:0]=['scripts','src']
import judge
import export

ROOT=Path('slop/logs/20260907_j_lens_donor_context')
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def lines(p):return [json.loads(l) for l in p.read_text().splitlines()]
data=load(ROOT/'generation.json');pre=load(ROOT/'preflight.json')
ref=load(Path('slop/logs/20260907_j_lens_transfer_probe/generation.json'))
assert all(sha(p)==h for p,h in pre['protected_hashes'].items())
assert all(sha(p)==h for p,h in data['source_hashes'].items())
modal_log=(ROOT/'modal.log').read_text().splitlines()
judge_log=(ROOT/'judge.log').read_text().splitlines()
assert modal_log[-1]==judge_log[-1]=='EXIT_CODE=0'
config=json.loads(next(l.removeprefix('DONOR_CONFIG ') for l in modal_log if l.startswith('DONOR_CONFIG ')))
assert all(data[k]==v for k,v in config.items() if k!='records')
printed=[json.loads(l.removeprefix('DONOR_RESPONSE ')) for l in modal_log if l.startswith('DONOR_RESPONSE ')]
assert len(printed)==15 and all(all(r[k]==v for k,v in p.items()) for p,r in zip(printed,data['records']))
source=subprocess.check_output(['git','show',data['source_revision']+':scripts/scratch/j_lens_donor_context.py'])
assert hashlib.sha256(source).hexdigest()==data['implementation_sha256']==pre['implementation_sha256']
scenarios=sorted({r['scenario'] for r in ref['records']})
arms=('unpatched','neither','parallel','complement','both')
assert len(data['records'])==15 and {(r['scenario'],r['condition']) for r in data['records']}=={(s,a) for s in scenarios for a in arms}
js=lines(ROOT/'judgments.jsonl');transport=lines(ROOT/'judge-transport.jsonl')
assert len(js)==len(transport)==18
assert js==[json.loads(l.removeprefix('DONOR_JUDGMENT ')) for l in judge_log if l.startswith('DONOR_JUDGMENT ')]
assert len({(j['vignette'],j['condition'],j['order']) for j in js})==18
axis=np.asarray(data['unit_axis'],dtype=np.float64);axis/=np.linalg.norm(axis)
steps=[];scores=[];pairs=[];identical=[]
text=['# Full donor-context comparisons and raw judge rationales','PI/OpenAI Codex. Fixed three selected donor contexts,15 generations,18 judgments. No historical scores changed. Full transport requests/responses: judge-transport.jsonl; full generation arrays: generation.json.']
for scenario in scenarios:
    old={r['condition']:r for r in ref['records'] if r['scenario']==scenario}
    rs={r['condition']:r for r in data['records'] if r['scenario']==scenario}
    base=rs['unpatched'];hb=np.asarray(old['bare']['patch']['after']);hd=np.asarray(old['direct_minus']['patch']['after'])
    assert base['generated_ids']==old['direct_minus']['generated_ids'] and base['final_states']==old['direct_minus']['final_states']
    p=axis*(axis@(hd-hb))
    text+=['## '+scenario,'```text',base['rendered'],'```']
    for arm in arms:
        r=rs[arm];m=r['patch'];v=r['delivery']
        assert r['input_ids']==base['input_ids']==old['direct_minus']['input_ids'] and r['rendered']==base['rendered']
        assert m['before']==hd.tolist() and m['next_block_input_exact']
        assert len(m['all_position_patch_norms'])==len(r['input_ids']) and not any(m['all_position_patch_norms'][:-1])
        assert all(n==1 for n in r['hook_calls'].values()) and set(r['hook_calls'])==set(old['direct_minus']['hook_calls'])
        after=np.asarray(m['after']);ideal={'unpatched':hd,'both':hd,'neither':hb,'parallel':hb+p,'complement':hd-p}[arm]
        np.testing.assert_allclose(np.linalg.norm(after-hd),v['actual_norm'],atol=1e-12,rtol=0)
        np.testing.assert_allclose(np.linalg.norm(after-ideal),v['rounding_error'],atol=1e-12,rtol=0)
        np.testing.assert_allclose(axis@after,v['coordinate_after'],atol=1e-12,rtol=0)
        assert v['rounding_error']<=v['rounding_bound']
        if arm in ('unpatched','both'):
            assert m['after']==hd.tolist() and not any(m['all_position_patch_norms'])
            assert r['first_token']['max_abs_logit_change']==r['first_token']['kl_from_donor']==0
            assert r['generated_ids']==base['generated_ids'] and r['final_states']==base['final_states']
        if arm=='both':assert r['identity_exact']
        if arm=='neither':assert m['after']==hb.tolist()
        steps.append({'scenario':scenario,'arm':arm,**v,**{k:r['first_token'][k] for k in ('max_abs_logit_change','kl_from_donor')}})
        text+=['### '+arm,r['text'],'Health: '+json.dumps(r['health']),'Delivery: '+json.dumps(v)]
        if arm in ('unpatched','both'):continue
        found=[]
        row={'bare':base['text'],'steered':r['text'],'prompt':r['prompt'],'vignette':scenario,'side':'-C'}
        for order in ('AB','BA'):
            j=next(j for j in js if (j['vignette'],j['condition'],j['order'])==(scenario,arm,order))
            t=next(t for t in transport if (t['scenario'],t['condition'],t['order'])==(scenario,arm,order))
            assert j['prompt']==judge.judge_prompt(row,order) and j['cache_key']==judge.cache_key(row,order,0)
            assert t['request']=={'model':judge.MODEL,'messages':[{'role':'user','content':j['prompt']}],
                'temperature':.7,'max_tokens':1024,'response_format':judge.FORMAT,
                'extra_body':{'reasoning':{'enabled':False},'provider':judge.provider_route(0)}}
            assert t['response']['choices'][0]['message']['content']==j['raw'] and j['raw_attempts']==[j['raw']]
            raw=json.loads(j['raw']);assert all(j['judgment'][k]==v for k,v in raw.items())
            b,a=('A','B') if order=='AB' else ('B','A')
            effect=raw['on_axis_'+b]-raw['on_axis_'+a]
            assert abs(effect-j['exported_effect'])<1e-12 and abs(effect-export.signed_axis_effect('-C',[export.score_cell(j)]))<1e-12
            score={'scenario':scenario,'arm':arm,'order':order,'donor_score':raw['on_axis_'+b],
                'arm_score':raw['on_axis_'+a],'signed_effect':effect,'donor_damage':raw['off_axis_'+b],
                'arm_damage':raw['off_axis_'+a],'evidence':raw['evidence'],'cache_key':j['cache_key']}
            scores.append(score);found.append(score)
            text+=['Raw '+order+': '+j['raw'],'Mapped: '+json.dumps(score)]
        if r['text']==base['text']:
            assert r['generated_ids']==base['generated_ids'];identical.append({'scenario':scenario,'arm':arm,'effects':[s['signed_effect'] for s in found]})
        pairs.append({'scenario':scenario,'arm':arm,'AB':found[0]['signed_effect'],'BA':found[1]['signed_effect'],
                      'mean':mean(s['signed_effect'] for s in found),'strict_reversal':found[0]['signed_effect']*found[1]['signed_effect']<0})
for name,rows in [('delivery.csv',steps),('scores.csv',scores),('paired.csv',pairs)]:
    with (ROOT/name).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(ROOT/'complete-response-audit.md').write_text('\n\n'.join(text)+'\n')
app='ap-3s6V3bMLZShNPgt8juODa1'
status=next(a for a in load(ROOT/'app-status.json') if a['app_id']==app)
assert status['state']=='stopped' and status['tasks']=='0'
billing=[r for r in load(ROOT/'billing-report.json') if r['object_id']==app]
assert {r['resource'] for r in billing}=={'H100','CPU','Memory'}
metered=sum(Decimal(r['cost']) for r in billing)
api=sum(Decimal(str(j['cost_usd'])) for j in js)
assert api==sum(Decimal(str(t['response']['usage']['cost'])) for t in transport)
budget={'app':app,'app_state':status,'metered_rows':billing,'metered_Modal_usd':str(metered),
    'reported_judge_usd':str(api),'observed_total_usd':str(metered+api),'allocated_usd':'1.20',
    'unreserved_usd':'7.22509672744','unused_allocation_retained_usd':str(Decimal('1.20')-metered-api),
    'cumulative_reported_API_usd':str(Decimal('1.08584037412')+api),
    'late_billing_reserve_usd':'.25','other_reserves':'unchanged','invoice_final':False,'new_paid_work_authorized':False}
(ROOT/'budget.json').write_text(json.dumps(budget,indent=2)+'\n')
summary={'responses':15,'judgments':18,'same_context_controls':3,'saved_donor_replay_exact':3,'both_identity_exact':3,
    'hook_calls_per_layer':1,'protected_files':len(pre['protected_hashes']),'paired_scores':pairs,
    'identical_answer_cells':identical,'runtime':data['runtime'],'metered_Modal_usd':str(metered),'judge_usd':str(api),
    'generation_sha256':sha(ROOT/'generation.json'),'judgments_sha256':sha(ROOT/'judgments.jsonl')}
(ROOT/'audit.json').write_text(json.dumps(summary,indent=2)+'\n')
print('DONOR_AUDIT_PASS',json.dumps(summary),flush=True)
