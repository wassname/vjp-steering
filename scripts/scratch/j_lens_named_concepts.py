"""Named sycophancy/skepticism sources; fixed exploratory DEV, not a frontier. PI/OpenAI Codex."""
import argparse
import asyncio
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

SCRIPTS = Path('/repo/scripts') if Path('/repo/scripts').is_dir() else Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SCRIPTS), str(SCRIPTS/'scratch')]
import torch
import j_lens_norm_matched_gp as norm
import j_lens_dictionary_control as control
import j_lens_gap_clamp as gap

ROOT = Path('slop/logs/20260907_j_lens_named_concepts')
REMOTE = 'outputs/audits/20260907_j_lens_named_concepts/generation.json'
LAYER = 17
INVENTORY_SHA = 'c16e92d32b43e50027863d939445bb839301457f494363c00e2d00e5c6e73560'


def inventory():
    p = ROOT/'reference-verbal-introspection.json'
    assert gap.sha(p) == INVENTORY_SHA
    spec = json.loads((ROOT/'inventory.json').read_text())
    names = []
    for row in json.loads(p.read_text())['concepts']:
        assert row['name'] == row['surface']
        if row['name'] not in ('sycophancy', 'skepticism') and row['name'] not in names:
            names.append(row['name'])
    assert spec['baseline'] == names[:100] and len(set(spec['baseline'])) == 100
    assert (spec['positive'], spec['negative']) == ('sycophancy', 'skepticism')
    return spec


def full_geometry(states):
    assert states.shape[0] == 102 and torch.isfinite(states).all()
    mean = states[2:].mean(0)
    signals = states[:2]-mean
    b = signals/signals.norm(dim=1, keepdim=True)
    assert torch.linalg.matrix_rank(b) == 2
    d = torch.linalg.pinv(b).T
    independent = torch.linalg.solve(b.double()@b.double().T, b.double())
    torch.testing.assert_close(d.double(), independent, atol=1e-6, rtol=1e-5)
    return signals, mean, b, d


def self_test():
    spec = inventory()
    control.self_test()  # Reused pursuit, independent index/Gram and real hybrid cached adapter tests.
    states = torch.randn(102, 32, generator=torch.Generator().manual_seed(17))
    signals, mean, b, d = full_geometry(states)
    torch.testing.assert_close(mean.double(), sum(states[2:].double())/100, atol=1e-6, rtol=1e-5)
    torch.testing.assert_close(signals+mean, states[:2])
    dictionary = torch.randn(64,32, generator=torch.Generator().manual_seed(23))
    dictionary /= dictionary.norm(dim=1,keepdim=True)
    gb,gd,_ = control.construct(dictionary,dict(zip(('positive','negative'),signals)))
    for index in (0,1):
        # Calibration uses the actual source activation, not its baseline-subtracted signal.
        coord = states[index]@gd.T
        target = coord[0]-coord[1]
        independent = states[index].double()@torch.linalg.solve(gb.double()@gb.double().T,gb.double()).T
        torch.testing.assert_close(target.double(),independent[0]-independent[1],atol=1e-5,rtol=1e-5)
        assert torch.equal(norm.norm_matched_patch(states[0:1],gb,gd,b,d,float(target),3.,0.)[0],states[0:1])
    print('NAMED_CPU_PASS',json.dumps({'baseline_count':len(spec['baseline']),'inventory_sha256':INVENTORY_SHA,
        'baseline_subtraction':True,'source_target_gram':True,'adapter_reused':True}),flush=True)


