"""Offline gates on the actual shared generation and judging routes; no paid calls."""
import asyncio
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
sys.path[:0]=['scripts/scratch','scripts','src']
import torch
import j_lens_donor_context as run
import judge
import export
from transformers import Qwen3_5TextConfig, Qwen3_5ForCausalLM, AutoTokenizer

ref,u=run.sources()
protected={str(p):run.gap.sha(p) for p in [run.REFERENCE,run.PROJECTION,Path('results/plot.png'),Path('results/plot_pareto.png'),Path('results/index.md'),Path('results/index.html'),Path('data/results.csv'),Path('scripts/judge.py')]}
geometry=[]
for scenario in run.gap.SCENARIOS:
    rs={r['condition']:r for r in ref['records'] if r['scenario']==scenario}
    b,d=(torch.tensor(rs[c]['patch']['after'],dtype=torch.bfloat16) for c in ('bare','direct_minus'))
    actual=run.states(b,d,u)
    axis=u.double();axis/=axis.norm()
    p=axis*(axis@(d.double()-b.double()))
    assert torch.equal(actual['both'],d) and torch.equal(actual['neither'],b)
    for arm,ideal in (('parallel',b.double()+p),('complement',d.double()-p)):
        error=float((actual[arm].double()-ideal).norm())
        assert error<.03 and not torch.equal(actual[arm],b if arm=='parallel' else d)
        geometry.append({'scenario':scenario,'arm':arm,'rounding_error':error})
# Local cached tokenizer only: no snapshot/model download. Same tokenization precedes weights remotely.
tokenizer=AutoTokenizer.from_pretrained(run.gap.MODEL,revision=run.gap.REVISION,local_files_only=True)
for r in ref['records']:
    if r['condition']=='direct_minus':
        assert tokenizer(r['rendered'],add_special_tokens=False)['input_ids']==r['input_ids']
print('SAVED_PROVENANCE_PASS',json.dumps({'hashes':run.HASHES,'geometry':geometry,'tokenizer_ids_exact':3}),flush=True)

torch.manual_seed(17)
config=Qwen3_5TextConfig(vocab_size=64,hidden_size=32,intermediate_size=64,num_hidden_layers=3,
    num_attention_heads=2,num_key_value_heads=1,head_dim=16,layer_types=['linear_attention','full_attention','linear_attention'],
    linear_num_key_heads=2,linear_num_value_heads=2,linear_key_head_dim=8,linear_value_head_dim=8,pad_token_id=0,eos_token_id=63)
model=Qwen3_5ForCausalLM(config).eval().bfloat16()
encoded=SimpleNamespace(input_ids=torch.tensor([[1,2,3,4]]))
# BatchEncoding supplies both mapping and attribute interface, like the real tokenizer.
from transformers import BatchEncoding
encoded=BatchEncoding({'input_ids':encoded.input_ids,'attention_mask':torch.ones(1,4,dtype=torch.long)})
u2=torch.randn(32);u2/=u2.norm()
base,first=run.generate(model,encoded,u2,None,max_tokens=4,layer=1)
hd=torch.tensor(base['patch']['after'],dtype=torch.bfloat16)
hb=(hd.float()+torch.randn(32)*.1).bfloat16()
for arm,replacement in run.states(hb,hd,u2).items():
    r,logits=run.generate(model,encoded,u2,replacement,max_tokens=4,layer=1)
    assert all(v==1 for v in r['hook_calls'].values()) and r['patch']['next_block_input_exact']
    assert not any(r['patch']['all_position_patch_norms'][:-1])
    if arm in ('both','unpatched'):
        assert r['generated_ids']==base['generated_ids'] and torch.equal(logits,first)
        assert r['final_states']==base['final_states']
    else:
        assert r['patch']['after']==replacement.float().tolist()
    assert not any(m._forward_hooks or m._forward_pre_hooks for m in model.model.layers)
# Exceptional cleanup: shared hook must remove itself when code inside context raises.
try:
    vector=SimpleNamespace(shared={1:{'basis':u2[None],'dual':u2[None]}})
    with run.transfer.observed_prefill(model,vector,'full_minus',hd[None],0.,{},layer=1):
        raise ValueError('intentional cleanup check')
except ValueError:pass
assert not any(m._forward_hooks or m._forward_pre_hooks for m in model.model.layers)
again,again_logits=run.generate(model,encoded,u2,None,max_tokens=4,layer=1)
assert again['generated_ids']==base['generated_ids'] and torch.equal(again_logits,first)
print('REAL_TINY_HYBRID_PASS fivearms_cached_one_shot_nonfinal_nextblock_identity_and_exception_cleanup',flush=True)

fixture={'records':[]}
for scenario in run.gap.SCENARIOS:
    donor=next(r for r in ref['records'] if r['scenario']==scenario and r['condition']=='direct_minus')
    for arm in run.ARMS:
        fixture['records'].append({**donor,'condition':arm,'identity_exact':arm=='both'})
rows=run.judge_rows(fixture)
for mutate in ('missing','wrong_context','missing_identity'):
    bad=copy.deepcopy(fixture)
    if mutate=='missing':bad['records'].pop()
    elif mutate=='wrong_context':bad['records'][1]['input_ids']=[]
    else:bad['records'][4]['identity_exact']=False
    try:run.judge_rows(bad)
    except AssertionError:pass
    else:raise AssertionError(mutate+' not rejected')

async def check_requests():
    calls=[]
    raw=json.dumps({'on_axis_A':1.2,'on_axis_B':2.3,'off_axis_A':.1,'off_axis_B':.2,'evidence':'offline synthetic scores'})
    response=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=raw))],usage=SimpleNamespace(cost=0),model_dump=lambda:{'offline_fixture':True})
    async def create(**kwargs):
        calls.append(kwargs)
        return response
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    with tempfile.TemporaryDirectory() as td:
        trace=Path(td)/'trace.jsonl'
        for row in rows:
            for order in ('AB','BA'):
                r=await run.judge_cell(client,row,order,trace)
                assert r['prompt']==judge.judge_prompt(row,order) and r['cache_key']==judge.cache_key(row,order,0)
                assert calls[-1]=={'model':judge.MODEL,'messages':[{'role':'user','content':r['prompt']}],
                    'temperature':.7,'max_tokens':1024,'response_format':judge.FORMAT,
                    'extra_body':{'reasoning':{'enabled':False},'provider':judge.provider_route(0)}}
                effect=export.signed_axis_effect('-C',[export.score_cell(r)])
                assert abs(effect-(-1.1 if order=='AB' else 1.1))<1e-12
        assert len(calls)==18
        # Invalid content cannot trigger a second network call.
        response.choices[0].message.content='bad json'
        count=len(calls)
        try:await run.judge_cell(client,rows[0],'AB',trace)
        except run.NoRetry:pass
        else:raise AssertionError('retry guard missing')
        assert len(calls)==count+1
asyncio.run(check_requests())
assert protected=={p:run.gap.sha(p) for p in protected}
run.save(run.ROOT/'preflight.json',{'implementation_sha256':run.gap.sha(run.__file__),
    'transfer_sha256':run.gap.sha(run.transfer.__file__),'protected_hashes':protected,'geometry':geometry,
    'tokenizer_parity':True,'real_tiny_hybrid':True,'judgments_expected':18,'request_parity':True,'no_retry_guard':True})
print('DONOR_PREFLIGHT_PASS savedsource_3inputs_actualhook_15fixturearms_18requests_no_retry_protected8',flush=True)
