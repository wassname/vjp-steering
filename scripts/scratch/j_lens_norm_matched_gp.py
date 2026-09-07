"""Pointwise norm-matched GP16 DEV diagnostic. PI/OpenAI Codex; not a frontier."""
import argparse
import asyncio
from contextlib import contextmanager
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SCRIPTS = Path('/repo/scripts') if Path('/repo/scripts').is_dir() else Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SCRIPTS), str(SCRIPTS/'scratch')]
import torch
import j_lens_dev15_representation as bridge
import j_lens_transfer_probe as probe
import j_lens_gap_clamp as gap

ROOT = Path('slop/logs/20260907_j_lens_norm_matched_gp')
REFERENCE = Path('slop/logs/20260907_j_lens_dev15_representation/generation.json')
REFERENCE_SHA = 'b5ebc369ad048844e64456e1949206af0450383f40c33f891f27b9a47727c985'
REMOTE = 'outputs/audits/20260907_j_lens_norm_matched_gp/generation.json'
LAYER = 17


def norm_matched_patch(h, gp_basis, gp_dual, full_basis, full_dual, gp_target, full_target, coefficient=1.):
    """Scale the nominal GP delta direction by the realized BF16 full delta norm, at this h."""
    c = h.float() @ gp_dual.T
    gp_delta = .5*(gp_target-(c[:, 0]-c[:, 1]))[:, None]*(gp_basis[0]-gp_basis[1])
    full_after = probe.replacement(h, None, full_basis, full_dual, 'gap_minus', full_target)
    full_delta = full_after.float()-h.float()
    reference_norm, gp_norm = full_delta.norm(), gp_delta.norm()
    if coefficient and reference_norm > 0 and gp_norm == 0:
        raise ValueError('ZERO_GP_DIRECTION_NONZERO_REFERENCE: stop arm; no invented direction')
    desired = torch.zeros_like(gp_delta) if not coefficient or reference_norm == 0 else coefficient*reference_norm*gp_delta/gp_norm
    after = h+desired.to(h)
    actual = after.float()-h.float()
    bound = torch.finfo(h.dtype).eps*(h.float().norm()+2*desired.norm())+1e-6
    assert torch.isfinite(after).all() and (actual-desired).norm() <= bound
    cosine = float(torch.nn.functional.cosine_similarity(actual, gp_delta).item()) if actual.norm() and gp_norm else None
    assert cosine is None or cosine > 0
    return after, {'gp_coordinates_before': c[0].tolist(), 'full_coordinates_before': (h.float()@full_dual.T)[0].tolist(),
        'gp_target': gp_target, 'full_target': full_target, 'gp_nominal_norm': float(gp_norm),
        'reference_realized_norm': float(reference_norm), 'desired_norm': float(desired.norm()),
        'actual_norm': float(actual.norm()), 'norm_error': float(abs(actual.norm()-desired.norm())),
        'rounding_error_norm': float((actual-desired).norm()), 'rounding_bound': float(bound),
        'direction_cosine': cosine, 'zero_reference': bool(reference_norm == 0)}


@contextmanager
def intervention(model, gp_vector, full_vector, gp_target, full_target, coefficient, measurements, layer=LAYER):
    b, d = (gp_vector.shared[layer][k].to(model.device) for k in ('basis','dual'))
    fb, fd = (full_vector.shared[layer][k].to(model.device) for k in ('basis','dual'))
    inserted = None
    def patch(_m, _i, output):
        nonlocal inserted
        before = output[0] if isinstance(output, tuple) else output
        h = before.clone()
        h[:, -1], metrics = norm_matched_patch(before[:, -1], b, d, fb, fd, gp_target, full_target, coefficient)
        assert torch.equal(h[:, :-1], before[:, :-1])
        if not coefficient: assert torch.equal(h, before)
        measurements.append({'call': len(measurements), 'sequence_length': h.shape[1], 'position': h.shape[1]-1,
            'nonfinal_exact': True, 'next_block_exact': False, **metrics})
        inserted = h[:, -1].clone()
        return (h, *output[1:]) if isinstance(output, tuple) else h
    def check(_m, inputs, kwargs):
        h = kwargs.get('hidden_states', inputs[0] if inputs else None)
        assert torch.equal(h[:, -1], inserted)
        measurements[-1]['next_block_exact'] = True
    handle = model.model.layers[layer].register_forward_hook(patch)
    following = model.model.layers[layer+1].register_forward_pre_hook(check, with_kwargs=True)
    try: yield
    finally:
        handle.remove()
        following.remove()


