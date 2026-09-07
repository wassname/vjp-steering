"""Offline reviewer-claim check; no model execution or recalibration. PI/OpenAI Codex."""
import json
from pathlib import Path
import sys
sys.path[:0]=['src','scripts','scripts/scratch']
import torch
import j_lens_dev15_representation as bridge
root=Path('slop/logs/20260907_j_lens_norm_matched_gp')
data=json.loads((root/'generation.json').read_text())
vectors,_,targets,_=bridge.sources(Path('outputs/experiments'))
b=vectors['j_gp16']['+C'].shared[17]['basis'].double()
f=vectors['full_residual']['+C'].shared[17]['basis'].double()
d=torch.linalg.solve(b@b.T,b)
unitcos=float(torch.nn.functional.cosine_similarity((b[0]-b[1])[None],(f[0]-f[1])[None]))
records=[];max_error=0.;max_sum_error=0.
for r in data['records']:
 for m in r['measurements']:
  c=torch.tensor(m['gp_coordinates_before'],dtype=torch.float64);t=m['gp_target']
  symmetric=.5*(t-c[0]+c[1])*(b[0]-b[1])
  desired=torch.stack((c.mean()+t/2,c.mean()-t/2))
  midpoint=(desired-c)@b
  max_error=max(max_error,float((symmetric-midpoint).abs().max()))
  max_sum_error=max(max_sum_error,float((symmetric@d.T).sum().abs()))
  fc=m['full_coordinates_before'];fg=m['full_target']-fc[0]+fc[1];gg=t-float(c[0])+float(c[1])
  records.append({'scenario':r['scenario'],'side':r['side'],'call':m['call'],'nominal_gp_full_cosine':unitcos*(1 if fg*gg>0 else -1),'gp_signed_gap':gg,'full_signed_gap':fg})
summary={'basis_difference_cosine':unitcos,'gp_midpoint_vs_symmetric_max_error':max_error,'gp_coordinate_sum_delta_max':max_sum_error,'calls':len(records),'sign_opposition_count':sum(r['nominal_gp_full_cosine']<0 for r in records),'nominal_cosine_min':min(r['nominal_gp_full_cosine'] for r in records),'nominal_cosine_max':max(r['nominal_gp_full_cosine'] for r in records),'caveat':'Nominal GP/full direction comparison,not exact BF16fullreferencecosine;full h arrays were not saved. No downstream causal interpretation.'}
(root/'science-update/geometry.json').write_text(json.dumps({'summary':summary,'records':records},indent=2)+'\n')
print('GEOMETRY_CHECK_PASS',json.dumps(summary))
