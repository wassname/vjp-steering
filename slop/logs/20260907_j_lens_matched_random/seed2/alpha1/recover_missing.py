"""One explicitly authorized missing judgment; no replacement of saved cells."""
import asyncio,json,os,sys
from pathlib import Path
sys.path[:0]=['scripts','src']
import judge,export
from openai import AsyncOpenAI
root=Path('slop/logs/20260907_j_lens_matched_random/seed2/alpha1')
path=root/'judgments.jsonl';before=path.read_bytes();saved=[json.loads(l) for l in before.splitlines()]
assert len(saved)==59
keys={j['cache_key'] for j in saved};data=json.loads((root/'generation.json').read_text());missing=[]
for r in data['records']:
 b=next(b for b in data['reused_records'] if b['scenario']==r['scenario'] and b['condition']=='bare')
 row=dict(bare=b['text'],steered=r['text'],prompt=r['prompt'],vignette=r['scenario'],side=r['side'],run='norm-matched-gp16-dev15',method=r['method'],source=str(root/'generation.json'))
 for order in ('AB','BA'):
  if judge.cache_key(row,order,0) not in keys:missing.append((row,order,r['condition']))
assert len(missing)==1
row,order,condition=missing[0]
print('MISSING_CELL_VERIFIED',json.dumps({'row':row,'order':order,'cache_key':judge.cache_key(row,order,0),'serialized_prompt':judge.judge_prompt(row,order)}),flush=True)
async def run():
 client=AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'],base_url='https://openrouter.ai/api/v1',timeout=60.,max_retries=0)
 try:result=await asyncio.wait_for(judge.judge_one(client,row,order,0),240)
 finally:await client.close()
 result['condition']=condition;result['exported_effect']=export.signed_axis_effect(row['side'],[export.score_cell(result)])
 print('RECOVERED_RAW',json.dumps(result),flush=True)
 assert path.read_bytes()==before and result['cache_key'] not in keys
 with path.open('a') as f:f.write(json.dumps(result,ensure_ascii=False)+'\n')
 assert path.read_bytes().startswith(before)
 print('MISSING_CELL_RECOVERY_PASS unchanged59, appended1, previous timeout providercharge UNKNOWN',flush=True)
asyncio.run(run())
