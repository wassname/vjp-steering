"""Fixed-dose raw named-GP contrast; exploratory DEV, not a frontier. PI/OpenAI Codex."""
import argparse
import asyncio
from contextlib import contextmanager
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

SCRIPTS = Path('/repo/scripts') if Path('/repo/scripts').is_dir() else Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SCRIPTS), str(SCRIPTS/'scratch')]
import torch
import j_lens_norm_matched_gp as norm
import j_lens_gap_clamp as gap

ROOT = Path('slop/logs/20260907_j_lens_additive_concepts')
SOURCE = Path('slop/logs/20260907_j_lens_named_concepts/generation.json')
STATES = Path('slop/logs/20260907_j_lens_transfer_probe/generation.json')
LAYER = 17
SOURCE_SHA = '9b47dcb594efc67f9b3491013273106346a0afb8c32fea3a6111e6121ca34a53'


SINGLE_ROOT = ROOT.with_name("20260907_j_lens_single_concept")
PROJECTION_ROOT = ROOT.with_name('20260907_j_lens_projection_removal')


def dose_root(alpha, single_concept=False, projection_removal=False):
    if projection_removal:
        assert alpha == 1 and not single_concept, 'Projection removal is fraction1, minus-only'
        return PROJECTION_ROOT
    if single_concept:
        assert alpha == 4
        return SINGLE_ROOT
    assert alpha in (1, 2, 4), 'Only the individually authorized doses are supported'
    return ROOT if alpha == 1 else ROOT.with_name(ROOT.name+f'_alpha{alpha}')


def source_contrast(single_concept=False):
    assert gap.sha(SOURCE) == SOURCE_SHA
    data = json.loads(SOURCE.read_text())
    assert data['model_revision'] == gap.REVISION
    c = data['construction']
    assert c['inventory']['positive'] == 'sycophancy' and c['inventory']['negative'] == 'skepticism'
    assert len(c['source_records']) == 102
    parts = []
    for name in ('positive', 'negative'):
        r = c['components'][name]
        component = torch.tensor(r['component'], dtype=torch.float32)
        rows = torch.tensor(r['dictionary_rows'], dtype=torch.float64)
        weights = torch.tensor(r['weights'], dtype=torch.float64)
        # Saved weights correspond to the full dictionary; retain exact nonzero vocabulary indices.
        if len(weights) != len(rows):
            weights = weights[r['nonzero_ids']]
        independent = weights @ rows
        torch.testing.assert_close(component.double(), independent, atol=1e-5, rtol=1e-4)
        assert abs(component.norm().item()-r['component_norm']) < 1e-5
        parts.append(component)
    delta = parts[0]-parts[1]
    assert torch.isfinite(delta).all() and delta.norm() > 0
    if single_concept:
        delta = parts[0] * (delta.norm() / parts[0].norm())
    return data, delta


def additive_patch(h, contrast, signed_alpha):
    """No normalization, target coordinates, pseudoinverse or state-dependent dose."""
    desired = signed_alpha*contrast.float()
    after = h+desired.to(h)
    actual = after.float()-h.float()
    bound = torch.finfo(h.dtype).eps*(h.float().norm()+2*desired.norm())+1e-6
    assert torch.isfinite(after).all() and (actual-desired).norm() <= bound
    if not signed_alpha:
        assert torch.equal(after, h)
    return after, {'signed_alpha':signed_alpha, 'desired_norm':float(desired.norm()),
        'actual_norm':float(actual.norm()), 'norm_error':float(abs(actual.norm()-desired.norm())),
        'rounding_error_norm':float((actual-desired).norm()), 'rounding_bound':float(bound),
        'direction_cosine':float(torch.nn.functional.cosine_similarity(actual, desired[None]).item()) if actual.norm() and desired.norm() else None}


