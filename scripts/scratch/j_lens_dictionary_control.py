"""Dictionary-only GP16 control; not J-lens. PI/OpenAI Codex."""
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
import j_lens_dev15_representation as bridge
import j_lens_gap_clamp as gap

ROOT = Path('slop/logs/20260907_j_lens_dictionary_control')
MATCHED = Path('slop/logs/20260907_j_lens_norm_matched_gp/generation.json')
MATCHED_SHA = 'f980ba598b72030c5f798042ac19cbdffab032131d8259a50f351b4bac946c6c'
REMOTE = 'outputs/audits/20260907_j_lens_dictionary_control/generation.json'
LAYER = 17


@torch.inference_mode()
def construct(dictionary, signals):
    """Same nonnegative GP16, only dictionary rows differ. Verify support/index reconstruction."""
    assert torch.isfinite(dictionary).all()
    torch.testing.assert_close(dictionary.norm(dim=1), torch.ones(len(dictionary), device=dictionary.device))
    components, records = [], {}
    for condition, signal in signals.items():
        weights, component, selected, errors = gap.concept.gradient_pursuit(signal, dictionary, 16)
        support = weights.nonzero().flatten()
        assert len(selected) <= 16 and len(set(selected.tolist())) == len(selected)
        assert set(support.tolist()) <= set(selected.tolist()) and (weights >= 0).all()
        assert component.norm() > 0
        reconstruction = weights[support].double() @ dictionary[support].double()
        torch.testing.assert_close(component.double(), reconstruction, atol=1e-5, rtol=1e-4)
        components.append(component)
        records[condition] = {'selected_ids': selected.tolist(), 'nonzero_ids': support.tolist(),
            'weights': weights[support].tolist(), 'component': component.tolist(),
            'reconstruction_max_error': float((component.double()-reconstruction).abs().max()),
            'errors': errors, 'signal_norm': float(signal.norm()), 'component_norm': float(component.norm())}
    basis = torch.stack(components)
    basis /= basis.norm(dim=1, keepdim=True)
    assert torch.linalg.matrix_rank(basis) == 2
    dual = torch.linalg.pinv(basis).T
    independent = torch.linalg.solve(basis.double()@basis.double().T, basis.double())
    torch.testing.assert_close(dual.double(), independent, atol=1e-6, rtol=1e-5)
    torch.testing.assert_close(basis @ dual.T, torch.eye(2, device=basis.device), atol=1e-6, rtol=1e-5)
    return basis, dual, {'components': records, 'basis': basis.tolist(), 'dual': dual.tolist(),
        'rank': 2, 'unit_norms': basis.norm(dim=1).tolist(), 'dual_gram_max_error': float((dual.double()-independent).abs().max())}


def self_test():
    norm.self_test()  # The exact reused adapter, including real hybrid cached generation and zero cases.
    generator = torch.Generator().manual_seed(17)
    dictionary = torch.randn(48,32,generator=generator)
    dictionary /= dictionary.norm(dim=1,keepdim=True)
    signals = {'positive': dictionary[3]*2+dictionary[11], 'negative': dictionary[29]*2+dictionary[44]}
    b,d,checks = construct(dictionary,signals)
    # Independent permutation mapping: vocabulary indices are not interchangeable labels.
    permutation = torch.randperm(len(dictionary),generator=generator)
    pb,pd,pc = construct(dictionary[permutation],signals)
    torch.testing.assert_close(b,pb,atol=1e-5,rtol=1e-5)
    for name in signals:
        assert permutation[torch.tensor(pc['components'][name]['selected_ids'])].tolist() == checks['components'][name]['selected_ids']
    h=torch.randn(1,32,generator=generator)
    for side in (-1.,1.):
        after,metrics=norm.norm_matched_patch(h,b,d,torch.eye(32)[:2],torch.eye(32)[:2],side*3,side*4)
        assert torch.isfinite(after).all() and metrics['direction_cosine'] > .999
        assert torch.equal(norm.norm_matched_patch(h,b,d,torch.eye(32)[:2],torch.eye(32)[:2],side*3,side*4,0.)[0],h)
    assert gap.sha(MATCHED)==MATCHED_SHA
    print('DICTIONARY_CPU_PASS',json.dumps({'dictionary_permutation_exact':True,'support_reconstruction':True,
        'rank':checks['rank'],'dual_gram_max_error':checks['dual_gram_max_error'],'adapter_reused_without_changes':True}),flush=True)


