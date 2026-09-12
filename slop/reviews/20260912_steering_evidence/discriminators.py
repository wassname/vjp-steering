# PI/OpenAI gpt-6-astra: exact inline discriminator source executed on 2026-09-12.
# From repo root: CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=scripts:src .venv/bin/python slop/reviews/20260912_steering_evidence/discriminators.py

import torch
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import experiment
import vjp_steering.vjp as v

class Enc(dict):
    def to(self,device): return Enc({k:x.to(device) for k,x in self.items()})
class Tok:
    def __call__(self,prompts,**kw):
        ids=torch.tensor([[int(p)]*4 for p in prompts]); return Enc(input_ids=ids,attention_mask=torch.ones_like(ids))
class Square(torch.nn.Module):
    def forward(self,x): return x*x
class Model(torch.nn.Module):
    def __init__(self,square=True):
        super().__init__(); self.emb=torch.nn.Embedding(4,2)
        with torch.no_grad(): self.emb.weight.copy_(torch.tensor([[0.,0.],[1.,2.],[2.,1.],[3.,3.]]))
        self.model=torch.nn.Module(); self.model.layers=torch.nn.ModuleList([torch.nn.Identity(),Square() if square else torch.nn.Identity()])
    def forward(self,input_ids,attention_mask):
        h=self.emb(input_ids)
        for layer in self.model.layers: h=layer(h)
        return h
m=Model(); kw=dict(target_layer=1,batch_size=1,max_length=4,skip_first=0)
a=v.vjp_delta(m,Tok(),["2"],["1"],(0,),**kw).stacked[0]["v"]
b=v.vjp_delta(m,Tok(),["1"],["2"],(0,),**kw).stacked[0]["v"]
print("vjp_label_swap", a.tolist(),b.tolist(),"equal",torch.equal(a,b))
assert torch.equal(a,b)
c=v.vjp_delta(Model(False),Tok(),["2"],["1"],(0,),**kw).stacked[0]["v"]
print("constant_jacobian_vjp",c.tolist(),"finite",bool(torch.isfinite(c).all()))
assert not torch.isfinite(c).all()
for method in ("mean_diff","vjp_delta","random","j_lens_injection"):
    args=SimpleNamespace(method=method,model="same-model",dtype="float32",layers="999",target_layer=999,n_pairs=1,seed=999,lens_file=Path("/nonexistent"),injection_plus_concept="other",injection_minus_concept="other")
    experiment.validate_extraction_identity(args,{"method":method,"model":"same-model","dtype":"float32","source_layers":[0],"target_layer":1,"n_pairs":200})
    print("cache_validator_accepts_changed_extraction_args",method)
for method,fn in (("j_lens_swap","j_lens_swap"),("j_lens_unit_direction","j_lens_unit_direction"),("j_lens_injection","j_lens_injection")):
    args=SimpleNamespace(method=method,layers="16",lens_file=Path("/chosen.pt"),injection_plus_concept="",injection_minus_concept="")
    def fake(*a,**kwargs): raise RuntimeError(str(kwargs))
    module=experiment if method=="j_lens_swap" else v
    with patch.object(experiment.walk,"resolve_layers",return_value=tuple(range(25))),patch.object(module,fn,side_effect=fake):
        try: experiment.extract_vectors(args,None,None)
        except RuntimeError as e:
            print("dispatch_kwargs",method,str(e)); assert "lens_file" not in str(e)
args=SimpleNamespace(method="vjp_mlp_up_shared_eb",layers="3",target_layer=5,extract_batch_size=1,max_length=384)
with patch.object(experiment,"extraction_prompts",return_value=(["p"],["n"])),patch.dict(experiment.EXTRACTORS,{args.method:lambda *a,**kw: (_ for _ in ()).throw(RuntimeError(str(kw)))}):
    try: experiment.extract_vectors(args,None,None)
    except RuntimeError as e: print("mlp_dispatch_kwargs",str(e)); assert "target_layer" not in str(e)
print("PASS discriminators reproduced production-path defects without models/downloads")