def projection_patch(h, direction, fraction):
    """Remove a single coordinate, not a constant displacement; BF16 need not reach zero."""
    assert fraction in (0., 1.)
    assert h.ndim == 2 and h.shape[0] == 1 and direction.shape == (h.shape[-1],)
    unit = direction.float() / direction.float().norm()
    assert torch.isfinite(unit).all()
    coordinate = h.float() @ unit
    desired = -fraction * coordinate[..., None] * unit
    after = (h.float() + desired).to(h.dtype)
    actual = after.float() - h.float()
    residual = after.float() @ unit
    orthogonal_change = actual - (actual @ unit)[..., None] * unit
    bound = torch.finfo(h.dtype).eps * (h.float().norm() + 2*desired.norm()) + 1e-6
    assert torch.isfinite(after).all() and (actual-desired).norm() <= bound
    assert orthogonal_change.norm() <= bound
    assert torch.max(abs(residual - (1-fraction)*coordinate)) <= bound
    if fraction == 0:
        assert torch.equal(after, h)
    return after, {'operator':'projection_removal', 'removal_fraction':fraction,
        'coordinate_before':float(coordinate.item()), 'coordinate_after':float(residual.item()),
        'desired_norm':float(desired.norm()), 'actual_norm':float(actual.norm()),
        'norm_error':float(abs(actual.norm()-desired.norm())),
        'orthogonal_change_norm':float(orthogonal_change.norm()),
        'rounding_error_norm':float((actual-desired).norm()), 'rounding_bound':float(bound)}


def intervention_patch(h, direction, strength, projection_removal=False):
    return (projection_patch if projection_removal else additive_patch)(h, direction, strength)


@contextmanager
def intervention(model, contrast, signed_alpha, measurements, layer=LAYER, projection_removal=False):
    contrast = contrast.to(model.device)
    inserted = None
    def patch(_m, _i, output):
        nonlocal inserted
        before = output[0] if isinstance(output, tuple) else output
        h = before.clone()
        h[:, -1], metrics = intervention_patch(before[:, -1], contrast, signed_alpha, projection_removal)
        assert torch.equal(h[:, :-1], before[:, :-1])
        measurements.append({'call':len(measurements),'sequence_length':h.shape[1], 'position':h.shape[1]-1,
            'nonfinal_exact':True,'next_block_exact':False,**metrics})
        inserted = h[:, -1].clone()
        return (h,*output[1:]) if isinstance(output,tuple) else h
    def check(_m, inputs, kwargs):
        h = kwargs.get('hidden_states', inputs[0] if inputs else None)
        assert torch.equal(h[:, -1], inserted)
        measurements[-1]['next_block_exact'] = True
    handle = model.model.layers[layer].register_forward_hook(patch)
    following = model.model.layers[layer+1].register_forward_pre_hook(check, with_kwargs=True)
    try:
        yield
    finally:
        handle.remove(); following.remove()


