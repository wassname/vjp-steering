"""Reconstruct saved judge requests/keys without API calls. PI/OpenAI Codex."""
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
sys.path[:0]=['scripts','src']
import judge

root=Path('slop/logs/20260907_j_lens_additive_concepts')
data=json.loads((root/'generation.json').read_text())
js=[json.loads(l) for l in (root/'judgments.jsonl').read_text().splitlines()]
assert subprocess.check_output(['git','show',data['source_revision']+':scripts/judge.py'])==Path('scripts/judge.py').read_bytes()
assert subprocess.check_output(['git','show',data['source_revision']+':scripts/scratch/j_lens_norm_matched_gp.py'])==Path('scripts/scratch/j_lens_norm_matched_gp.py').read_bytes()
records=[]
for j in js:
    r=next(r for r in data['records'] if r['scenario']==j['vignette'] and r['side']==j['side'])
    bare=next(b for b in data['reused_records'] if b['scenario']==r['scenario'] and b['condition']=='bare')
    row={'bare':bare['text'],'steered':r['text'],'prompt':r['prompt'],'vignette':r['scenario'],'side':r['side'],'run':'norm-matched-gp16-dev15','method':r['method'],'source':str(root/'generation.json')}
    assert judge.judge_prompt(row,j['order'])==j['prompt']
    assert judge.cache_key(row,j['order'],0)==j['cache_key']
    assert len(j['raw_attempts'])==1 and j['raw_attempts'][0]==j['raw']
    if r['scenario'].endswith('phys_pnf_02') and r['side']=='-C':
        assert bare['text']==r['text'] and bare['generated_ids']==r['generated_ids']
        captured=[]
        async def create(**kwargs):
            captured.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=j['raw'],reasoning=None))],usage=SimpleNamespace(cost=j['cost_usd']),provider=j['provider'])
        client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        replay=asyncio.run(judge.judge_one(client,row,j['order'],0))
        assert len(captured)==1 and captured[0]['messages']==[{'role':'user','content':j['prompt']}]
        assert replay['raw']==j['raw'] and replay['judgment']==j['judgment'] and replay['cache_key']==j['cache_key']
        records.append({'order':j['order'],'baseline_text':bare['text'],'steered_text':r['text'],
            'baseline_generated_ids':bare['generated_ids'],'steered_generated_ids':r['generated_ids'],
            'text_sha256':hashlib.sha256(r['text'].encode()).hexdigest(),'request_reconstructed_offline':captured[0],
            'saved_record':j,'request_replay_matches':True})
assert len(records)==2 and records[0]['saved_record']['cache_key']!=records[1]['saved_record']['cache_key']
assert records[0]['saved_record']['prompt']==records[1]['saved_record']['prompt']
(root/'DNL-exact-requests-and-records.json').write_text(json.dumps(records,indent=2)+'\n')
result={'all60_prompt_reconstruction_exact':True,'all60_cache_keys_exact':True,'single_raw_attempt_each':True,
    'DNL_same_text_ids_and_serialized_prompt_AB_BA':True,'DNL_order_keys_differ':True,'DNL_offline_client_fixture_pass':True,
    'judge_source_sha256':hashlib.sha256(Path('scripts/judge.py').read_bytes()).hexdigest(),
    'limit':'Offline client replay, NOT captured HTTP wire/provider request IDs. Original raw content/usage and serialized prompt retained.'}
(root/'judge-identity-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print('JUDGE_IDENTITY_AUDIT_PASS',json.dumps(result))
for r in records:
    j=r['saved_record'];print('DNL_RAW',r['order'],j['cache_key'],j['exported_effect'],j['raw'])