def self_test():
    from types import SimpleNamespace
    from transformers import Qwen3_5TextConfig, Qwen3_5ForCausalLM
    vectors, _, targets, provenance = bridge.sources(Path('outputs/experiments'))
    assert not any(provenance['overlaps_exact_or_normalized_substring'].values())
    assert gap.sha(REFERENCE) == REFERENCE_SHA
    torch.manual_seed(17)
    cases = 0
    for side in ('+C','-C'):
        b,d = (vectors['j_gp16'][side].shared[17][k] for k in ('basis','dual'))
        fb,fd = (vectors['full_residual'][side].shared[17][k] for k in ('basis','dual'))
        for dtype in (torch.float32, torch.bfloat16):
            h = torch.randn(1,b.shape[1]).to(dtype)
            gt,ft = targets['j_gp16'][side],targets['full_residual'][side]
            after,m = norm_matched_patch(h,b,d,fb,fd,gt,ft)
            gc = h.double()@torch.linalg.solve(b.double()@b.double().T,b.double()).T
            fc = h.double()@torch.linalg.solve(fb.double()@fb.double().T,fb.double()).T
            gd = .5*(gt-gc[:,0]+gc[:,1])[:,None]*(b[0].double()-b[1].double())
            full = .5*(ft-fc[:,0]+fc[:,1])[:,None]*(fb[0].double()-fb[1].double())
            # The reference requires two BF16 roundings, matching the existing full-residual hook.
            reference = (h+full.to(h)).float()-h.float()
            independent = h+(reference.norm()*gd/gd.norm()).to(h)
            torch.testing.assert_close(after,independent,atol=2e-5 if dtype==torch.float32 else .02,rtol=1e-5)
            assert torch.equal(norm_matched_patch(h,b,d,fb,fd,gt,ft,0.)[0],h)
            cases += 1
    b=torch.eye(32)[:2];fb=torch.eye(32)[2:4];d=b;fd=fb;h=torch.zeros(1,32)
    assert torch.equal(norm_matched_patch(h,b,d,fb,fd,1.,0.)[0],h)
    try: norm_matched_patch(h,b,d,fb,fd,0.,1.)
    except ValueError as e: assert 'ZERO_GP_DIRECTION' in str(e)
    else: raise AssertionError('zero direction not rejected')
    config=Qwen3_5TextConfig(vocab_size=64,hidden_size=32,intermediate_size=64,num_hidden_layers=3,
        num_attention_heads=2,num_key_value_heads=1,head_dim=16,layer_types=['linear_attention','full_attention','linear_attention'],
        linear_num_key_heads=2,linear_num_value_heads=2,linear_key_head_dim=8,linear_value_head_dim=8,pad_token_id=0,eos_token_id=63)
    model=Qwen3_5ForCausalLM(config).eval()
    gp=SimpleNamespace(shared={1:{'basis':b,'dual':d}});full=SimpleNamespace(shared={1:{'basis':fb,'dual':fd}})
    inputs={'input_ids':torch.tensor([[1,2,3,4]]),'attention_mask':torch.ones(1,4,dtype=torch.long)}
    def generate(): return model.generate(**inputs,max_new_tokens=4,do_sample=False,use_cache=True)
    with torch.inference_mode():
        bare=generate()
        for sign in (-1.,1.):
            for alpha in (0.,1.):
                measurements=[]
                with intervention(model,gp,full,sign*3,sign*4,alpha,measurements,layer=1): out=generate()
                assert len(measurements)==out.shape[1]-4
                assert [m['sequence_length'] for m in measurements]==[4]+[1]*(len(measurements)-1)
                assert all(m['next_block_exact'] and m['nonfinal_exact'] for m in measurements)
                if not alpha: assert torch.equal(out,bare) and all(m['actual_norm']==0 for m in measurements)
        assert torch.equal(generate(),bare)
    print('NORM_MATCH_CPU_PASS',json.dumps({'fp64_cases':cases,'both_signs':True,'zero_exception':True,'zero_reference':True,'alpha0_exact':True,'cached_calls':True,'next_block_exact':True,'cleanup_exact':True}),flush=True)


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data)+'\n')
    temporary.replace(path)