@torch.inference_mode()
def source_control(model, tokenizer, metadata, vectors):
    fm=metadata['full_residual']
    assert gap.concept.tokenizer_content_hash(tokenizer)==fm['tokenizer_content_sha256']
    lens, checkpoint=gap.concept._load_j_lens(model,[LAYER],None)
    assert gap.sha(lens)==fm['lens_sha256']
    del checkpoint
    raw=model.lm_head.weight.detach().float()
    # Preserve every lm_head row, including padded vocabulary rows, as in the J dictionary.
    assert raw.shape[0]==model.config.get_text_config().vocab_size and max(tokenizer.get_vocab().values()) < raw.shape[0]
    assert torch.all(raw.norm(dim=1)>0)
    dictionary=raw/raw.norm(dim=1,keepdim=True)
    signals={c:torch.tensor(fm['layers']['17']['decomposition'][c]['full_signal'],device=model.device) for c in ('positive','negative')}
    b,d,construction=construct(dictionary,signals)
    construction['dictionary']='unit_rows(lm_head), vocabulary order unchanged; NO J transport'
    construction['dictionary_rows']=raw.shape[0]
    construction['tokenizer_entries']=len(tokenizer)
    construction['padded_vocabulary_rows_retained']=raw.shape[0]-len(tokenizer)
    construction['lens_sha256']=gap.sha(lens)
    construction['source_tokenizer_sha256']=gap.concept.tokenizer_content_hash(tokenizer)
    for c,record in construction['components'].items():
        ids=record['nonzero_ids']
        record['selected_tokens']=[tokenizer.decode([i]) for i in ids]
        record['selected_dictionary_rows']=dictionary[ids].tolist()
        torch.testing.assert_close(dictionary[ids], raw[ids]/raw[ids].norm(dim=1,keepdim=True),atol=0,rtol=0)
    full_b=vectors['full_residual']['+C'].shared[LAYER]['basis'].to(b)
    old_b=vectors['j_gp16']['+C'].shared[LAYER]['basis'].to(b)
    construction['direction_cosines']={name:float(torch.nn.functional.cosine_similarity((b[0]-b[1])[None],(ob[0]-ob[1])[None]))
        for name,ob in [('full_residual',full_b),('j_gp16',old_b)]}
    del raw,dictionary
    n,fit=fm['source_unique_count'],fm['source_fit_count']
    targets,calibration={},{}
    for ci,condition in enumerate(('positive','negative','baseline')):
        records=[];states=[]
        for index in range(fit,n):
            tr=fm['token_records'][ci*n+index]
            ids,mask=tr['input_ids'],tr['attention_mask']
            assert mask==[1]*sum(mask)+[0]*(len(mask)-sum(mask)) and tr['final_position']==sum(mask)-1
            assert all(t==tokenizer.pad_token_id for t,a in zip(ids,mask) if not a)
            prompt=fm['source_prompts'][condition][index]
            assert tokenizer(prompt,add_special_tokens=False).input_ids==[t for t,a in zip(ids,mask) if a]
            encoded={k:torch.tensor([tr[k]],device=model.device) for k in ('input_ids','attention_mask')}
            with gap.concept._activations(model,[LAYER]) as found:model.model(**encoded,use_cache=False)
            states.append(found[LAYER][0,tr['final_position']].float())
            records.append({'id':fm['source_ids'][index],'ordinal':ci*n+index,**tr})
        h=torch.stack(states);coords=h@d.T
        independent=h.double()@torch.linalg.solve(b.double()@b.double().T,b.double()).T
        torch.testing.assert_close(coords.double(),independent,atol=1e-5,rtol=1e-5)
        calibration[condition]={'records':records,'states':h.tolist(),'coordinates':coords.tolist(),'mean':coords.mean(0).tolist()}
        # Existing representations give an approximate replay check; frozen targets never changed.
        replay={}
        for name,pair in vectors.items():
            replay_coords=h@pair['+C'].shared[LAYER]['dual'].to(h).T
            saved=torch.tensor(metadata[name]['layers']['17']['heldout_source_coordinates'][condition],device=model.device)
            error=float((replay_coords-saved).abs().max())
            assert error<.1,(name,condition,error)  # Same pre-existing replay gate, not exact parity.
            replay[name]={'coordinate_max_error':error,'replayed_mean':replay_coords.mean(0).tolist(),'saved_mean':saved.mean(0).tolist()}
        calibration[condition]['reference_replay']=replay
        if condition!='baseline':targets['+C' if condition=='positive' else '-C']=float(coords.mean(0)[0]-coords.mean(0)[1])
        print('DICTIONARY_CALIBRATION',json.dumps({'condition':condition,'mean':coords.mean(0).tolist(),'reference_replay':replay,'records':len(records),'saved_masks_exact':True}),flush=True)
    construction['calibration']=calibration
    print('DICTIONARY_SOURCE_PASS',json.dumps({'rank':2,'targets':targets,'direction_cosines':construction['direction_cosines'],
        'supports':{c:r['selected_ids'] for c,r in construction['components'].items()},'historical_revision':fm['model_revision']}),flush=True)
    return SimpleNamespace(shared={LAYER:{'basis':b,'dual':d}}),targets,construction


