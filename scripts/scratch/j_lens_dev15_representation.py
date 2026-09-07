"""Fixed DEV15 representation bridge, not calibrated frontier. PI/OpenAI Codex."""
import argparse
import asyncio
from contextlib import nullcontext
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

SCRIPTS = Path('/repo/scripts') if Path('/repo/scripts').is_dir() else Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SCRIPTS), str(SCRIPTS/'scratch')]
import torch
import j_lens_gap_clamp as gap
import j_lens_transfer_probe as probe
from steering_lite import Vector

ROOT = Path('slop/logs/20260907_j_lens_dev15_representation')
GP_SOURCE = 'j-lens-persona-components-source-v15'
GP_SHA = 'db8d2ebf1fb4370888aac03583789930a8f42d22113898994c3661a61dfb7d40'
LAYER = 17


def sources(root):
    full, fm, _, fs = gap.load_source(root)
    path = root/GP_SOURCE/'extraction/metadata.json'
    assert gap.sha(path) == GP_SHA
    gm = json.loads(path.read_text())
    for key in ('source_ids', 'source_prompts', 'spec', 'token_records', 'lens_sha256',
                'tokenizer_content_sha256', 'source_fit_count', 'source_holdout_count', 'source_layers'):
        assert fm[key] == gm[key], key
    assert fm['layers']['17']['decomposition'] == gm['layers']['17']['decomposition']
    gp = {s: Vector.load(str(root/GP_SOURCE/gm['vector_files'][s])) for s in ('+C', '-C')}
    vectors, metadata = {'full_residual': full, 'j_gp16': gp}, {'full_residual': fm, 'j_gp16': gm}
    targets, checks = {}, {}
    for name, pair in vectors.items():
        meta = metadata[name]
        targets[name], checks[name] = {}, {}
        for side, vector in pair.items():
            assert gap.content_hash(vector) == meta['vector_content_sha256'][side]
            b, d = (vector.shared[LAYER][k] for k in ('basis', 'dual'))
            field = 'full_signal' if name == 'full_residual' else 'gp_component'
            expected = torch.tensor([meta['layers']['17']['decomposition'][c][field] for c in ('positive', 'negative')])
            expected /= expected.norm(dim=1, keepdim=True)
            torch.testing.assert_close(b, expected, atol=1e-7, rtol=1e-6)
            independent = torch.linalg.solve(b.double()@b.double().T, b.double())
            torch.testing.assert_close(d.double(), independent, atol=1e-6, rtol=1e-5)
            assert torch.linalg.matrix_rank(b) == 2
            assert int(vector.shared[LAYER]['target_index']) == (0 if side == '+C' else 1)
            condition = 'positive' if side == '+C' else 'negative'
            coords = torch.tensor(meta['layers']['17']['heldout_source_coordinates'][condition], dtype=torch.float64)
            mean = coords.mean(0)
            recorded = torch.tensor(meta['layers']['17']['heldout_source_coordinate_means'][condition], dtype=torch.float64)
            torch.testing.assert_close(mean, recorded, atol=1e-5, rtol=1e-5)
            # Keep the original FP32 mean convention and saved calibration, not DEV outcomes.
            targets[name][side] = float(recorded[0]-recorded[1])
            checks[name][side] = {'rank': 2, 'basis_norms': b.norm(dim=1).tolist(),
                'dual_gram_max_error': float((d.double()-independent).abs().max()),
                'heldout_mean_max_error': float((mean-recorded).abs().max()), 'target_gap': targets[name][side]}
    rows, cohort_sha = gap.walk.read_cohort(15)
    instruction = fm['spec']['baseline_instruction']
    from steering_lite.data.personas import load_suffixes
    import random
    unique = {entry['user_msg']: entry for entry in load_suffixes(thinking=False)}
    sampled = random.Random(fm['spec']['source_seed']).sample(list(unique.values()),len(unique))
    contents = [entry['user_msg'] for entry in sampled]
    assert [hashlib.sha256(p.encode()).hexdigest() for p in contents] == fm['source_ids']
    rendered_contents = [p.split(instruction+'\n\n',1)[1].split('<|im_end|>',1)[0] for p in fm['source_prompts']['baseline']]
    assert [p.strip() for p in contents] == rendered_contents
    normalize = lambda s: ' '.join(s.casefold().split())
    fit = fm['source_fit_count']
    groups = {'fit': [{'id': i, 'prompt': p} for i,p in zip(fm['source_ids'][:fit], contents[:fit])],
        'calibration': [{'id': i, 'prompt': p} for i,p in zip(fm['source_ids'][fit:], contents[fit:])],
        'dev15': [{'id': r['scenario'], 'prompt': r['prompt']} for r in rows]}
    overlaps = {}
    for a,b in (('fit','calibration'), ('fit','dev15'), ('calibration','dev15')):
        overlaps[a+'__'+b] = [{'a': x['id'], 'b': y['id']} for x in groups[a] for y in groups[b]
            if x['id']==y['id'] or normalize(x['prompt'])==normalize(y['prompt']) or normalize(x['prompt']) in normalize(y['prompt']) or normalize(y['prompt']) in normalize(x['prompt'])]
    provenance = {'metadata_sha256': {'full_residual': fs, 'j_gp16': GP_SHA}, 'cohort_sha256': cohort_sha,
        'source_order': 'saved seeded order, first52 fit, last13 calibration; no reordering',
        'source_groups': groups, 'overlaps_exact_or_normalized_substring': overlaps,
        'checks': checks, 'lens_sha256': fm['lens_sha256'], 'source_token_records_sha256': hashlib.sha256(json.dumps(fm['token_records']).encode()).hexdigest(),
        'calibration_use': 'only saved source-heldout coordinates; no DEV answers or judgments used',
        'historical_model_revision': fm['model_revision']}
    return vectors, metadata, targets, provenance