def self_test(alpha=1, single_concept=False):
    from transformers import Qwen3_5TextConfig, Qwen3_5ForCausalLM
    root = dose_root(alpha, single_concept)
    data, contrast = source_contrast(single_concept)
    # Exact named source states plus prior pinned-model DEV prefill states, NOT named decode states.
    earlier = json.loads(STATES.read_text())
    assert earlier['model_revision'] == data['model_revision']
    states = [('named_source', torch.tensor(h).to(torch.bfloat16)) for h in data['construction']['source_states']]
    states += [('earlier_transfer_prefill',torch.tensor(r['final_states']['17']).to(torch.bfloat16)) for r in earlier['records']]
    rows = []
    for group,h in states:
        for sign in (-1.,1.):
            after,m = additive_patch(h[None], contrast, sign*alpha)
            independent = (h.double()+(sign*alpha*contrast).to(h).double()).to(h)
            assert m['signed_alpha'] == sign*alpha
            assert abs(m['desired_norm']-alpha*float(contrast.norm())) < 1e-6
            assert torch.equal(after[0],independent) and m['actual_norm'] > 0 and m['direction_cosine'] > .99
            assert torch.equal(additive_patch(h[None],contrast,0.)[0],h[None])
            rows.append({'group':group,**m})
    config=Qwen3_5TextConfig(vocab_size=64,hidden_size=32,intermediate_size=64,num_hidden_layers=3,
        num_attention_heads=2,num_key_value_heads=1,head_dim=16,layer_types=['linear_attention','full_attention','linear_attention'],
        linear_num_key_heads=2,linear_num_value_heads=2,linear_key_head_dim=8,linear_value_head_dim=8,pad_token_id=0,eos_token_id=63)
    torch.manual_seed(17)
    model=Qwen3_5ForCausalLM(config).eval()
    v=contrast[:32].clone()
    assert v.norm() > 0
    inputs={'input_ids':torch.tensor([[1,2,3,4]]),'attention_mask':torch.ones(1,4,dtype=torch.long)}
    def generate():return model.generate(**inputs,max_new_tokens=4,do_sample=False,use_cache=True)
    with torch.inference_mode():
        bare=generate()
        for sign in (-1.,1.):
            for dose in (0.,alpha):
                ms=[]
                with intervention(model,v,sign*dose,ms,layer=1):out=generate()
                assert len(ms)==out.shape[1]-4
                assert [m['sequence_length'] for m in ms]==[4]+[1]*(len(ms)-1)
                assert all(m['next_block_exact'] and m['nonfinal_exact'] for m in ms)
                assert all(m['signed_alpha']==sign*dose for m in ms)
                assert all(abs(m['desired_norm']-float((sign*dose*v).norm()))<1e-6 for m in ms)
                if not dose:assert torch.equal(out,bare) and all(m['actual_norm']==0 for m in ms)
        assert torch.equal(generate(),bare)
    result={'source_sha256':gap.sha(SOURCE),'earlier_states_sha256':gap.sha(STATES),'fixed_alpha':alpha, 'single_concept':single_concept, 'vector':contrast.tolist(),
        'requested_norm':alpha*float(contrast.norm()), 'raw_contrast_norm':float(contrast.norm()),'state_count':len(states),'cases':len(rows),'zero_updates':0,
        'realized_norm_min':min(r['actual_norm'] for r in rows),'realized_norm_median':statistics.median(r['actual_norm'] for r in rows),
        'realized_norm_max':max(r['actual_norm'] for r in rows),'min_direction_cosine':min(r['direction_cosine'] for r in rows),
        'max_absolute_norm_error':max(r['norm_error'] for r in rows),'both_signs':True,'cached_identity_next_block_cleanup':True,
        'limit':'102 actual named source states +21 earlier transfer final-prefill states; no named-source decode hidden states persisted', 'rows':rows}
    root.mkdir(parents=True,exist_ok=True)
    norm.save(root/'offline-bf16.json',result)
    print('ADDITIVE_CPU_PASS',json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)


def generation_tokenizer(snapshot, source, reference):
    """Verify extraction identity before the existing generation-only pad override."""
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(snapshot)
    raw_hash = gap.concept.tokenizer_content_hash(tokenizer)
    assert raw_hash == source['construction']['source_tokenizer_sha256']
    tokenizer.pad_token = tokenizer.eos_token
    generation_hash = gap.concept.tokenizer_content_hash(tokenizer)
    assert generation_hash == reference['metrology']['generation_tokenizer']['sha256']
    print('TOKENIZER_IDENTITIES_PASS', json.dumps({'raw_sha256':raw_hash, 'generation_sha256':generation_hash}), flush=True)
    return tokenizer


