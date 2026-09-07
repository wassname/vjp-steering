"""Source-only BF16 delivery, no model/API call. PI/OpenAI Codex."""
import hashlib
import json
from pathlib import Path
import statistics
import torch

p=Path('slop/logs/20260907_j_lens_named_concepts/generation.json')
d=json.loads(p.read_text());c=d['construction']
assert c['inventory']['positive']=='sycophancy' and c['inventory']['negative']=='skepticism'
v=torch.tensor(c['components']['positive']['component'])-torch.tensor(c['components']['negative']['component'])
h=torch.tensor(c['source_states']).bfloat16()
assert h.shape[0]==102 and d['model_revision']=='851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a'
out={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'fixed_alpha':1,'raw_contrast_norm':v.norm().item(),'scope':'102 saved actual named source states only, not DEV state parity','sides':{}}
for side,sign in [('+C',1),('-C',-1)]:
    actual=(h+(sign*v).to(h)).float()-h.float()
    norms=actual.norm(dim=1);error=(norms-v.norm()).abs()
    assert (norms>0).all()
    out['sides'][side]={'source_states':len(h),'nonzero_updates':int((norms>0).sum()),'zero_updates':int((norms==0).sum()),'requested_norm':v.norm().item(),'realized_min':norms.min().item(),'realized_median':statistics.median(norms.tolist()),'realized_max':norms.max().item(),'absolute_error_max':error.max().item(),'relative_error_max':(error/v.norm()).max().item()}
Path('slop/logs/20260907_j_lens_additive_concepts/offline-source-only.json').write_text(json.dumps(out,indent=2)+'\n')
print('SOURCE_ONLY_BF16_PASS',json.dumps(out))