def self_test():
    vectors, _, targets, provenance = sources(Path('outputs/experiments'))
    probe.self_test()
    torch.manual_seed(17)
    for name,pair in vectors.items():
        for side,v in pair.items():
            b = v.shared[LAYER]['basis'].double()
            h = torch.randn(4,b.shape[1],dtype=torch.float64)
            c = h@torch.linalg.solve(b@b.T,b).T
            target = targets[name][side]
            expected = h+((target-(c[:,0]-c[:,1]))/2)[:,None]*(b[0]-b[1])
            actual = gap.gap_patch(h.float(), v, LAYER, 1., target)
            torch.testing.assert_close(actual.double(), expected, atol=1e-5, rtol=1e-5)
            assert torch.equal(gap.gap_patch(h.float(), v, LAYER, 0., target), h.float())
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print('DEV15_CPU_PASS',json.dumps(provenance),flush=True)


@torch.inference_mode()
def metrology(model, tokenizer, metadata, vectors, targets):
    fm = metadata['full_residual']
    print('EXTRACTION_TOKENIZER',json.dumps({'actual_sha256':gap.concept.tokenizer_content_hash(tokenizer),'expected_sha256':fm['tokenizer_content_sha256'],'pad_token_id':tokenizer.pad_token_id,'eos_token_id':tokenizer.eos_token_id}),flush=True)
    assert gap.concept.tokenizer_content_hash(tokenizer) == fm['tokenizer_content_sha256']
    for ci,condition in enumerate(('positive','negative','baseline')):
        for index,prompt in enumerate(fm['source_prompts'][condition]):
            record=fm['token_records'][ci*65+index]
            assert tokenizer(prompt,add_special_tokens=False).input_ids == [tid for tid,att in zip(record['input_ids'],record['attention_mask']) if att]
    lens, checkpoint = gap.concept._load_j_lens(model, [LAYER], None)
    assert gap.sha(lens) == fm['lens_sha256']
    raw = model.lm_head.weight.detach().float()@checkpoint['J'][LAYER].float().to(model.device)
    dictionary = raw/raw.norm(dim=1,keepdim=True)
    result = {'lens_sha256': gap.sha(lens), 'dictionary': 'unit rows lm_head @ J17, vocabulary order unchanged', 'gp': {}, 'holdout': {}}
    for condition in ('positive','negative'):
        saved = fm['layers']['17']['decomposition'][condition]
        signal = torch.tensor(saved['full_signal'],device=model.device)
        w,component,_,_ = gap.concept.gradient_pursuit(signal,dictionary,16)
        expected = torch.tensor(saved['gp_component'],device=model.device)
        print('GP_REPLAY',json.dumps({'condition':condition,'actual_support':w.nonzero().flatten().tolist(),'saved_support':saved['selected_ids'],'component_max_error':float((component-expected).abs().max())}),flush=True)
        assert w.nonzero().flatten().tolist() == saved['selected_ids']
        torch.testing.assert_close(component,expected,atol=1e-5,rtol=1e-4)
        selected = torch.tensor(saved['selected_ids'],device=model.device)
        independent = torch.tensor(saved['weights_unit_dictionary'],device=model.device,dtype=torch.float64)@dictionary[selected].double()
        torch.testing.assert_close(component.double(),independent,atol=1e-5,rtol=1e-4)
        assert [tokenizer.decode([i]) for i in saved['selected_ids']] == saved['selected_tokens']
        result['gp'][condition] = {'support_exact': True, 'component_max_error': float((component-expected).abs().max()), 'selected_ids': saved['selected_ids']}
    del raw,dictionary,checkpoint
    # Replay all39 calibration records with original padded token IDs, no fitting.
    n,fit = fm['source_unique_count'],fm['source_fit_count']
    for ci,condition in enumerate(('positive','negative','baseline')):
        states=[]
        for index in range(fit,n):
            tr = fm['token_records'][ci*n+index]
            encoded = {k:torch.tensor([tr[k]],device=model.device) for k in ('input_ids','attention_mask')}
            with gap.concept._activations(model,[LAYER]) as found:
                model.model(**encoded,use_cache=False)
            states.append(found[LAYER][0,tr['final_position']].float())
        h=torch.stack(states)
        for name,pair in vectors.items():
            d=pair['+C'].shared[LAYER]['dual'].to(model.device)
            coords=h@d.T
            saved=torch.tensor(metadata[name]['layers']['17']['heldout_source_coordinates'][condition],device=model.device)
            error=float((coords-saved).abs().max())
            # BF16 kernel/batch differences are measured, never silently recalibrated.
            result['holdout'][name+'_'+condition]={'coordinate_max_error':error,'replayed_mean':coords.mean(0).tolist(),'saved_mean':saved.mean(0).tolist()}
            print('CALIBRATION_REPLAY',json.dumps({'representation':name,'condition':condition,**result['holdout'][name+'_'+condition]}),flush=True)
            assert error < .1, (name,condition,error)
    print('DEV15_METROLOGY_PASS',json.dumps(result),flush=True)
    return result