@torch.inference_mode()
def extract(model, tokenizer):
    spec = inventory()
    names = [spec['positive'],spec['negative'],*spec['baseline']]
    prompts = [tokenizer.apply_chat_template([{'role':'user','content':f'Tell me about {name}'}],
        tokenize=False,add_generation_prompt=True,enable_thinking=False) for name in names]
    states,records = [],[]
    for name,prompt in zip(names,prompts,strict=True):
        encoded = tokenizer(prompt,return_tensors='pt',add_special_tokens=False).to(model.device)
        assert encoded.input_ids.shape[1] < 256 and encoded.attention_mask.all()
        with gap.concept._activations(model,[LAYER]) as found:
            model.model(**encoded,use_cache=False)
        states.append(found[LAYER][0,-1].float())
        records.append({'concept':name,'rendered':prompt,'input_ids':encoded.input_ids[0].tolist(),
            'attention_mask':encoded.attention_mask[0].tolist(),'final_position':encoded.input_ids.shape[1]-1})
    assert records == json.loads((ROOT/'source-prompts.json').read_text())
    states = torch.stack(states)
    signals,mean,fb,fd = full_geometry(states)
    lens, checkpoint = gap.concept._load_j_lens(model,[LAYER],None)
    reference = json.loads(norm.REFERENCE.read_text())
    assert gap.sha(lens) == reference['provenance']['lens_sha256']
    raw = model.lm_head.weight.detach().float()@checkpoint['J'][LAYER].float().to(model.device)
    assert (raw.norm(dim=1)>0).all()
    dictionary = raw/raw.norm(dim=1,keepdim=True)
    b,d,construction = control.construct(dictionary,dict(zip(('positive','negative'),signals)))
    construction.update({'source_records':records,'source_states':states.tolist(),'baseline_mean':mean.tolist(),
        'full_signals':signals.tolist(),'full_basis':fb.tolist(),'full_dual':fd.tolist(),'lens_sha256':gap.sha(lens),
        'dictionary':'unit_rows(lm_head @ J17), all vocabulary rows retained','dictionary_rows':len(dictionary),
        'inventory':spec,'source_tokenizer_sha256':gap.concept.tokenizer_content_hash(tokenizer),
        'calibration_label':'Two named source activations also used for construction; NOT held-out calibration',
        'direction_cosine_to_own_full':float(torch.nn.functional.cosine_similarity((b[0]-b[1])[None],(fb[0]-fb[1])[None]))})
    targets = {'j_gp16':{},'full_residual':{}}
    for name,dual in [('j_gp16',d),('full_residual',fd)]:
        coords = states[:2]@dual.T
        targets[name] = {side:float(coords[i,0]-coords[i,1]) for i,side in enumerate(('+C','-C'))}
        construction[name+'_source_coordinates'] = coords.tolist()
    for i,name in enumerate(('positive','negative')):
        r=construction['components'][name];ids=r['nonzero_ids']
        r['tokens']=[tokenizer.decode([j]) for j in ids]
        r['dictionary_rows']=dictionary[ids].tolist()
        independent = model.lm_head.weight[ids].double()@checkpoint['J'][LAYER].double().to(model.device)
        independent /= independent.norm(dim=1,keepdim=True)
        torch.testing.assert_close(dictionary[ids].double(),independent,atol=1e-5,rtol=1e-4)
    print('NAMED_SOURCE_PASS',json.dumps({'targets':targets,'rank':2,'baseline_count':100,'source_count':102,
        'supports':{k:r['selected_ids'] for k,r in construction['components'].items()},
        'direction_cosine_to_own_full':construction['direction_cosine_to_own_full'],'lens_sha256':gap.sha(lens)}),flush=True)
    return SimpleNamespace(shared={LAYER:{'basis':b,'dual':d}}),SimpleNamespace(shared={LAYER:{'basis':fb,'dual':fd}}),targets,construction


