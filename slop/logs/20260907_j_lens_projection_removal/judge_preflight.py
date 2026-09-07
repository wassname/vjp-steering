"""Exercise cardinality and exact judge requests locally; no API client transport."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
sys.path[:0]=['scripts/scratch','scripts','src']
import j_lens_additive_concepts as runner
import judge

root=runner.PROJECTION_ROOT
data=json.loads((root/'generation.json').read_text())
captured=[]
raw=json.dumps({'evidence':'Offline transport fixture, not a measured score.','on_axis_A':1.2,'on_axis_B':2.3,'off_axis_A':.2,'off_axis_B':.4})
async def create(**kwargs):
    captured.append(kwargs)
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=raw,reasoning=None))],usage=SimpleNamespace(cost=0),provider='OFFLINE_FIXTURE')
async def close(): pass
client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)),close=close)
with tempfile.TemporaryDirectory() as tmp, patch('openai.AsyncOpenAI',return_value=client),patch.dict('os.environ',{'OPENROUTER_API_KEY':'offline-fixture'}):
    output=Path(tmp)/'judgments.jsonl'
    asyncio.run(runner.norm.judge_run(SimpleNamespace(judge=root/'generation.json',output=output)))
    records=[json.loads(l) for l in output.read_text().splitlines()]
    assert len(records)==len(captured)==30
    for j in records:
        r=next(r for r in data['records'] if r['scenario']==j['vignette'])
        b=next(b for b in data['reused_records'] if b['scenario']==r['scenario'] and b['condition']=='bare')
        row={'bare':b['text'],'steered':r['text'],'prompt':r['prompt'],'vignette':r['scenario'],'side':'-C','method':r['method'],'run':'norm-matched-gp16-dev15','source':str(root/'generation.json')}
        expected=judge.judge_prompt(row,j['order'])
        atext,btext=(b['text'],r['text']) if j['order']=='AB' else (r['text'],b['text'])
        assert expected.endswith('Response A:\n'+atext+'\n\nResponse B:\n'+btext)
        assert j['prompt']==expected and j['cache_key']==judge.cache_key(row,j['order'],0)
        assert any(c['messages']==[{'role':'user','content':expected}] for c in captured)
    for mutation in ('missing','plus','identity'):
        invalid=json.loads(json.dumps(data))
        if mutation=='missing':invalid['records'].pop()
        elif mutation=='plus':invalid['records'][0]['side']='+C'
        else:invalid['identity_controls']=[]
        path=Path(tmp)/f'{mutation}.json';path.write_text(json.dumps(invalid))
        try:
            asyncio.run(runner.norm.judge_run(SimpleNamespace(judge=path,output=Path(tmp)/f'{mutation}-output.jsonl')))
            raise RuntimeError('invalid projection cardinality accepted')
        except AssertionError:pass
    assert len(captured)==30
print('JUDGE_PREFLIGHT_PASS 15unique-minus+1identity;30actualjudge_one requests exact;invalid coverage fails beforeAPI;fixture scores discarded')