def run(args):
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer,AutoModelForCausalLM
    assert not args.output.exists()
    started=time.monotonic()
    assert gap.sha(REFERENCE)==REFERENCE_SHA
    reference=json.loads(REFERENCE.read_text())
    vectors,metadata,targets,provenance=bridge.sources(args.source_root)
    assert targets==reference['targets'] and provenance==reference['provenance']
    snapshot=Path(snapshot_download(gap.MODEL,revision=gap.REVISION));assert snapshot.name==gap.REVISION
    assert gap.sha(snapshot/'config.json')==reference['model_config_sha256']
    assert gap.sha(snapshot/'model.safetensors.index.json')==reference['model_index_sha256']
    tokenizer=AutoTokenizer.from_pretrained(snapshot);tokenizer.pad_token=tokenizer.eos_token
    assert gap.concept.tokenizer_content_hash(tokenizer)==reference['metrology']['generation_tokenizer']['sha256']
    model=AutoModelForCausalLM.from_pretrained(snapshot,dtype=torch.bfloat16).to('cuda').eval()
    data={'schema':'norm_matched_gp16_v1','source_revision':args.source_revision,'implementation_sha256':gap.sha(__file__),
        'dependencies_sha256':{p:gap.sha(SCRIPTS/'scratch'/p) for p in ('j_lens_dev15_representation.py','j_lens_transfer_probe.py','j_lens_gap_clamp.py')},
        'reference_sha256':REFERENCE_SHA,'model_revision':gap.REVISION,'snapshot':str(snapshot),'provenance':provenance,
        'targets':targets,'settings':reference['settings'],'records':[],'identity_controls':[],
        'operator':'nominal GP delta direction scaled by realized BF16 full-residual counterfactual norm on same state; not target-gap achievement'}
    print('NORM_CONFIG',json.dumps({k:data[k] for k in ('source_revision','reference_sha256','model_revision','settings','operator')}),flush=True)
    print('SHOULD: 30 new treatment cells+2exactidentities; every cached forward norm/direction/nonfinal/nextblock measured; unchanged source/rubric; no old target-gap invariant.',flush=True)
    rows,_=gap.walk.read_cohort(15)
    for ri,row in enumerate(rows):
        bare=next(r for r in reference['records'] if r['scenario']==row['scenario'] and r['condition']=='bare')
        rendered=gap.walk.generation_inputs(tokenizer,[row])[0]
        encoded=tokenizer(rendered,return_tensors='pt',add_special_tokens=False).to(model.device)
        assert rendered==bare['rendered'] and encoded.input_ids[0].tolist()==bare['input_ids']
        for side in ('+C','-C'):
            for alpha in ((0.,1.) if ri==0 else (1.,)):
                measurements=[]
                try:
                    with torch.inference_mode(),intervention(model,vectors['j_gp16'][side],vectors['full_residual'][side],targets['j_gp16'][side],targets['full_residual'][side],alpha,measurements):
                        output=model.generate(**encoded,do_sample=False,temperature=None,top_p=None,top_k=None,pad_token_id=tokenizer.eos_token_id,max_new_tokens=512,use_cache=True)
                except Exception as e:
                    data['failure']={'scenario':row['scenario'],'side':side,'error':repr(e),'measurements':measurements}
                    save(args.output,data)
                    raise
                ids=output[0,encoded.input_ids.shape[1]:].tolist()
                assert len(measurements)==len(ids) and all(m['next_block_exact'] for m in measurements)
                assert [m['sequence_length'] for m in measurements]==[len(bare['input_ids'])]+[1]*(len(ids)-1)
                text=tokenizer.decode(ids,skip_special_tokens=True).strip()
                record={'scenario':row['scenario'],'prompt':row['prompt'],'condition':'norm_matched_gp_'+('plus' if side=='+C' else 'minus'),
                    'method':'norm_matched_gp','side':side,'rendered':rendered,'input_ids':bare['input_ids'],'attention_mask':encoded.attention_mask[0].tolist(),
                    'generated_ids':ids,'text':text,'measurements':measurements,'health':gap.walk.health(tokenizer,[text])}
                if not alpha:
                    assert ids==bare['generated_ids'] and all(m['actual_norm']==0 for m in measurements)
                    record['identity_exact']=True;data['identity_controls'].append(record)
                else:data['records'].append(record)
                save(args.output,data)
                print('NORM_RESPONSE',json.dumps({k:v for k,v in record.items() if k not in ('input_ids','attention_mask','generated_ids','measurements')}),flush=True)
    data['reused_records']=reference['records']
    data['runtime']={'seconds':time.monotonic()-started,'gpu':torch.cuda.get_device_name(),'peak_memory_bytes':torch.cuda.max_memory_allocated(),'torch':torch.__version__}
    assert len(data['records'])==30 and len(data['identity_controls'])==2
    save(args.output,data)
    print('NORM_COMPLETE',json.dumps(data['runtime']),flush=True)