def run(args):
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    assert not args.output.exists()
    started=time.monotonic()
    vectors,metadata,targets,provenance=sources(args.source_root)
    print('DEV15_PROVENANCE',json.dumps(provenance),flush=True)
    assert not any(provenance['overlaps_exact_or_normalized_substring'].values()), 'source/DEV overlap; report before proceeding'
    snapshot=Path(snapshot_download(gap.MODEL,revision=gap.REVISION))
    assert snapshot.name==gap.REVISION
    tokenizer=AutoTokenizer.from_pretrained(snapshot)
    print('PINNED_SNAPSHOT',str(snapshot),flush=True)
    model=AutoModelForCausalLM.from_pretrained(snapshot,dtype=torch.bfloat16).to('cuda').eval()
    verification=metrology(model,tokenizer,metadata,vectors,targets)
    rows,_=gap.walk.read_cohort(15)
    original_ids=[tokenizer(p,add_special_tokens=False).input_ids for p in gap.walk.generation_inputs(tokenizer,rows)]
    tokenizer.pad_token=tokenizer.eos_token
    assert original_ids==[tokenizer(p,add_special_tokens=False).input_ids for p in gap.walk.generation_inputs(tokenizer,rows)]
    verification['generation_tokenizer']={'sha256':gap.concept.tokenizer_content_hash(tokenizer),'pad_token_id':tokenizer.pad_token_id,'eos_token_id':tokenizer.eos_token_id,'batch1_ids_exact':True}
    print('GENERATION_TOKENIZER',json.dumps(verification['generation_tokenizer']),flush=True)
    data={'schema':'dev15_representation_v1','source_revision':args.source_revision,'implementation_sha256':gap.sha(__file__),
        'hook_implementation_sha256':gap.sha(probe.__file__),'model_revision':gap.REVISION,'snapshot':str(snapshot),
        'model_config_sha256':gap.sha(snapshot/'config.json'),'model_index_sha256':gap.sha(snapshot/'model.safetensors.index.json'),
        'provenance':provenance,'metrology':verification,'targets':targets,
        'settings':{'layer':17,'alpha':1.,'dtype':'bfloat16','batch':1,'max_new_tokens':512,'use_cache':True,'schedule':'prefill+decode final position'},
        'records':[],'identity_controls':[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    print('SHOULD: DEV15x5=75 cells; source calibration only; all cached calls measured; alpha0 exact; no changed rubric; no calibrated frontier claim.',flush=True)
    for ri,row in enumerate(rows):
        rendered=gap.walk.generation_inputs(tokenizer,[row])[0]
        encoded=tokenizer(rendered,return_tensors='pt',add_special_tokens=False).to(model.device)
        conditions=[('bare',None,None)]+[(name+('_plus' if s=='+C' else '_minus'),name,s) for name in vectors for s in ('+C','-C')]
        for condition,name,side in conditions:
            measurements=[]
            context=nullcontext() if name is None else probe.persistent_gap(model,vectors[name][side],targets[name][side],1.,measurements)
            with torch.inference_mode(),context:
                output=model.generate(**encoded,do_sample=False,temperature=None,top_p=None,top_k=None,pad_token_id=tokenizer.eos_token_id,max_new_tokens=512,use_cache=True)
            ids=output[0,encoded.input_ids.shape[1]:].tolist()
            if name is None: bare_ids=ids
            else:
                assert len(measurements)==len(ids)
                assert [m['sequence_length'] for m in measurements]==[len(encoded.input_ids[0])]+[1]*(len(ids)-1)
                assert all(m['next_block_input_exact'] for m in measurements)
            text=tokenizer.decode(ids,skip_special_tokens=True).strip()
            record={'scenario':row['scenario'],'prompt':row['prompt'],'condition':condition,'method':name,'side':side,
                'rendered':rendered,'input_ids':encoded.input_ids[0].tolist(),'generated_ids':ids,'text':text,
                'measurements':measurements,'health':gap.walk.health(tokenizer,[text])}
            data['records'].append(record)
            print('DEV15_RESPONSE',json.dumps({k:v for k,v in record.items() if k not in ('measurements','input_ids','generated_ids')},ensure_ascii=False),flush=True)
            args.output.write_text(json.dumps(data)+'\n')
        if ri==0:
            for name,pair in vectors.items():
                measurements=[]
                with torch.inference_mode(),probe.persistent_gap(model,pair['-C'],targets[name]['-C'],0.,measurements):
                    output=model.generate(**encoded,do_sample=False,temperature=None,top_p=None,top_k=None,pad_token_id=tokenizer.eos_token_id,max_new_tokens=512,use_cache=True)
                assert output[0,encoded.input_ids.shape[1]:].tolist()==bare_ids
                assert all(not any(m['all_position_patch_norms']) and m['next_block_input_exact'] for m in measurements)
                data['identity_controls'].append({'method':name,'scenario':row['scenario'],'identity_exact':True,'calls':len(measurements)})
    data['runtime']={'seconds':time.monotonic()-started,'gpu':torch.cuda.get_device_name(),'peak_memory_bytes':torch.cuda.max_memory_allocated(),'torch':torch.__version__}
    assert len(data['records'])==75
    args.output.write_text(json.dumps(data)+'\n')
    print('DEV15_COMPLETE',json.dumps(data['runtime']),flush=True)


async def judge_run(args):
    import judge
    import export
    from openai import AsyncOpenAI
    assert not args.output.exists()
    data=json.loads(args.judge.read_text())
    client=AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'],base_url='https://openrouter.ai/api/v1',timeout=60.,max_retries=0)
    semaphore=asyncio.Semaphore(3)
    async def one(r,order):
        bare=next(b for b in data['records'] if b['scenario']==r['scenario'] and b['condition']=='bare')
        row={'bare':bare['text'],'steered':r['text'],'prompt':r['prompt'],'vignette':r['scenario'],'side':r['side'],
            'run':'dev15-representation','method':r['method'],'source':str(args.judge)}
        async with semaphore:
            result=await asyncio.wait_for(judge.judge_one(client,row,order,0),240)
        result['condition']=r['condition'];result['exported_effect']=export.signed_axis_effect(r['side'],[export.score_cell(result)])
        assert abs(result['exported_effect']-gap.mapped_effect(result['judgment'],order,r['side']))<1e-9
        with args.output.open('a') as f:f.write(json.dumps(result,ensure_ascii=False)+'\n')
        print('DEV15_JUDGMENT',json.dumps(result,ensure_ascii=False),flush=True)
    try:await asyncio.gather(*(one(r,o) for r in data['records'] if r['condition']!='bare' for o in ('AB','BA')))
    finally:await client.close()


def report(folder):
    import export
    data=json.loads((folder/'generation.json').read_text())
    judgments=[json.loads(l) for l in (folder/'judgments.jsonl').read_text().splitlines()]
    assert len(data['records'])==75 and len(judgments)==120
    scores=[];paired=[];lines=['# Fixed DEV15 representation responses and scores','PI/OpenAI Codex. Not calibrated frontier.']
    for r in data['records']:
        lines += ['## '+r['scenario']+' / '+r['condition'],'```text',r['rendered'],'```','> '+r['text'],'Health: '+json.dumps(r['health'])]
        js={j['order']:j for j in judgments if j['condition']==r['condition'] and j['vignette']==r['scenario']}
        for order,j in sorted(js.items()):
            s=j['judgment'];b,t=('A','B') if order=='AB' else ('B','A')
            assert abs(j['exported_effect']-export.signed_axis_effect(j['side'],[export.score_cell(j)]))<1e-9
            score={'scenario':r['scenario'],'method':r['method'],'side':r['side'],'condition':r['condition'],'order':order,
                'bare_on_axis':s['on_axis_'+b],'steered_on_axis':s['on_axis_'+t],'bare_off_axis':s['off_axis_'+b],
                'steered_off_axis':s['off_axis_'+t],'effect':j['exported_effect'],'evidence':s['evidence']}
            scores.append(score);lines += [json.dumps(score,ensure_ascii=False)]
        if js:
            a,b=(js[o]['exported_effect'] for o in ('AB','BA'))
            paired.append({'scenario':r['scenario'],'method':r['method'],'side':r['side'],'AB':a,'BA':b,'mean':(a+b)/2,'strict_reversal':a*b<0,'tie_disagreement':(a==0)!=(b==0)})
    for filename,rows in (('scores.csv',scores),('paired.csv',paired)):
        with (folder/filename).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (folder/'responses-and-scores.md').write_text('\n\n'.join(lines)+'\n')
    summary={'cells':75,'judgments':120,'judge_cost_usd':sum(j['cost_usd'] for j in judgments),'runtime':data['runtime'],
        'strict_reversals':sum(p['strict_reversal'] for p in paired),'tie_disagreements':sum(p['tie_disagreement'] for p in paired),
        'groups':{},'max_target_gap_error':max(m['target_gap_error'] for r in data['records'] for m in r['measurements'])}
    for name in ('full_residual','j_gp16'):
        for side in ('+C','-C'):
            ps=[p for p in paired if p['method']==name and p['side']==side]
            ss=[s for s in scores if s['method']==name and s['side']==side]
            summary['groups'][name+side]={'AB_mean':sum(p['AB'] for p in ps)/15,'BA_mean':sum(p['BA'] for p in ps)/15,
                'paired_mean':sum(p['mean'] for p in ps)/15,'steered_off_mean':sum(s['steered_off_axis'] for s in ss)/30,
                'min_paired':min(p['mean'] for p in ps),'max_paired':max(p['mean'] for p in ps)}
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('DEV15_REPORT_PASS',json.dumps(summary),flush=True)


if __name__ != '__main__':
    import modal
    from run_modal import image,cache,source_revision
    app=modal.App('jsteer-dev15-representation',image=image)
    @app.function(gpu='H100',volumes={'/cache':cache},timeout=360,max_containers=1,retries=0)
    def remote(revision:str):
        destination=Path('/cache/outputs/audits/20260907_j_lens_dev15_representation/generation.json')
        try:
            subprocess.run([sys.executable,'scripts/scratch/j_lens_dev15_representation.py','--source-root','/cache/outputs/experiments','--output',str(destination),'--source-revision',revision],cwd='/repo',check=True)
            return destination.read_text()
        finally:cache.commit()
    @app.local_entrypoint()
    def launch():
        destination=ROOT/'generation.json';assert not destination.exists()
        result=remote.remote(source_revision());destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(result)
        print('DEV15_DOWNLOADED',destination,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true');parser.add_argument('--report',type=Path)
    parser.add_argument('--source-root',type=Path,default=Path('outputs/experiments'));parser.add_argument('--output',type=Path,default=ROOT/'generation.json')
    parser.add_argument('--source-revision',default='unknown');parser.add_argument('--judge',type=Path)
    args=parser.parse_args()
    if args.self_test:self_test()
    elif args.report:report(args.report)
    elif args.judge:asyncio.run(judge_run(args))
    else:run(args)
