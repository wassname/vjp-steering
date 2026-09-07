"""Offline source identity, geometry and measured-scale checks. No model/API call."""
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import torch

root=Path(__file__).resolve().parent
data=json.loads((root/'generation.json').read_text())
assert len(data['records'])==30 and len(data['identity_controls'])==2
source=data['construction'];states=torch.tensor(source['source_states'],dtype=torch.float64)
assert len(states)==102 and source['source_records']==json.loads((root/'source-prompts.json').read_text())
assert hashlib.sha256((root/'reference-verbal-introspection.json').read_bytes()).hexdigest()==source['inventory']['source_sha256']
mean=states[2:].mean(0)
torch.testing.assert_close(mean,torch.tensor(source['baseline_mean']).double(),atol=1e-6,rtol=1e-5)
full=states[:2]-mean
fb=full/full.norm(dim=1,keepdim=True)
torch.testing.assert_close(fb,torch.tensor(source['full_basis']).double(),atol=1e-6,rtol=1e-5)
b=torch.tensor(source['basis'],dtype=torch.float64)
for name,basis in [('j_gp16',b),('full_residual',fb)]:
    dual=torch.linalg.solve(basis@basis.T,basis)
    for i,side in enumerate(('+C','-C')):
        c=states[i]@dual.T
        assert abs(float(c[0]-c[1])-data['targets'][name][side])<1e-5
for i,key in enumerate(('positive','negative')):
    row=source['components'][key];dictionary=torch.tensor(row['dictionary_rows'],dtype=torch.float64)
    component=torch.tensor(row['weights'],dtype=torch.float64)@dictionary
    torch.testing.assert_close(component,torch.tensor(row['component']).double(),atol=1e-5,rtol=1e-4)
    torch.testing.assert_close(b[i],component/component.norm(),atol=1e-6,rtol=1e-5)
ref=Path('slop/logs/20260907_j_lens_dev15_representation/generation.json')
assert hashlib.sha256(ref.read_bytes()).hexdigest()==data['reference_sha256']
assert data['reused_records']==json.loads(ref.read_text())['records']
expected={(r['scenario'],s) for r in data['reused_records'] if r['condition']=='bare' for s in ('+C','-C')}
assert {(r['scenario'],r['side']) for r in data['records']}==expected
logged=[]
for line in (root/'modal.log').read_text().splitlines():
    if line.startswith('NAMED_RESPONSE '):logged.append(json.loads(line[len('NAMED_RESPONSE '):]))
assert len(logged)==32
for r in data['records']+data['identity_controls']:
    lr=[x for x in logged if x['scenario']==r['scenario'] and x['side']==r['side'] and x.get('identity_exact',False)==r.get('identity_exact',False)]
    assert len(lr)==1 and lr[0]['text']==r['text'] and lr[0]['rendered']==r['rendered']
judges=[json.loads(l) for l in (root/'judgments.jsonl').read_text().splitlines()]
assert len(judges)==60 and len({(j['vignette'],j['side'],j['order']) for j in judges})==60
trace=[json.loads(l[len('NORM_JUDGMENT '):]) for l in (root/'judge.log').read_text().splitlines() if l.startswith('NORM_JUDGMENT ')]
assert trace==judges
for j in judges:
    r=next(r for r in data['records'] if r['scenario']==j['vignette'] and r['side']==j['side'])
    bare=next(r for r in data['reused_records'] if r['scenario']==j['vignette'] and r['condition']=='bare')
    a,btext=(bare['text'],r['text']) if j['order']=='AB' else (r['text'],bare['text'])
    assert j['prompt'].endswith('Response A:\n'+a+'\n\nResponse B:\n'+btext)
    assert 'Naming the flaw is the target behaviour.' in j['prompt']
    assert len(j['raw_attempts'])==1
q=lambda a:{'min':min(a),'median':statistics.median(a),'max':max(a)}
scale={}
for side in ('+C','-C'):
    ms=[m for r in data['records'] if r['side']==side for m in r['measurements']]
    bad=[m for m in ms if m['desired_norm'] and m['norm_error']/m['desired_norm']>.05]
    scale[side]={'calls':len(ms),'actual':q([m['actual_norm'] for m in ms]),'reference':q([m['reference_realized_norm'] for m in ms]),
        'absolute_error':q([m['norm_error'] for m in ms]),'zero_actual':sum(m['actual_norm']==0 for m in ms),
        'relative_error_gt5pct':len(bad),'bad_max_desired':max((m['desired_norm'] for m in bad),default=None),
        'relative_max':max(m['norm_error']/m['desired_norm'] for m in ms if m['desired_norm']),
        'nominal_opposes_fixed_side':sum((m['gp_target']-(m['gp_coordinates_before'][0]-m['gp_coordinates_before'][1]))*(1 if side=='+C' else -1)<0 for m in ms),
        'nominal_gp_full_sign_opposition':sum((m['gp_target']-(m['gp_coordinates_before'][0]-m['gp_coordinates_before'][1]))*(m['full_target']-(m['full_coordinates_before'][0]-m['full_coordinates_before'][1]))<0 for m in ms)}
    scale[side]['rounded_zero_rows']=[{'scenario':r['scenario'],**m} for r in data['records'] if r['side']==side for m in r['measurements'] if m['actual_norm']==0]
r=next(r for r in data['records'] if r['scenario']=='syco_bullshit_v2_phys_pnf_02' and r['side']=='-C');ms=r['measurements']
scale['DNL_minus']={'calls':len(ms),'norms':q([m['actual_norm'] for m in ms]),'max_abs_error':max(m['norm_error'] for m in ms),'first_call':ms[0],
    'nominal_opposes_fixed_side':sum(m['gp_target']-(m['gp_coordinates_before'][0]-m['gp_coordinates_before'][1])>0 for m in ms)}
scale['source_exact_inputs']=102;scale['raw_log_responses_exact']=32;scale['raw_judgments_exact']=60
scale['generation_sha256']=hashlib.sha256((root/'generation.json').read_bytes()).hexdigest()
(root/'norm-audit.json').write_text(json.dumps(scale,indent=2)+'\n')
print('NAMED_OFFLINE_PASS',json.dumps(scale))
