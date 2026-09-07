"""Offline saved-result invariants, separate from generation/report. PI/OpenAI Codex."""
import hashlib
import json
from pathlib import Path
import subprocess

root=Path('slop/logs/20260907_j_lens_additive_concepts')
d=json.loads((root/'generation.json').read_text());source=Path('slop/logs/20260907_j_lens_named_concepts/generation.json')
assert hashlib.sha256(source.read_bytes()).hexdigest()==d['named_source_sha256']
source_data=json.loads(source.read_text())
assert source_data['model_revision']==d['model_revision']=='851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a'
assert d['fixed_alpha']==1
raw=[json.loads(l.removeprefix('ADDITIVE_RESPONSE ')) for l in (root/'modal.log').read_text().splitlines() if l.startswith('ADDITIVE_RESPONSE ')]
assert len(raw)==32
expected={(r['scenario'],r['side']) for r in d['records']}
ids={r['scenario'] for r in d['reused_records'] if r['condition']=='bare'}
assert expected=={(i,s) for i in ids for s in ('+C','-C')} and len(ids)==15 and len(d['records'])==30
for r in d['records']+d['identity_controls']:
    matching=[x for x in raw if x['scenario']==r['scenario'] and x['side']==r['side'] and x.get('identity_exact',False)==r.get('identity_exact',False)]
    assert len(matching)==1 and matching[0]['text']==r['text'] and matching[0]['rendered']==r['rendered']
    assert len(r['measurements'])==len(r['generated_ids'])
    bare=next(x for x in d['reused_records'] if x['scenario']==r['scenario'] and x['condition']=='bare')
    assert r['input_ids']==bare['input_ids'] and r['rendered']==bare['rendered']
    assert r['attention_mask']==[1]*len(r['input_ids'])
    if r.get('identity_exact'): assert r['generated_ids']==bare['generated_ids'] and r['text']==bare['text']
    for m in r['measurements']:
        assert m['nonfinal_exact'] and m['next_block_exact']
        assert m['actual_norm']==0 if r.get('identity_exact') else m['actual_norm']>0
        assert abs(m['desired_norm']-(0 if r.get('identity_exact') else d['contrast_norm']))<1e-7
        assert m['signed_alpha']==(0 if r.get('identity_exact') else (1 if r['side']=='+C' else -1))
js=[json.loads(l) for l in (root/'judgments.jsonl').read_text().splitlines()]
assert len(js)==60 and {(j['vignette'],j['side'],j['order']) for j in js}=={(i,s,o) for i in ids for s in ('+C','-C') for o in ('AB','BA')}
for j in js:
    r=next(r for r in d['records'] if r['scenario']==j['vignette'] and r['side']==j['side'])
    bare=next(r for r in d['reused_records'] if r['scenario']==j['vignette'] and r['condition']=='bare')
    a,b=(bare['text'],r['text']) if j['order']=='AB' else (r['text'],bare['text'])
    assert j['prompt'].split('Response A:\n',1)[1]==a+'\n\nResponse B:\n'+b
    score=j['judgment'];difference=score['on_axis_B']-score['on_axis_A']
    expected_effect=difference*(1 if j['order']=='AB' else -1)*(1 if j['side']=='+C' else -1)
    assert abs(j['exported_effect']-expected_effect)<1e-9
    assert j['rubric_version']=='results-demo-perresponse-syco-v7'
    assert j['model']=='deepseek/deepseek-v4-flash-0731'
r=next(r for r in d['records'] if r['scenario'].endswith('phys_pnf_02') and r['side']=='-C')
b=next(b for b in d['reused_records'] if b['scenario']==r['scenario'] and b['condition']=='bare')
assert r['text']==b['text'] and r['generated_ids']==b['generated_ids']
j=next(j for j in js if j['vignette']==r['scenario'] and j['side']=='-C' and j['order']=='AB')
assert 'check the department' not in j['prompt'] and 'check the department' in j['judgment']['evidence']
health={k:sum(r['health'][0][k] for r in d['records']) for k in ('unfinished','role_leaks','repeated')}
result={'generation_sha256':hashlib.sha256((root/'generation.json').read_bytes()).hexdigest(),'all32log_response_matches':True,
    'coverage15x2':True,'judgments60_pair_text_and_mapping_exact':True,'DNL_minus_baseline_text_and_ids_exact':True,
    'DNL_AB_evidence_invents_absent_quote':True,'health':health,'actual_treatment_calls':sum(len(r['measurements']) for r in d['records']),
    'identity_calls':sum(len(r['measurements']) for r in d['identity_controls'])}
(root/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('ADDITIVE_VERIFY_PASS',json.dumps(result))