def run(args):
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer,AutoModelForCausalLM
    assert not args.output.exists()
    started=time.monotonic()
    assert gap.sha(norm.REFERENCE)==norm.REFERENCE_SHA and gap.sha(MATCHED)==MATCHED_SHA
    reference=json.loads(norm.REFERENCE.read_text());matched=json.loads(MATCHED.read_text())
    assert matched['reused_records']==reference['records']
    vectors,metadata,targets,provenance=bridge.sources(args.source_root)
    assert targets==reference['targets'] and provenance==reference['provenance']
    snapshot=Path(snapshot_download(gap.MODEL,revision=gap.REVISION));assert snapshot.name==gap.REVISION
    assert gap.sha(snapshot/'config.json')==reference['model_config_sha256']
    assert gap.sha(snapshot/'model.safetensors.index.json')==reference['model_index_sha256']
    tokenizer=AutoTokenizer.from_pretrained(snapshot)
    model=AutoModelForCausalLM.from_pretrained(snapshot,dtype=torch.bfloat16).to('cuda').eval()
    print('DICTIONARY_MODEL',json.dumps({'revision':gap.REVISION,'snapshot':str(snapshot),'historical_revision':metadata['full_residual']['model_revision']}),flush=True)
    vector,new_targets,construction=source_control(model,tokenizer,metadata,vectors)
    source_seconds=time.monotonic()-started
    tokenizer.pad_token=tokenizer.eos_token
    assert gap.concept.tokenizer_content_hash(tokenizer)==reference['metrology']['generation_tokenizer']['sha256']
    data={'schema':'direct_dictionary_gp16_v1','source_revision':args.source_revision,'implementation_sha256':gap.sha(__file__),
        'dependencies_sha256':{p:gap.sha(SCRIPTS/'scratch'/p) for p in ('j_lens_norm_matched_gp.py','j_lens_dev15_representation.py','j_lens_transfer_probe.py','j_lens_gap_clamp.py')},
        'reference_sha256':norm.REFERENCE_SHA,'matched_reference_sha256':MATCHED_SHA,'model_revision':gap.REVISION,'snapshot':str(snapshot),
        'model_config_sha256':gap.sha(snapshot/'config.json'),'model_index_sha256':gap.sha(snapshot/'model.safetensors.index.json'),
        'provenance':provenance,'targets':targets,'control_targets':new_targets,'construction':construction,
        'settings':reference['settings'],'records':[],'identity_controls':[],
        'reused_records':reference['records']+matched['records'],
        'operator':'same pointwise norm-matched persistent adapter; direct residual dictionary GP16 is NOT J-lens',
        'stage_seconds':{'model_and_source':source_seconds}}
    norm.save(args.output,data)
    print('SHOULD:39source-only calibration records;30new DEV treatments+2identities;all cached norm/direction/mask/next-block checks;no source/parameter selection or rubric change.',flush=True)
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
                    with torch.inference_mode(),norm.intervention(model,vector,vectors['full_residual'][side],new_targets[side],targets['full_residual'][side],alpha,measurements):
                        output=model.generate(**encoded,do_sample=False,temperature=None,top_p=None,top_k=None,pad_token_id=tokenizer.eos_token_id,max_new_tokens=512,use_cache=True)
                except Exception as e:
                    data['failure']={'scenario':row['scenario'],'side':side,'error':repr(e),'measurements':measurements};norm.save(args.output,data);raise
                ids=output[0,encoded.input_ids.shape[1]:].tolist()
                assert len(measurements)==len(ids) and all(m['next_block_exact'] for m in measurements)
                assert [m['sequence_length'] for m in measurements]==[len(bare['input_ids'])]+[1]*(len(ids)-1)
                text=tokenizer.decode(ids,skip_special_tokens=True).strip()
                r={'scenario':row['scenario'],'prompt':row['prompt'],'condition':'direct_dictionary_gp_'+('plus' if side=='+C' else 'minus'),
                    'method':'direct_dictionary_gp','side':side,'rendered':rendered,'input_ids':bare['input_ids'],'attention_mask':encoded.attention_mask[0].tolist(),
                    'generated_ids':ids,'text':text,'measurements':measurements,'health':gap.walk.health(tokenizer,[text])}
                if not alpha:
                    assert ids==bare['generated_ids'] and all(m['actual_norm']==0 for m in measurements)
                    r['identity_exact']=True;data['identity_controls'].append(r)
                else:data['records'].append(r)
                norm.save(args.output,data)
                print('DICTIONARY_RESPONSE',json.dumps({k:v for k,v in r.items() if k not in ('input_ids','attention_mask','generated_ids','measurements')}),flush=True)
    data['stage_seconds']['generation']=time.monotonic()-generation_started
    data['runtime']={'seconds':time.monotonic()-started,'gpu':torch.cuda.get_device_name(),'peak_memory_bytes':torch.cuda.max_memory_allocated(),'torch':torch.__version__}
    assert len(data['records'])==30 and len(data['identity_controls'])==2
    norm.save(args.output,data);print('DICTIONARY_COMPLETE',json.dumps({'runtime':data['runtime'],'stages':data['stage_seconds']}),flush=True)