def run(args):
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer,AutoModelForCausalLM
    assert not args.output.exists()
    source,contrast=source_contrast(args.single_concept or args.projection_removal)
    offline_path=dose_root(args.alpha,args.single_concept,args.projection_removal)/'offline-bf16.json'
    offline=json.loads(offline_path.read_text())
    assert offline['source_sha256']==gap.sha(SOURCE) and offline['zero_updates']==0
    assert offline['fixed_alpha']==args.alpha
    assert offline.get('single_concept',False)==args.single_concept
    assert offline.get('projection_removal',False)==args.projection_removal
    if args.single_concept or args.projection_removal: assert offline['vector']==contrast.tolist()
    if args.projection_removal: assert offline['implementation_sha256']==gap.sha(__file__)
    reference=json.loads(norm.REFERENCE.read_text());assert gap.sha(norm.REFERENCE)==norm.REFERENCE_SHA
    started=time.monotonic()
    snapshot=Path(snapshot_download(gap.MODEL,revision=gap.REVISION));assert snapshot.name==gap.REVISION
    assert gap.sha(snapshot/'config.json')==source['model_config_sha256']
    assert gap.sha(snapshot/'model.safetensors.index.json')==source['model_index_sha256']
    tokenizer=generation_tokenizer(snapshot, source, reference)
    model=AutoModelForCausalLM.from_pretrained(snapshot,dtype=torch.bfloat16).to('cuda').eval()
    data={'schema':'additive_named_gp_v1','source_revision':args.source_revision,'implementation_sha256':gap.sha(__file__),
        'dependencies_sha256':{p:gap.sha(SCRIPTS/'scratch'/p) for p in ('j_lens_norm_matched_gp.py','j_lens_gap_clamp.py')},
        'model_revision':gap.REVISION,'snapshot':str(snapshot),'reference_sha256':norm.REFERENCE_SHA,'named_source_sha256':gap.sha(SOURCE),
        'model_config_sha256':gap.sha(snapshot/'config.json'),'model_index_sha256':gap.sha(snapshot/'model.safetensors.index.json'),
        'projection_removal':args.projection_removal, 'single_concept':args.single_concept, 'contrast':contrast.tolist(),'contrast_norm':float(contrast.norm()),'fixed_alpha':args.alpha,'settings':reference['settings'],
        'argv':sys.argv,'offline_check_sha256':gap.sha(offline_path),
        'records':[],'identity_controls':[],'reused_records':reference['records'],
        'scope':f'{"Single sycophancy GP projection removal (fraction1, minus-only, not norm-matched)" if args.projection_removal else "Norm-matched single sycophancy GP component" if args.single_concept else "Raw named-GP difference"}, persistent layer17, alpha{args.alpha}; no source inference; exploratory reused DEV15, not frontier'}
    norm.save(args.output,data)
    print('ADDITIVE_MODEL',json.dumps({k:data[k] for k in ('model_revision','snapshot','named_source_sha256','contrast_norm','fixed_alpha')}),flush=True)
    print('SHOULD:15treatments+1exactidentity;projection residual and orthogonal preservation within rounding;fixed rubric.' if args.projection_removal else 'SHOULD:30treatments+2exactidentity;nonzero actual signed-additive delivery each cached call;no source fitting;constant vector and fixed rubric.',flush=True)
    rows,_=gap.walk.read_cohort(15)
    for ri,row in enumerate(rows):
        bare=next(r for r in reference['records'] if r['scenario']==row['scenario'] and r['condition']=='bare')
        rendered=gap.walk.generation_inputs(tokenizer,[row])[0]
        encoded=tokenizer(rendered,return_tensors='pt',add_special_tokens=False).to(model.device)
        assert rendered==bare['rendered'] and encoded.input_ids[0].tolist()==bare['input_ids'] and encoded.attention_mask.all()
        for side,sign in ((('-C',1.),) if args.projection_removal else (('+C',1.),('-C',-1.))):
            for alpha in ((0.,args.alpha) if ri==0 else (args.alpha,)):
                ms=[]
                try:
                    with torch.inference_mode(),intervention(model,contrast,sign*alpha,ms,projection_removal=args.projection_removal):
                        output=model.generate(**encoded,do_sample=False,temperature=None,top_p=None,top_k=None,pad_token_id=tokenizer.eos_token_id,max_new_tokens=512,use_cache=True)
                except Exception as e:
                    data['failure']={'scenario':row['scenario'],'side':side,'error':repr(e),'measurements':ms};norm.save(args.output,data);raise
                ids=output[0,encoded.input_ids.shape[1]:].tolist()
                assert len(ms)==len(ids) and all(m['next_block_exact'] for m in ms)
                assert [m['sequence_length'] for m in ms]==[len(bare['input_ids'])]+[1]*(len(ids)-1)
                text=tokenizer.decode(ids,skip_special_tokens=True).strip()
                r={'scenario':row['scenario'],'prompt':row['prompt'],'condition':('projection_removal_' if args.projection_removal else 'single_concept_' if args.single_concept else 'additive_concepts_')+('plus' if side=='+C' else 'minus'),
                    'method':'sycophancy_gp_projection_removal' if args.projection_removal else 'single_sycophancy_gp' if args.single_concept else 'additive_named_gp','side':side,'rendered':rendered,'input_ids':bare['input_ids'],
                    'attention_mask':encoded.attention_mask[0].tolist(),'generated_ids':ids,'text':text,'measurements':ms,'health':gap.walk.health(tokenizer,[text])}
                if not alpha:
                    assert ids==bare['generated_ids'] and all(m['actual_norm']==0 for m in ms)
                    r['identity_exact']=True;data['identity_controls'].append(r)
                else:
                    if args.projection_removal:
                        assert all(m['operator']=='projection_removal' and m['removal_fraction']==1 for m in ms)
                    else:
                        assert all(m['actual_norm']>0 and m['direction_cosine']>.99 for m in ms)
                    data['records'].append(r)
                norm.save(args.output,data)
                print('ADDITIVE_RESPONSE',json.dumps({k:v for k,v in r.items() if k not in ('input_ids','attention_mask','generated_ids','measurements')}),flush=True)
    data['runtime']={'seconds':time.monotonic()-started,'gpu':torch.cuda.get_device_name(),'peak_memory_bytes':torch.cuda.max_memory_allocated(),'torch':torch.__version__}
    assert len(data['records'])==(15 if args.projection_removal else 30) and len(data['identity_controls'])==(1 if args.projection_removal else 2)
    norm.save(args.output,data);print('ADDITIVE_COMPLETE',json.dumps(data['runtime']),flush=True)


