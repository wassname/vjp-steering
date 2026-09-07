"""Offline audit of recovered frozen-target generations; no model/judge call. PI/OpenAI Codex."""
import json,sys,hashlib,subprocess
from pathlib import Path
import torch
sys.path[:0]=['src','scripts','scripts/scratch']
import j_lens_dev15_representation as bridge
root=bridge.ROOT
path=root/'generation.json'
data=json.loads(path.read_text())
vectors,metadata,targets,provenance=bridge.sources(Path('outputs/experiments'))
assert data['source_revision']=='3a1b921'+data['source_revision'][7:]
source=subprocess.check_output(['git','show',data['source_revision']+':scripts/scratch/j_lens_dev15_representation.py'])
assert hashlib.sha256(source).hexdigest()==data['implementation_sha256']
for key in provenance:
    if key != 'checks':assert data['provenance'][key]==provenance[key], key
for name in targets:
    assert data['targets'][name]==targets[name]
rows,_=bridge.gap.walk.read_cohort(15)
conditions=['bare','full_residual_plus','full_residual_minus','j_gp16_plus','j_gp16_minus']
expected={(r['scenario'],c) for r in rows for c in conditions}
assert {(r['scenario'],r['condition']) for r in data['records']}==expected and len(data['records'])==75
logged=[json.loads(l.split(' ',1)[1]) for l in (root/'modal-retry.log').read_text().splitlines() if l.startswith('DEV15_RESPONSE ')]
assert len(logged)==75
for r,l in zip(data['records'],logged):
    assert r['scenario']==l['scenario'] and r['condition']==l['condition'] and r['text']==l['text']
fm=metadata['full_residual']
masks=[]
for ci,condition in enumerate(('positive','negative','baseline')):
    for i in range(52,65):
        ordinal=ci*65+i;tr=fm['token_records'][ordinal];length=len(tr['input_ids']);att=tr['attention_mask'];valid=sum(att)
        assert len(att)==length and att==[1]*valid+[0]*(length-valid)
        assert tr['final_position']==valid-1 and all(t==248044 for t,a in zip(tr['input_ids'],att) if not a)
        masks.append({'condition':condition,'source_id':fm['source_ids'][i],'source_index':i,'flattened_ordinal':ordinal,
            'original_batch_start':ordinal//8*8,'original_batch_shape':[min(8,len(fm['token_records'])-ordinal//8*8),length],
            'replay_shape':[1,length],'input_ids':tr['input_ids'],'attention_mask':att,'attended_length':valid,'padding_length':length-valid,
            'pad_token_id':248044,'padding_side':'right','final_position':tr['final_position']})
(root/'replay-masks.json').write_text(json.dumps(masks,indent=2)+'\n')
def stats(values):
    if not values:return {'count':0}
    v=torch.tensor(values,dtype=torch.float64)
    return {'count':len(values),'min':float(v.min()),'q25':float(v.quantile(.25)),'median':float(v.median()),'q75':float(v.quantile(.75)),'q95':float(v.quantile(.95)),'max':float(v.max())}
summary=[];steps=[]
for name in ('full_residual','j_gp16'):
    for side,condition in (('+C','positive'),('-C','negative')):
        entry=data['metrology']['holdout'][name+'_'+condition]
        frozen=targets[name][side];replayed=entry['replayed_mean'][0]-entry['replayed_mean'][1];shift=replayed-frozen
        b=vectors[name][side].shared[17]['basis'].double();factor=float((b[0]-b[1]).norm()/2);delta_norm=abs(shift)*factor
        group=[]
        for r in data['records']:
            if r['method']!=name or r['side']!=side:continue
            measures=r['measurements'];assert len(measures)==len(r['generated_ids'])
            assert [m['sequence_length'] for m in measures]==[len(r['input_ids'])]+[1]*(len(measures)-1)
            for index,m in enumerate(measures):
                numeric=[*m['coordinates_before'],*m['coordinates_after'],m['target_gap'],m['target_gap_error'],*m['all_position_patch_norms']]
                assert all(torch.isfinite(torch.tensor(numeric))) and m['next_block_input_exact']
                assert len(m['all_position_patch_norms'])==m['sequence_length'] and not any(m['all_position_patch_norms'][:-1])
                assert m['target_gap']==frozen and m['target_gap_error']<.05
                current=m['coordinates_before'][0]-m['coordinates_before'][1]
                old=frozen-current;new=replayed-current;norm=m['all_position_patch_norms'][-1]
                sign_change=old*new<0
                record={'scenario':r['scenario'],'method':name,'side':side,'call':index,'current_gap':current,
                    'frozen_target':frozen,'replay_target':replayed,'frozen_signed_shift':old,'replay_signed_shift':new,
                    'strict_sign_change':sign_change,'either_shift_zero':old==0 or new==0,
                    'actual_frozen_patch_norm':norm,'analytic_frozen_patch_norm':abs(old)*factor,'analytic_replay_patch_norm':abs(new)*factor,
                    'absolute_update_vector_difference_norm':delta_norm,'absolute_patch_magnitude_difference':abs(abs(new)-abs(old))*factor,
                    'relative_update_difference_to_actual':delta_norm/norm if norm else None,
                    'relative_magnitude_difference_to_actual':abs(abs(new)-abs(old))*factor/norm if norm else None,
                    'actual_patch_no_larger_than_target_shift':norm<=delta_norm}
                group.append(record);steps.append(record)
        flips=[s for s in group if s['strict_sign_change']]
        summary.append({'method':name,'side':side,'saved_target':frozen,'replay_mean_target':replayed,'target_shift':shift,
            'absolute_target_shift':abs(shift),'relative_target_shift':abs(shift/frozen),'max_coordinate_error_separate':entry['coordinate_max_error'],
            'basis_difference_half_norm':factor,'update_vector_difference_norm':delta_norm,'calls':len(group),'strict_sign_changes':len(flips),
            'zero_actual_updates':sum(s['actual_frozen_patch_norm']==0 for s in group),
            'zero_signed_shifts':sum(s['either_shift_zero'] for s in group),
            'near_zero_defined_as_actual_update_le_target_shift_norm':sum(s['actual_patch_no_larger_than_target_shift'] for s in group),
            'actual_updates_all':stats([s['actual_frozen_patch_norm'] for s in group]),
            'actual_updates_flip_subset':stats([s['actual_frozen_patch_norm'] for s in flips]),
            'relative_update_difference_nonzero':stats([s['relative_update_difference_to_actual'] for s in group if s['relative_update_difference_to_actual'] is not None]),
            'relative_update_difference_flip_nonzero':stats([s['relative_update_difference_to_actual'] for s in flips if s['relative_update_difference_to_actual'] is not None]),
            'absolute_magnitude_difference_all':stats([s['absolute_patch_magnitude_difference'] for s in group]),
            'relative_magnitude_difference_nonzero':stats([s['relative_magnitude_difference_to_actual'] for s in group if s['relative_magnitude_difference_to_actual'] is not None])})
assert len(steps)==3937
(root/'target-impact-steps.json').write_text(json.dumps(steps)+'\n')
result={'generation_sha256':bridge.gap.sha(path),'source_revision':data['source_revision'],'implementation_sha256':data['implementation_sha256'],
    'records':75,'response_log_matches':75,'missing_cells':[],'treated_steps':len(steps),'mask_records':39,
    'identities':data['identity_controls'],'groups':summary,'runtime':data['runtime']}
(root/'target-impact.json').write_text(json.dumps(result,indent=2)+'\n')
print('RECOVERY_IMPACT_PASS',json.dumps(result),flush=True)