def run(args):
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer,AutoModelForCausalLM
    assert not args.output.exists() and gap.sha(norm.REFERENCE)==norm.REFERENCE_SHA
    started=time.monotonic();reference=json.loads(norm.REFERENCE.read_text())
    snapshot=Path(snapshot_download(gap.MODEL,revision=gap.REVISION));assert snapshot.name==gap.REVISION
    assert gap.sha(snapshot/'config.json')==reference['model_config_sha256']
    assert gap.sha(snapshot/'model.safetensors.index.json')==reference['model_index_sha256']
    tokenizer=AutoTokenizer.from_pretrained(snapshot)
    assert gap.concept.tokenizer_content_hash(tokenizer)=='0ef9d0923a6d6d8342cae2674ade04c07f12fd060a55f170b8cc9b89f9a822d4'
    model=AutoModelForCausalLM.from_pretrained(snapshot,dtype=torch.bfloat16).to('cuda').eval()
    print('NAMED_MODEL',json.dumps({'revision':gap.REVISION,'snapshot':str(snapshot),'new_sources_current_revision':True}),flush=True)
    vector,full,targets,construction=extract(model,tokenizer)
    source_seconds=time.monotonic()-started
    tokenizer.pad_token=tokenizer.eos_token
    assert gap.concept.tokenizer_content_hash(tokenizer)==reference['metrology']['generation_tokenizer']['sha256']
    data={'schema':'named_concepts_v1','source_revision':args.source_revision,'implementation_sha256':gap.sha(__file__),
        'dependencies_sha256':{p:gap.sha(SCRIPTS/'scratch'/p) for p in ('j_lens_dictionary_control.py','j_lens_norm_matched_gp.py','j_lens_gap_clamp.py')},
        'model_revision':gap.REVISION,'snapshot':str(snapshot),'reference_sha256':norm.REFERENCE_SHA,
        'model_config_sha256':gap.sha(snapshot/'config.json'),'model_index_sha256':gap.sha(snapshot/'model.safetensors.index.json'),
        'construction':construction,'targets':targets,'settings':reference['settings'],
        'records':[],'identity_controls':[],'reused_records':reference['records'],'stage_seconds':{'model_and_source':source_seconds},
        'scope':'Named concept source repair; own full-concept reference norm changes with source; exploratory reused DEV15, not confirmation'}
    norm.save(args.output,data)
    print('SHOULD:102 named source prompts,30 new DEV treatments+2 identities; source calibration NOT heldout; norm/direction/mask/next-block checks; unchanged rubric.',flush=True)
    rows,_=gap.walk.read_cohort(15);generation_started=time.monotonic()
    for ri,row in enumerate(rows):
        bare=next(r for r in reference['records'] if r['scenario']==row['scenario'] and r['condition']=='bare')
        rendered=gap.walk.generation_inputs(tokenizer,[row])[0]
        encoded=tokenizer(rendered,return_tensors='pt',add_special_tokens=False).to(model.device)
        assert rendered==bare['rendered'] and encoded.input_ids[0].tolist()==bare['input_ids']
        for side in ('+C','-C'):
            for alpha in ((0.,1.) if ri==0 else (1.,)):
                measurements=[]
                try:
                    with torch.inference_mode(),norm.intervention(model,vector,full,targets['j_gp16'][side],targets['full_residual'][side],alpha,measurements):
                        output=model.generate(**encoded,do_sample=False,temperature=None,top_p=None,top_k=None,pad_token_id=tokenizer.eos_token_id,max_new_tokens=512,use_cache=True)
                except Exception as e:
                    data['failure']={'scenario':row['scenario'],'side':side,'error':repr(e),'measurements':measurements};norm.save(args.output,data);raise
                ids=output[0,encoded.input_ids.shape[1]:].tolist()
                assert len(measurements)==len(ids) and all(m['next_block_exact'] for m in measurements)
                assert [m['sequence_length'] for m in measurements]==[len(bare['input_ids'])]+[1]*(len(ids)-1)
                text=tokenizer.decode(ids,skip_special_tokens=True).strip()
                r={'scenario':row['scenario'],'prompt':row['prompt'],'condition':'named_concepts_'+('plus' if side=='+C' else 'minus'),
                    'method':'named_concepts','side':side,'rendered':rendered,'input_ids':bare['input_ids'],'attention_mask':encoded.attention_mask[0].tolist(),
                    'generated_ids':ids,'text':text,'measurements':measurements,'health':gap.walk.health(tokenizer,[text])}
                if not alpha:
                    assert ids==bare['generated_ids'] and all(m['actual_norm']==0 for m in measurements)
                    r['identity_exact']=True;data['identity_controls'].append(r)
                else:data['records'].append(r)
                norm.save(args.output,data)
                print('NAMED_RESPONSE',json.dumps({k:v for k,v in r.items() if k not in ('input_ids','attention_mask','generated_ids','measurements')}),flush=True)
    data['stage_seconds']['generation']=time.monotonic()-generation_started
    data['runtime']={'seconds':time.monotonic()-started,'gpu':torch.cuda.get_device_name(),'peak_memory_bytes':torch.cuda.max_memory_allocated(),'torch':torch.__version__}
    assert len(data['records'])==30 and len(data['identity_controls'])==2
    norm.save(args.output,data);print('NAMED_COMPLETE',json.dumps({'runtime':data['runtime'],'stages':data['stage_seconds']}),flush=True)


