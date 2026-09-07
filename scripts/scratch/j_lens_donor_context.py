"""Fixed donor-context factorial, not a DEV steering point. PI/OpenAI Codex."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

SCRIPT_ROOT = Path('/repo/scripts') if Path('/repo/scripts').is_dir() else Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SCRIPT_ROOT), str(SCRIPT_ROOT/'scratch')]
import torch
import j_lens_transfer_probe as transfer

gap = transfer.gap
ROOT = Path('slop/logs/20260907_j_lens_donor_context')
REFERENCE = transfer.ROOT/'generation.json'
PROJECTION = Path('slop/logs/20260907_j_lens_projection_removal/generation.json')
HASHES = {str(REFERENCE): 'b69925310ad2b2744e107442b1d283569d106365fda73c5a1ec98f857bf169e9',
          str(PROJECTION): '03aaaae93f1aaad0436c0f92e12469a04b8a7ad27e58acf2f6d3bd890ffca431'}
ARMS = ('unpatched', 'neither', 'parallel', 'complement', 'both')

def load(path):
    return json.loads(Path(path).read_text())

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2)+'\n')

def sources():
    assert all(gap.sha(p)==h for p,h in HASHES.items())
    ref, projection = load(REFERENCE), load(PROJECTION)
    assert ref['model_revision']==projection['model_revision']==gap.REVISION
    u = torch.tensor(projection['contrast'], dtype=torch.float64)
    u = (u/u.norm()).float()
    assert set(r['scenario'] for r in ref['records'])==set(gap.SCENARIOS)
    return ref, u

def states(hb, hd, u):
    """FP32 partial-arm arithmetic, one final BF16 cast; exact endpoint copies."""
    p = u * (u @ (hd.float()-hb.float()))
    return {'unpatched': None, 'neither': hb.clone(), 'parallel': (hb.float()+p).to(hb),
            'complement': (hd.float()-p).to(hd), 'both': hd.clone()}

def generate(model, encoded, u, replacement, max_tokens=512, layer=17):
    """All arms use the earlier real one-shot hook and independent next-block check."""
    vector = SimpleNamespace(shared={layer: {'basis': u[None], 'dual': u[None]}})
    record = {}
    mode = 'direct_minus' if replacement is None else 'full_minus'
    donor = None if replacement is None else replacement[None]
    with torch.inference_mode(), transfer.observed_prefill(model, vector, mode, donor, 0., record, layer=layer):
        output = model.generate(**encoded, do_sample=False, temperature=None, top_p=None, top_k=None,
            pad_token_id=model.config.eos_token_id, max_new_tokens=max_tokens, use_cache=True,
            return_dict_in_generate=True, output_logits=True)
    ids = output.sequences[0, encoded.input_ids.shape[1]:].tolist()
    first = output.logits[0][0].float().cpu()
    record['generated_ids'] = ids
    return record, first

def run(args):
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    start = time.monotonic()
    assert not args.output.exists()
    reference, u = sources()
    preflight = load(ROOT/'preflight.json')
    assert preflight['implementation_sha256']==gap.sha(__file__)
    assert preflight['transfer_sha256']==gap.sha(transfer.__file__)
    snapshot = Path(snapshot_download(gap.MODEL, revision=gap.REVISION))
    assert snapshot.name==gap.REVISION
    assert gap.sha(snapshot/'config.json')==reference['model_config_sha256']
    assert gap.sha(snapshot/'model.safetensors.index.json')==reference['model_index_sha256']
    tokenizer = AutoTokenizer.from_pretrained(snapshot)
    tokenizer.pad_token = tokenizer.eos_token
    encoded_inputs = {}
    for scenario in gap.SCENARIOS:
        old = next(r for r in reference['records'] if r['scenario']==scenario and r['condition']=='direct_minus')
        encoded = tokenizer(old['rendered'], return_tensors='pt', add_special_tokens=False)
        assert encoded.input_ids[0].tolist()==old['input_ids']
        encoded_inputs[scenario] = encoded
    model = AutoModelForCausalLM.from_pretrained(snapshot, dtype=torch.bfloat16).to('cuda').eval()
    u = u.to(model.device)
    data = {'schema':'donor_context_factorial_v1', 'source_revision':args.source_revision,
        'implementation_sha256':gap.sha(__file__), 'transfer_sha256':gap.sha(transfer.__file__),
        'source_hashes':HASHES, 'model':gap.MODEL, 'model_revision':gap.REVISION,
        'settings':{'layer':17,'dtype':'bfloat16','batch':1,'max_new_tokens':512,'use_cache':True,'one_shot':True},
        'arms':ARMS, 'records':[], 'argv':sys.argv, 'unit_axis':u.cpu().tolist()}
    print('DONOR_CONFIG',json.dumps(data),flush=True)
    print('SHOULD: 15 responses; saved donor replay exact; all arms donor context; one-shot/nonfinal identity/next-block exact; both exact full IDs/logits/states. Neither must impair correction before component inference.',flush=True)
    for scenario in gap.SCENARIOS:
        old = {r['condition']:r for r in reference['records'] if r['scenario']==scenario}
        donor = old['direct_minus']
        hb = torch.tensor(old['bare']['patch']['after'],dtype=torch.bfloat16,device=model.device)
        hd = torch.tensor(donor['patch']['after'],dtype=torch.bfloat16,device=model.device)
        replacements = states(hb, hd, u)
        encoded = encoded_inputs[scenario].to(model.device)
        baseline, baseline_logits = None, None
        for arm in ARMS:
            record, logits = generate(model, encoded, u, replacements[arm])
            record.update(scenario=scenario, condition=arm, prompt=donor['prompt'], rendered=donor['rendered'],
                input_ids=donor['input_ids'], text=tokenizer.decode(record['generated_ids'],skip_special_tokens=True).strip())
            record['health'] = gap.walk.health(tokenizer,[record['text']])
            # Save even a failed control before raising; never relax replay to complete the run.
            data['records'].append(record)
            save(args.output,data)
            assert record['patch']['before']==donor['patch']['after'], 'saved donor residual mismatch'
            if arm=='unpatched':
                assert record['generated_ids']==donor['generated_ids'], 'saved donor output mismatch'
                assert record['final_states']==donor['final_states'], 'saved donor downstream mismatch'
                baseline, baseline_logits = record, logits
            if arm=='both':
                assert record['generated_ids']==baseline['generated_ids']
                assert torch.equal(logits,baseline_logits)
                assert record['final_states']==baseline['final_states']
                record['identity_exact']=True
            before = torch.tensor(record['patch']['before'],dtype=torch.float64)
            after = torch.tensor(record['patch']['after'],dtype=torch.float64)
            b,d,axis = hb.cpu().double(),hd.cpu().double(),u.cpu().double()
            axis /= axis.norm()
            p = axis*(axis@(d-b))
            ideal = {'unpatched':d,'both':d,'neither':b,'parallel':b+p,'complement':d-p}[arm]
            error = float((after-ideal).norm())
            bound = float(torch.finfo(torch.bfloat16).eps*ideal.norm()+8*torch.finfo(torch.float32).eps*(b.norm()+d.norm()))
            assert error<=bound
            record['delivery']={'actual_norm':float((after-before).norm()),'ideal_norm':float((ideal-d).norm()),
                'rounding_error':error,'rounding_bound':bound,'coordinate_before':float(axis@before),
                'coordinate_after':float(axis@after),'ideal_coordinate':float(axis@ideal)}
            logp, logq = logits.log_softmax(-1), baseline_logits.log_softmax(-1)
            record['first_token']={'top20_ids':logits.topk(20).indices.tolist(),
                'max_abs_logit_change':float((logits-baseline_logits).abs().max()),
                'kl_from_donor':float((logq.exp()*(logq-logp)).sum())}
            save(args.output,data)
            print('DONOR_RESPONSE',json.dumps({k:record[k] for k in ('scenario','condition','rendered','text','health','delivery','first_token')}),flush=True)
    data['runtime']={'seconds':time.monotonic()-start,'gpu':torch.cuda.get_device_name(),
                     'peak_memory_bytes':torch.cuda.max_memory_allocated(),'torch':torch.__version__}
    save(args.output,data)
    print('DONOR_COMPLETE',json.dumps(data['runtime']),flush=True)

def judge_rows(data):
    assert len(data['records'])==15
    assert {(r['scenario'],r['condition']) for r in data['records']}=={(s,a) for s in gap.SCENARIOS for a in ARMS}
    rows=[]
    for scenario in gap.SCENARIOS:
        records={r['condition']:r for r in data['records'] if r['scenario']==scenario}
        donor=records['unpatched']
        assert records['both'].get('identity_exact') and records['both']['generated_ids']==donor['generated_ids']
        for arm,r in records.items():
            assert r['input_ids']==donor['input_ids'] and r['rendered']==donor['rendered']
            if arm in ('neither','parallel','complement'):
                rows.append({'bare':donor['text'],'steered':r['text'],'prompt':r['prompt'],'vignette':scenario,
                    'side':'-C','run':'donor-context-factorial','method':'donor_context_'+arm,
                    'source':str(ROOT/'generation.json'),'condition':arm})
    assert len(rows)==9
    return rows

class NoRetry(BaseException):
    """Abort shared judge retries without allowing another paid request."""

async def judge_cell(client,row,order,trace):
    import judge
    used=False
    async def once(**kwargs):
        nonlocal used
        if used:
            raise NoRetry('Another request for the same cell is not authorized')
        used=True
        try:
            response=await client.chat.completions.create(**kwargs)
        except Exception as error:
            raise NoRetry(f'First request failed: {error}') from error
        with trace.open('a') as f:
            f.write(json.dumps({'scenario':row['vignette'],'condition':row['condition'],'order':order,
                               'request':kwargs,'response':response.model_dump()},ensure_ascii=False)+'\n')
        return response
    guarded=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=once)))
    result=await judge.judge_one(guarded,row,order,0)
    result['condition']=row['condition']
    return result

async def judge_run():
    import export
    from openai import AsyncOpenAI
    data=load(ROOT/'generation.json')
    assert 'runtime' in data
    rows=judge_rows(data)
    out=ROOT/'judgments.jsonl'
    trace=ROOT/'judge-transport.jsonl'
    assert not out.exists() and not trace.exists()
    client=AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'],base_url='https://openrouter.ai/api/v1',timeout=60.,max_retries=0)
    try:
        for row in rows:
            for order in ('AB','BA'):
                result=await judge_cell(client,row,order,trace)
                result['exported_effect']=export.signed_axis_effect('-C',[export.score_cell(result)])
                with out.open('a') as f:f.write(json.dumps(result,ensure_ascii=False)+'\n')
                print('DONOR_JUDGMENT',json.dumps(result,ensure_ascii=False),flush=True)
    finally:
        await client.close()

if __name__!='__main__':
    import modal
    from run_modal import image,cache,source_revision
    for path in (REFERENCE,PROJECTION,ROOT/'preflight.json'):
        if path.exists():image=image.add_local_file(str(path),'/repo/'+str(path))
    app=modal.App('jsteer-donor-context',image=image)
    @app.function(gpu='H100',volumes={'/cache':cache},timeout=360,max_containers=1,retries=0)
    def remote(revision:str):
        destination=Path('/cache/outputs/audits/20260907_j_lens_donor_context/generation.json')
        try:
            subprocess.run([sys.executable,'scripts/scratch/j_lens_donor_context.py','--output',str(destination),
                            '--source-revision',revision],cwd='/repo',check=True)
            return destination.read_text()
        finally:cache.commit()
    @app.local_entrypoint()
    def launch():
        assert not (ROOT/'generation.json').exists()
        assert load(ROOT/'preflight.json')['implementation_sha256']==gap.sha(__file__)
        data=remote.remote(source_revision())
        (ROOT/'generation.json').write_text(data)
        print('DONOR_DOWNLOADED',ROOT/'generation.json',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=ROOT/'generation.json')
    p.add_argument('--source-revision',default='unknown')
    p.add_argument('--judge',action='store_true')
    args=p.parse_args()
    if args.judge:asyncio.run(judge_run())
    else:run(args)