def report(folder):
    import export
    data=json.loads((folder/'generation.json').read_text())
    assert gap.sha(norm.REFERENCE)==data['reference_sha256'] and gap.sha(MATCHED)==data['matched_reference_sha256']
    ref=json.loads(norm.REFERENCE.read_text());matched=json.loads(MATCHED.read_text())
    assert data['reused_records']==ref['records']+matched['records']
    executed=subprocess.check_output(['git','show',data['source_revision']+':scripts/scratch/j_lens_dictionary_control.py'])
    assert hashlib.sha256(executed).hexdigest()==data['implementation_sha256']
    judgments=[]
    for path,expected in [(norm.REFERENCE.parent/'judgments.jsonl',120),(MATCHED.parent/'judgments.jsonl',60),(folder/'judgments.jsonl',60)]:
        js=[json.loads(l) for l in path.read_text().splitlines()];assert len(js)==expected;judgments+=js
    assert len(data['records'])==30 and len({(r['scenario'],r['side']) for r in data['records']})==30
    assert len(data['identity_controls'])==2 and all(r['identity_exact'] for r in data['identity_controls'])
    steps=[];scores=[];pairs=[];lines=['# All direct-dictionary GP16 comparisons','PI/OpenAI Codex. 105 prior outputs reused,30new treatments. No J-lens/frontier success claim.']
    for r in data['reused_records']+data['records']:
        lines+=['## '+r['scenario']+' / '+r['condition'],'```text',r['rendered'],'```','> '+r['text'],'Health: '+json.dumps(r['health'])]
        js={j['order']:j for j in judgments if j['vignette']==r['scenario'] and j['condition']==r['condition']}
        assert len(js)==(0 if r['condition']=='bare' else 2)
        for order,j in sorted(js.items()):
            s=j['judgment'];b,t=('A','B') if order=='AB' else ('B','A')
            assert abs(j['exported_effect']-export.signed_axis_effect(j['side'],[export.score_cell(j)]))<1e-9
            score={'scenario':r['scenario'],'method':r['method'],'side':r['side'],'condition':r['condition'],'order':order,
                'bare_on_axis':s['on_axis_'+b],'steered_on_axis':s['on_axis_'+t],'bare_off_axis':s['off_axis_'+b],
                'steered_off_axis':s['off_axis_'+t],'effect':j['exported_effect'],'evidence':s['evidence']}
            scores.append(score);lines.append(json.dumps(score,ensure_ascii=False))
        if js:
            a,b=(js[o]['exported_effect'] for o in ('AB','BA'))
            pairs.append({'scenario':r['scenario'],'method':r['method'],'side':r['side'],'AB':a,'BA':b,'mean':(a+b)/2,
                'strict_reversal':a*b<0,'tie_disagreement':(a==0)!=(b==0)})
    for r in data['records']+data['identity_controls']:
        ms=r['measurements'];assert len(ms)==len(r['generated_ids'])
        assert [m['sequence_length'] for m in ms]==[len(r['input_ids'])]+[1]*(len(ms)-1)
        for m in ms:
            assert m['next_block_exact'] and m['nonfinal_exact'] and m['rounding_error_norm']<=m['rounding_bound']
            assert all(torch.isfinite(torch.tensor(m[k])) for k in ('actual_norm','reference_realized_norm','gp_nominal_norm'))
            steps.append({'scenario':r['scenario'],'side':r['side'],'identity':r.get('identity_exact',False),**m})
    for name,rs in [('steps.csv',steps),('scores.csv',scores),('paired.csv',pairs)]:
        with (folder/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rs[0]),lineterminator='\n');w.writeheader();w.writerows(rs)
    (folder/'responses-and-scores.md').write_text('\n\n'.join(lines)+'\n')
    treatment=[m for m in steps if not m['identity']]
    summary={'new_responses':32,'reused_responses':105,'new_judgments':60,'judge_cost_usd':sum(j['cost_usd'] for j in judgments[-60:]),
        'runtime':data['runtime'],'stages':data['stage_seconds'],'direction_cosines':data['construction']['direction_cosines'],
        'control_targets':data['control_targets'],'treatment_calls':len(treatment),'identity_calls':len(steps)-len(treatment),
        'max_relative_norm_error':max(m['norm_error']/m['desired_norm'] for m in treatment if m['desired_norm']),
        'max_absolute_norm_error':max(m['norm_error'] for m in treatment),
        'min_direction_cosine':min(m['direction_cosine'] for m in treatment if m['direction_cosine'] is not None),
        'zero_reference_count':sum(m['zero_reference'] for m in treatment),'groups':{}}
    for method in ('full_residual','j_gp16','norm_matched_gp','direct_dictionary_gp'):
        for side in ('+C','-C'):
            ps=[p for p in pairs if p['method']==method and p['side']==side];ss=[s for s in scores if s['method']==method and s['side']==side]
            rs=[r for r in data['reused_records']+data['records'] if r['method']==method and r['side']==side]
            summary['groups'][method+side]={'AB_mean':sum(p['AB'] for p in ps)/15,'BA_mean':sum(p['BA'] for p in ps)/15,
                'paired_mean':sum(p['mean'] for p in ps)/15,'steered_off_mean':sum(s['steered_off_axis'] for s in ss)/30,
                'strict_reversals':sum(p['strict_reversal'] for p in ps),'ties':sum(p['tie_disagreement'] for p in ps),
                'health':{k:sum(r['health'][0][k] for r in rs) for k in ('unfinished','role_leaks','repeated')}}
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('DICTIONARY_REPORT_PASS',json.dumps(summary),flush=True)