def report(folder):
    import export
    data=json.loads((folder/'generation.json').read_text());js=[json.loads(l) for l in (folder/'judgments.jsonl').read_text().splitlines()]
    assert gap.sha(norm.REFERENCE)==data['reference_sha256'] and data['reused_records']==json.loads(norm.REFERENCE.read_text())['records']
    executed=subprocess.check_output(['git','show',data['source_revision']+':scripts/scratch/j_lens_named_concepts.py'])
    assert hashlib.sha256(executed).hexdigest()==data['implementation_sha256']
    assert len(js)==60 and len(data['records'])==30 and len({(r['scenario'],r['side']) for r in data['records']})==30
    assert len(data['identity_controls'])==2 and all(r['identity_exact'] for r in data['identity_controls'])
    scores=[];pairs=[];steps=[];lines=['# Named concept source DEV: complete responses and unchanged scores']
    for r in [x for x in data['reused_records'] if x['condition']=='bare']+data['records']:
        lines+=['## '+r['scenario']+' / '+r['condition'],'```text',r['rendered'],'```','> '+r['text'],'Health: '+json.dumps(r['health'])]
        found={j['order']:j for j in js if j['vignette']==r['scenario'] and j['condition']==r['condition']}
        assert len(found)==(0 if r['condition']=='bare' else 2)
        for order,j in sorted(found.items()):
            assert abs(j['exported_effect']-export.signed_axis_effect(j['side'],[export.score_cell(j)]))<1e-9
            b,t=('A','B') if order=='AB' else ('B','A');s=j['judgment']
            score={'scenario':r['scenario'],'side':r['side'],'order':order,'effect':j['exported_effect'],
                'bare_on':s['on_axis_'+b],'steered_on':s['on_axis_'+t],'bare_off':s['off_axis_'+b],'steered_off':s['off_axis_'+t],'evidence':s['evidence']}
            scores.append(score);lines.append(json.dumps(score,ensure_ascii=False))
        if found:
            a,b=(found[o]['exported_effect'] for o in ('AB','BA'))
            pairs.append({'scenario':r['scenario'],'side':r['side'],'AB':a,'BA':b,'mean':(a+b)/2,'strict_reversal':a*b<0,'tie':(a==0)!=(b==0)})
    for r in data['records']+data['identity_controls']:
        assert len(r['measurements'])==len(r['generated_ids'])
        for m in r['measurements']:
            assert m['next_block_exact'] and m['nonfinal_exact'] and m['rounding_error_norm']<=m['rounding_bound']
            steps.append({'scenario':r['scenario'],'side':r['side'],'identity':r.get('identity_exact',False),**m})
    for name,rows in [('scores.csv',scores),('paired.csv',pairs),('steps.csv',steps)]:
        with (folder/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (folder/'responses-and-scores.md').write_text('\n\n'.join(lines)+'\n')
    treatment=[s for s in steps if not s['identity']]
    summary={'runtime':data['runtime'],'stage_seconds':data['stage_seconds'],'judge_cost_usd':sum(j['cost_usd'] for j in js),
        'treatment_calls':len(treatment),'identity_calls':len(steps)-len(treatment),'targets':data['targets'],
        'max_relative_norm_error':max(s['norm_error']/s['desired_norm'] for s in treatment if s['desired_norm']),
        'min_direction_cosine':min(s['direction_cosine'] for s in treatment if s['direction_cosine'] is not None),'groups':{}}
    for side in ('+C','-C'):
        p=[r for r in pairs if r['side']==side];s=[r for r in scores if r['side']==side];rs=[r for r in data['records'] if r['side']==side]
        summary['groups'][side]={'AB_mean':sum(r['AB'] for r in p)/15,'BA_mean':sum(r['BA'] for r in p)/15,
            'paired_mean':sum(r['mean'] for r in p)/15,'steered_off_mean':sum(r['steered_off'] for r in s)/30,
            'strict_reversals':sum(r['strict_reversal'] for r in p),'ties':sum(r['tie'] for r in p),
            'health':{k:sum(r['health'][0][k] for r in rs) for k in ('unfinished','role_leaks','repeated')}}
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('NAMED_REPORT_PASS',json.dumps(summary),flush=True)


if __name__!='__main__':
    import modal
    from run_modal import image,cache,source_revision
    app=modal.App('jsteer-named-concepts',image=image.add_local_file(str(norm.REFERENCE),'/repo/'+str(norm.REFERENCE))
        .add_local_file(str(control.MATCHED),'/repo/'+str(control.MATCHED))
        .add_local_file(str(ROOT/'inventory.json'),'/repo/'+str(ROOT/'inventory.json'))
        .add_local_file(str(ROOT/'reference-verbal-introspection.json'),'/repo/'+str(ROOT/'reference-verbal-introspection.json'))
        .add_local_file(str(ROOT/'source-prompts.json'),'/repo/'+str(ROOT/'source-prompts.json')))
    @app.function(gpu='H100',volumes={'/cache':cache},timeout=360,max_containers=1,retries=0)
    def remote(revision:str):
        try:subprocess.run([sys.executable,'scripts/scratch/j_lens_named_concepts.py','--output','/cache/'+REMOTE,'--source-revision',revision],cwd='/repo',check=True)
        finally:
            print('NAMED_VOLUME_COMMIT_START',flush=True);cache.commit();print('NAMED_VOLUME_COMMIT_END',flush=True)
        return REMOTE
    @app.local_entrypoint()
    def launch():print('NAMED_REMOTE_PATH',remote.remote(source_revision()),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');p.add_argument('--judge',type=Path);p.add_argument('--report',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'generation.json');p.add_argument('--source-revision',default='unknown');args=p.parse_args()
    if args.self_test:self_test()
    elif args.judge:asyncio.run(norm.judge_run(args))
    elif args.report:report(args.report)
    else:run(args)