def report(folder):
    import export
    data=json.loads((folder/'generation.json').read_text());js=[json.loads(l) for l in (folder/'judgments.jsonl').read_text().splitlines()]
    assert gap.sha(SOURCE)==data['named_source_sha256'] and gap.sha(norm.REFERENCE)==data['reference_sha256']
    assert data['reused_records']==json.loads(norm.REFERENCE.read_text())['records']
    executed=subprocess.check_output(['git','show',data['source_revision']+':scripts/scratch/j_lens_additive_concepts.py'])
    assert hashlib.sha256(executed).hexdigest()==data['implementation_sha256']
    assert len(js)==60 and len({(j['vignette'],j['condition'],j['order']) for j in js})==60
    assert len(data['records'])==30 and len({(r['scenario'],r['side']) for r in data['records']})==30
    assert len(data['identity_controls'])==2 and all(r['identity_exact'] for r in data['identity_controls'])
    scores=[];pairs=[];steps=[];lines=['# '+('Single sycophancy GP' if data.get('single_concept') else 'Additive named GP')+': complete responses and unchanged per-response scores']
    for r in [b for b in data['reused_records'] if b['condition']=='bare']+data['records']:
        lines+=['## '+r['scenario']+' / '+r['condition'],'```text',r['rendered'],'```','> '+r['text'],'Health: '+json.dumps(r['health'])]
        found={j['order']:j for j in js if j['vignette']==r['scenario'] and j['condition']==r['condition']}
        assert len(found)==(0 if r['condition']=='bare' else 2)
        for order,j in sorted(found.items()):
            assert abs(j['exported_effect']-export.signed_axis_effect(j['side'],[export.score_cell(j)]))<1e-9
            b,t=('A','B') if order=='AB' else ('B','A');s=j['judgment']
            score={'scenario':r['scenario'],'side':r['side'],'order':order,'effect':j['exported_effect'],'bare_on':s['on_axis_'+b],
                'steered_on':s['on_axis_'+t],'bare_off':s['off_axis_'+b],'steered_off':s['off_axis_'+t],'evidence':s['evidence']}
            scores.append(score);lines.append(json.dumps(score,ensure_ascii=False))
        if found:
            a,b=(found[o]['exported_effect'] for o in ('AB','BA'))
            pairs.append({'scenario':r['scenario'],'side':r['side'],'AB':a,'BA':b,'mean':(a+b)/2,'strict_reversal':a*b<0,'tie_disagreement':(a==0)!=(b==0)})
    for r in data['records']+data['identity_controls']:
        ms=r['measurements'];identity=r.get('identity_exact',False)
        assert len(ms)==len(r['generated_ids']) and [m['sequence_length'] for m in ms]==[len(r['input_ids'])]+[1]*(len(ms)-1)
        for m in ms:
            assert m['nonfinal_exact'] and m['next_block_exact'] and m['rounding_error_norm']<=m['rounding_bound']
            if identity:assert m['actual_norm']==0
            else:assert m['actual_norm']>0 and m['direction_cosine']>.99 and m['signed_alpha']==data['fixed_alpha']*(1 if r['side']=='+C' else -1)
            steps.append({'scenario':r['scenario'],'side':r['side'],'identity':identity,**m})
    for name,rows in (('scores.csv',scores),('paired.csv',pairs),('steps.csv',steps)):
        with (folder/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (folder/'responses-and-scores.md').write_text('\n\n'.join(lines)+'\n')
    summary={'runtime':data['runtime'],'judge_cost_usd':sum(j['cost_usd'] for j in js),'fixed_alpha':data['fixed_alpha'],'contrast_norm':data['contrast_norm'],'groups':{}}
    for side in ('+C','-C'):
        ss=[s for s in scores if s['side']==side];ps=[p for p in pairs if p['side']==side];ms=[m for m in steps if m['side']==side and not m['identity']]
        summary['groups'][side]={o+'_mean':statistics.mean(s['effect'] for s in ss if s['order']==o) for o in ('AB','BA')}
        summary['groups'][side].update({'paired_mean':statistics.mean(p['mean'] for p in ps),'off_mean':statistics.mean(s['steered_off'] for s in ss),
            'strict_reversals':sum(p['strict_reversal'] for p in ps),'tie_disagreements':sum(p['tie_disagreement'] for p in ps),'calls':len(ms),
            'norm_min':min(m['actual_norm'] for m in ms),'norm_median':statistics.median(m['actual_norm'] for m in ms),'norm_max':max(m['actual_norm'] for m in ms),
            'max_absolute_norm_error':max(m['norm_error'] for m in ms),'min_direction_cosine':min(m['direction_cosine'] for m in ms)})
    norm.save(folder/'summary.json',summary);print('ADDITIVE_REPORT_PASS',json.dumps(summary),flush=True)


def generation_report(folder):
    """Offline, generation-only comparison; never calls a judge or invents scores."""
    data=json.loads((folder/'generation.json').read_text())
    earlier=json.loads((ROOT/'generation.json').read_text())
    reference=json.loads(norm.REFERENCE.read_text())
    assert data['fixed_alpha'] in (2,4) and earlier['fixed_alpha']==1
    previous=json.loads((dose_root(2)/'generation.json').read_text()) if data['fixed_alpha']==4 else None
    if previous:
        for key in ('named_source_sha256','reference_sha256','model_revision','settings','contrast'):
            assert previous[key]==data[key]
        assert previous['fixed_alpha']==2
    assert gap.sha(SOURCE)==SOURCE_SHA==data['named_source_sha256']==earlier['named_source_sha256']
    assert gap.sha(norm.REFERENCE)==norm.REFERENCE_SHA==data['reference_sha256']==earlier['reference_sha256']
    assert data['reused_records']==earlier['reused_records']==reference['records']
    for key in ('model_revision','model_config_sha256','model_index_sha256','settings','contrast','contrast_norm'):
        assert data[key]==earlier[key], key
    executed=subprocess.check_output(['git','show',data['source_revision']+':scripts/scratch/j_lens_additive_concepts.py'])
    assert hashlib.sha256(executed).hexdigest()==data['implementation_sha256']
    assert gap.sha(folder/'offline-bf16.json')==data['offline_check_sha256']
    for name,expected in data['dependencies_sha256'].items():
        assert gap.sha(SCRIPTS/'scratch'/name)==expected
    assert len(data['records'])==30 and len(data['identity_controls'])==2
    assert len({(r['scenario'],r['side']) for r in data['records']})==30
    wanted=data['fixed_alpha']*float(torch.tensor(data['contrast'],dtype=torch.float32).norm())
    steps=[];pairs=[];lines=['# Complete baseline / alpha1 / '+('alpha2 / ' if previous else '')+f"alpha{data['fixed_alpha']} response comparison",
        'Generation-only: no judge calls or scores. Exact prompts, IDs and all per-step records: generation.json.']
    for r in data['records']+data['identity_controls']:
        bare=next(b for b in reference['records'] if b['scenario']==r['scenario'] and b['condition']=='bare')
        one=next(b for b in earlier['records'] if (b['scenario'],b['side'])==(r['scenario'],r['side']))
        for key in ('input_ids','rendered','prompt'):
            assert r[key]==bare[key]==one[key]
        assert all(r['attention_mask'])
        identity=r.get('identity_exact',False)
        ms=r['measurements']
        assert len(ms)==len(r['generated_ids'])
        assert [m['sequence_length'] for m in ms]==[len(r['input_ids'])]+[1]*(len(ms)-1)
        for m in ms:
            assert m['nonfinal_exact'] and m['next_block_exact']
            assert m['position']==m['sequence_length']-1
            assert m['rounding_error_norm']<=m['rounding_bound']
            if identity:
                assert m['actual_norm']==0 and m['signed_alpha']==0 and m['desired_norm']==0
            else:
                assert m['signed_alpha']==data['fixed_alpha']*(1 if r['side']=='+C' else -1)
                assert abs(m['desired_norm']-wanted)<1e-6 and m['actual_norm']>0 and m['direction_cosine']>.99
                assert abs(m['norm_error']-abs(m['actual_norm']-wanted))<1e-6
            steps.append({'scenario':r['scenario'],'side':r['side'],'identity':identity,**m})
        if identity:
            assert r['generated_ids']==bare['generated_ids'] and r['text']==bare['text']
            continue
        pair={'scenario':r['scenario'],'side':r['side'],'baseline_text_equal':r['text']==bare['text'],
            'baseline_ids_equal':r['generated_ids']==bare['generated_ids'],'alpha1_text_equal':r['text']==one['text'],
            'alpha1_ids_equal':r['generated_ids']==one['generated_ids'],'tokens':len(r['generated_ids']),**r['health'][0]}
        variants=[('Baseline',bare),('Alpha1',one)]
        if previous:
            two=next(b for b in previous['records'] if (b['scenario'],b['side'])==(r['scenario'],r['side']))
            assert all(two[k]==r[k] for k in ('input_ids','rendered','prompt'))
            pair.update(alpha2_text_equal=r['text']==two['text'],alpha2_ids_equal=r['generated_ids']==two['generated_ids'])
            variants.append(('Alpha2',two))
        variants.append((f"Alpha{data['fixed_alpha']}",r))
        pairs.append(pair)
        lines+=['## '+r['scenario']+' / '+r['side'],'```text\n'+r['rendered']+'\n```']
        for label,record in variants:
            lines+=['### '+label,record['text'],'Health: '+json.dumps(record['health'])]
        lines.append('Equality and length: '+json.dumps(pair))
    for name,rows in (('steps.csv',steps),('comparisons.csv',pairs)):
        with (folder/name).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    (folder/'responses-comparison.md').write_text('\n\n'.join(lines)+'\n')
    summary={'runtime':data['runtime'],'source_revision':data['source_revision'],'fixed_alpha':data['fixed_alpha'],'requested_norm':wanted,
        'generation_sha256':gap.sha(folder/'generation.json'),'alpha1_sha256':gap.sha(ROOT/'generation.json'),
        'identity_calls':sum(m['identity'] for m in steps),'treatment_calls':sum(not m['identity'] for m in steps),
        'API_calls':0,'groups':{}}
    if previous:summary['alpha2_sha256']=gap.sha(dose_root(2)/'generation.json')
    for side in ('+C','-C'):
        ms=[m for m in steps if m['side']==side and not m['identity']];ps=[p for p in pairs if p['side']==side]
        summary['groups'][side]={'calls':len(ms),'nonzero_calls':sum(m['actual_norm']>0 for m in ms),
            'norm_min':min(m['actual_norm'] for m in ms),'norm_median':statistics.median(m['actual_norm'] for m in ms),
            'norm_max':max(m['actual_norm'] for m in ms),'max_absolute_norm_error':max(m['norm_error'] for m in ms),
            'max_relative_norm_error':max(m['norm_error']/wanted for m in ms),'min_direction_cosine':min(m['direction_cosine'] for m in ms),
            'health':{k:sum(p[k] for p in ps) for k in ('unfinished','role_leaks','repeated')},
            'max_tokens':max(p['tokens'] for p in ps),'mean_words':statistics.mean(p['mean_words'] for p in ps),
            'baseline_text_equal':sum(p['baseline_text_equal'] for p in ps),'alpha1_text_equal':sum(p['alpha1_text_equal'] for p in ps)}
        if previous:summary['groups'][side]['alpha2_text_equal']=sum(p['alpha2_text_equal'] for p in ps)
    norm.save(folder/'summary.json',summary)
    print('ADDITIVE_GENERATION_REPORT_PASS',json.dumps(summary),flush=True)


if __name__!='__main__':
    import modal
    from run_modal import image,cache,source_revision
    image=image.add_local_file(str(norm.REFERENCE),'/repo/'+str(norm.REFERENCE)).add_local_file(str(SOURCE),'/repo/'+str(SOURCE))
    for alpha,single,projection in ((1,False,False),(2,False,False),(4,False,False),(4,True,False),(1,False,True)):
        check=dose_root(alpha,single,projection)/'offline-bf16.json'
        if check.exists():image=image.add_local_file(str(check),'/repo/'+str(check))
    app=modal.App('jsteer-additive-named-concepts',image=image)
    @app.function(gpu='H100',volumes={'/cache':cache},timeout=360,max_containers=1,retries=0)
    def remote(revision:str,alpha:int=1,single_concept:bool=False,projection_removal:bool=False):
        destination='outputs/audits/'+dose_root(alpha,single_concept,projection_removal).name+'/generation.json'
        try:subprocess.run([sys.executable,'scripts/scratch/j_lens_additive_concepts.py','--alpha',str(alpha),'--output','/cache/'+destination,'--source-revision',revision]+(['--single-concept'] if single_concept else [])+(['--projection-removal'] if projection_removal else []),cwd='/repo',check=True)
        finally:
            print('ADDITIVE_VOLUME_COMMIT_START',flush=True);cache.commit();print('ADDITIVE_VOLUME_COMMIT_END',flush=True)
        return destination
    @app.local_entrypoint()
    def launch(alpha:int=1,single_concept:bool=False,projection_removal:bool=False):
        assert (dose_root(alpha,single_concept,projection_removal)/'offline-bf16.json').exists()
        print('ADDITIVE_REMOTE_PATH',remote.remote(source_revision(),alpha,single_concept,projection_removal),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');p.add_argument('--judge',type=Path);p.add_argument('--report',type=Path)
    p.add_argument('--generation-report',type=Path)
    p.add_argument('--single-concept',action='store_true')
    p.add_argument('--projection-removal',action='store_true')
    p.add_argument('--alpha',type=int,choices=(1,2,4),default=1)
    p.add_argument('--output',type=Path);p.add_argument('--source-revision',default='unknown');args=p.parse_args()
    args.output=args.output or dose_root(args.alpha,args.single_concept,args.projection_removal)/'generation.json'
    if args.self_test:
        assert not args.projection_removal, 'Run slop/logs/20260907_j_lens_projection_removal/precheck.py for the offline projection check'
        self_test(args.alpha,args.single_concept)
    elif args.judge:asyncio.run(norm.judge_run(args))
    elif args.report:report(args.report)
    elif args.generation_report:generation_report(args.generation_report)
    else:run(args)
