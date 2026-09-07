"""First-draw Gaussian layer17 controls at all retained additive doses; PI/OpenAI Codex."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

# Modal hydrates this entrypoint under /root; dependencies are mounted in /repo.
SCRIPT_ROOT = Path('/repo/scripts') if Path('/repo/scripts').is_dir() else Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SCRIPT_ROOT), str(SCRIPT_ROOT/'scratch')]
import torch
import j_lens_additive_concepts as additive

norm, gap = additive.norm, additive.gap
ROOT=Path('slop/logs/20260907_j_lens_matched_random')
SAMPLER=ROOT/'sampler.json'


def freeze():
    source,contrast=additive.source_contrast()
    sampler={'seeds':list(range(10)), 'layers':[17], 'stream':'FIRST CPU Gaussian draw per seed; not historical band vectors',
        'formula':'g=torch.randn(d_model,generator=torch.Generator().manual_seed(seed)); unit=g/(g.norm()+1e-8)',
        'source_sha256':gap.sha(additive.SOURCE),'requested_base_norm':float(contrast.norm()),
        'sampling_source_sha256':gap.sha('../jsteer/jsteer/jacobian.py'), 'vectors':{}}
    states=[torch.tensor(h,dtype=torch.bfloat16) for h in source['construction']['source_states']]
    checks=[]
    for seed in range(10):
        g=torch.randn(contrast.numel(),generator=torch.Generator().manual_seed(seed))
        unit=g/(g.norm()+1e-8)
        sampler['vectors'][str(seed)]=unit.tolist()
        v=unit*contrast.norm()
        for alpha in (1,2,4):
            for sign in (-1,1):
                ms=[]
                for h in states:
                    after,m=additive.additive_patch(h[None],v,sign*alpha)
                    independent=(h.double()+(sign*alpha*v).to(h).double()).to(h)
                    assert torch.equal(after[0],independent)
                    assert m['actual_norm']>0 and m['direction_cosine']>.99
                    assert torch.equal(additive.additive_patch(h[None],v,0)[0],h[None])
                    ms.append(m)
                checks.append(dict(seed=seed,alpha=alpha,sign=sign,count=len(ms),nonzero=len(ms),
                    requested_norm=alpha*float(contrast.norm()),actual_min=min(m['actual_norm'] for m in ms),
                    actual_median=statistics.median(m['actual_norm'] for m in ms),actual_max=max(m['actual_norm'] for m in ms)))
    ROOT.mkdir(parents=True,exist_ok=True)
    norm.save(SAMPLER,sampler)
    # Existing real hybrid cached-hook CPU test also covers alpha0, delivery and cleanup.
    for alpha in (1,2,4):
        path=additive.dose_root(alpha)/'offline-bf16.json'
        check=json.loads(path.read_text())
        assert check['cached_identity_next_block_cleanup'] and check['zero_updates']==0
    norm.save(ROOT/'cpu.json',{'scope':'102 saved source states, NOT actual DEV delivery', 'sampler_sha256':gap.sha(SAMPLER),'checks':checks})
    print('RANDOM_CPU_PASS',json.dumps({'sampler_sha256':gap.sha(SAMPLER),'cases':sum(r['count'] for r in checks),
        'zero_updates':0,'requested_norms':[a*float(contrast.norm()) for a in (1,2,4)],
        'actual_min':min(r['actual_min'] for r in checks),'actual_max':max(r['actual_max'] for r in checks)}),flush=True)


def run(seed, output, revision):
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer,AutoModelForCausalLM
    assert seed in range(10) and not output.exists()
    sampler=json.loads(SAMPLER.read_text()); check=json.loads((ROOT/'cpu.json').read_text())
    assert check['sampler_sha256']==gap.sha(SAMPLER) and sampler['source_sha256']==gap.sha(additive.SOURCE)
    source,_=additive.source_contrast();reference=json.loads(norm.REFERENCE.read_text())
    assert gap.sha(norm.REFERENCE)==norm.REFERENCE_SHA
    v=torch.tensor(sampler['vectors'][str(seed)])*sampler['requested_base_norm']
    g=torch.randn(v.numel(),generator=torch.Generator().manual_seed(seed))
    torch.testing.assert_close(v,(g/(g.norm()+1e-8))*sampler['requested_base_norm'],rtol=0,atol=0)
    started=time.monotonic()
    snapshot=Path(snapshot_download(gap.MODEL,revision=gap.REVISION))
    assert snapshot.name==gap.REVISION and gap.sha(snapshot/'config.json')==source['model_config_sha256']
    assert gap.sha(snapshot/'model.safetensors.index.json')==source['model_index_sha256']
    tokenizer=AutoTokenizer.from_pretrained(snapshot);tokenizer.pad_token=tokenizer.eos_token
    assert gap.concept.tokenizer_content_hash(tokenizer)==source['construction']['source_tokenizer_sha256']
    model=AutoModelForCausalLM.from_pretrained(snapshot,dtype=torch.bfloat16).to('cuda').eval()
    data=dict(schema='matched_random_additive_v1',seed=seed,source_revision=revision,implementation_sha256=gap.sha(__file__),
        additive_sha256=gap.sha(additive.__file__),sampler_sha256=gap.sha(SAMPLER),model_revision=gap.REVISION,
        reference_sha256=norm.REFERENCE_SHA,settings=reference['settings'],contrast=v.tolist(),contrast_norm=float(v.norm()),
        reused_records=reference['records'],records=[],identity_controls=[])
    norm.save(output,data)
    print('SHOULD:90 treatments+2 identities per seed; requested norms alpha*.7216137051582336; no source inference; all doses retained.',flush=True)
    rows,_=gap.walk.read_cohort(15)
    for ri,row in enumerate(rows):
        bare=next(r for r in reference['records'] if r['scenario']==row['scenario'] and r['condition']=='bare')
        rendered=gap.walk.generation_inputs(tokenizer,[row])[0]
        encoded=tokenizer(rendered,return_tensors='pt',add_special_tokens=False).to(model.device)
        assert rendered==bare['rendered'] and encoded.input_ids[0].tolist()==bare['input_ids'] and encoded.attention_mask.all()
        for side,sign in (('+C',1),('-C',-1)):
            for alpha in ((0,1,2,4) if ri==0 else (1,2,4)):
                ms=[]
                with torch.inference_mode(),additive.intervention(model,v,sign*alpha,ms):
                    out=model.generate(**encoded,do_sample=False,temperature=None,top_p=None,top_k=None,
                        pad_token_id=tokenizer.eos_token_id,max_new_tokens=512,use_cache=True)
                ids=out[0,encoded.input_ids.shape[1]:].tolist()
                text=tokenizer.decode(ids,skip_special_tokens=True).strip()
                assert len(ms)==len(ids) and all(m['next_block_exact'] and m['nonfinal_exact'] for m in ms)
                assert [m['sequence_length'] for m in ms]==[len(bare['input_ids'])]+[1]*(len(ids)-1)
                r=dict(scenario=row['scenario'],prompt=row['prompt'],condition=f'random_s{seed}_a{alpha}_{side}',method='matched_random_additive',
                    side=side,alpha=alpha,rendered=rendered,input_ids=bare['input_ids'],attention_mask=encoded.attention_mask[0].tolist(),
                    generated_ids=ids,text=text,measurements=ms,health=gap.walk.health(tokenizer,[text]))
                if alpha:
                    assert all(m['actual_norm']>0 and m['direction_cosine']>.99 for m in ms)
                    data['records'].append(r)
                else:
                    assert ids==bare['generated_ids'] and all(m['actual_norm']==0 for m in ms)
                    r['identity_exact']=True;data['identity_controls'].append(r)
                norm.save(output,data)
                print('RANDOM_RESPONSE',json.dumps({k:r[k] for k in ('scenario','side','alpha','text','health')}),flush=True)
    assert len(data['records'])==90 and len(data['identity_controls'])==2
    data['runtime']=dict(seconds=time.monotonic()-started,gpu=torch.cuda.get_device_name(),peak_memory_bytes=torch.cuda.max_memory_allocated())
    norm.save(output,data);print('RANDOM_COMPLETE',json.dumps(data['runtime']),flush=True)


def split(path):
    data=json.loads(path.read_text());assert len(data['records'])==90 and len(data['identity_controls'])==2
    for alpha in (1,2,4):
        rows=[r for r in data['records'] if r['alpha']==alpha]
        assert len(rows)==30
        destination=path.parent/f'alpha{alpha}'/'generation.json'
        assert not destination.exists()
        norm.save(destination,{**data,'fixed_alpha':alpha,'records':rows,'parent_sha256':gap.sha(path)})
    print('RANDOM_SPLIT_PASS',path,flush=True)


if __name__!='__main__':
    import modal
    from run_modal import image,cache,source_revision
    image=image.add_local_file(str(norm.REFERENCE),'/repo/'+str(norm.REFERENCE)).add_local_file(str(additive.SOURCE),'/repo/'+str(additive.SOURCE))
    for file in (SAMPLER,ROOT/'cpu.json'):
        if file.exists():image=image.add_local_file(str(file),'/repo/'+str(file))
    app=modal.App('jsteer-matched-random-additive',image=image)
    @app.function(gpu='H100',volumes={'/cache':cache},timeout=360,max_containers=1,retries=0)
    def remote(seed:int,revision:str):
        destination=f'outputs/audits/{ROOT.name}/seed{seed}/generation.json'
        try:subprocess.run([sys.executable,'scripts/scratch/j_lens_matched_random.py','--seed',str(seed),'--output','/cache/'+destination,'--source-revision',revision],cwd='/repo',check=True)
        finally:
            print('RANDOM_VOLUME_COMMIT_START',flush=True);cache.commit();print('RANDOM_VOLUME_COMMIT_END',flush=True)
        return destination
    @app.function(timeout=60, max_containers=1, retries=0)
    def import_check():
        assert str(Path(__file__)).startswith('/root/')
        assert str(Path(additive.__file__)).startswith('/repo/scripts/scratch/')
        assert str(Path(norm.__file__)).startswith('/repo/scripts/scratch/')
        assert str(Path(gap.__file__)).startswith('/repo/scripts/scratch/')
        return dict(entrypoint=__file__, additive=additive.__file__, norm=norm.__file__, gap=gap.__file__, cuda=torch.cuda.is_available())
    @app.local_entrypoint()
    def check_imports():
        print('MOUNTED_IMPORT_PASS',json.dumps(import_check.remote()),flush=True)
    @app.local_entrypoint()
    def launch(seed:int):
        print('RANDOM_REMOTE_PATH',remote.remote(seed,source_revision()),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--split',type=Path)
    p.add_argument('--seed',type=int);p.add_argument('--output',type=Path);p.add_argument('--source-revision',default='unknown');args=p.parse_args()
    if args.freeze:freeze()
    elif args.split:split(args.split)
    else:run(args.seed,args.output,args.source_revision)