async def judge_run(args):
    import judge
    import export
    from openai import AsyncOpenAI
    assert not args.output.exists()
    data=json.loads(args.judge.read_text());assert len(data['records'])==30 and 'runtime' in data
    client=AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'],base_url='https://openrouter.ai/api/v1',timeout=60.,max_retries=0)
    semaphore=asyncio.Semaphore(3)
    async def one(r,order):
        bare=next(b for b in data['reused_records'] if b['scenario']==r['scenario'] and b['condition']=='bare')
        row={'bare':bare['text'],'steered':r['text'],'prompt':r['prompt'],'vignette':r['scenario'],'side':r['side'],
            'run':'norm-matched-gp16-dev15','method':r['method'],'source':str(args.judge)}
        async with semaphore: result=await asyncio.wait_for(judge.judge_one(client,row,order,0),240)
        result['condition']=r['condition'];result['exported_effect']=export.signed_axis_effect(r['side'],[export.score_cell(result)])
        assert abs(result['exported_effect']-gap.mapped_effect(result['judgment'],order,r['side']))<1e-9
        with args.output.open('a') as f:f.write(json.dumps(result,ensure_ascii=False)+'\n')
        print('NORM_JUDGMENT',json.dumps(result,ensure_ascii=False),flush=True)
    try:await asyncio.gather(*(one(r,o) for r in data['records'] for o in ('AB','BA')))
    finally:await client.close()


if __name__!='__main__':
    import modal
    from run_modal import image,cache,source_revision
    app=modal.App('jsteer-norm-matched-gp',image=image.add_local_file(str(REFERENCE),'/repo/'+str(REFERENCE)))
    @app.function(gpu='H100',volumes={'/cache':cache},timeout=360,max_containers=1,retries=0)
    def remote(revision:str):
        try:
            subprocess.run([sys.executable,'scripts/scratch/j_lens_norm_matched_gp.py','--source-root','/cache/outputs/experiments','--output','/cache/'+REMOTE,'--source-revision',revision],cwd='/repo',check=True)
        finally:
            print('NORM_VOLUME_COMMIT_START',flush=True);cache.commit();print('NORM_VOLUME_COMMIT_END',flush=True)
        return REMOTE
    @app.local_entrypoint()
    def launch():
        print('NORM_REMOTE_PATH',remote.remote(source_revision()),flush=True)
        print('Download separately with modal volume get; no large remote return.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true');parser.add_argument('--judge',type=Path)
    parser.add_argument('--source-root',type=Path,default=Path('outputs/experiments'));parser.add_argument('--output',type=Path,default=ROOT/'generation.json')
    parser.add_argument('--source-revision',default='unknown');args=parser.parse_args()
    if args.self_test:self_test()
    elif args.judge:asyncio.run(judge_run(args))
    else:run(args)