if __name__!='__main__':
    import modal
    from run_modal import image,cache,source_revision
    app=modal.App('jsteer-dictionary-control',image=image.add_local_file(str(norm.REFERENCE),'/repo/'+str(norm.REFERENCE)).add_local_file(str(MATCHED),'/repo/'+str(MATCHED)))
    @app.function(gpu='H100',volumes={'/cache':cache},timeout=360,max_containers=1,retries=0)
    def remote(revision:str):
        try:subprocess.run([sys.executable,'scripts/scratch/j_lens_dictionary_control.py','--source-root','/cache/outputs/experiments','--output','/cache/'+REMOTE,'--source-revision',revision],cwd='/repo',check=True)
        finally:
            print('DICTIONARY_VOLUME_COMMIT_START',flush=True);cache.commit();print('DICTIONARY_VOLUME_COMMIT_END',flush=True)
        return REMOTE
    @app.local_entrypoint()
    def launch():print('DICTIONARY_REMOTE_PATH',remote.remote(source_revision()),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');p.add_argument('--judge',type=Path);p.add_argument('--report',type=Path)
    p.add_argument('--source-root',type=Path,default=Path('outputs/experiments'));p.add_argument('--output',type=Path,default=ROOT/'generation.json');p.add_argument('--source-revision',default='unknown');args=p.parse_args()
    if args.self_test:self_test()
    elif args.judge:asyncio.run(norm.judge_run(args))
    elif args.report:report(args.report)
    else:run(args)
