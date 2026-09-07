"""Offline projection removal: independent FP64 oracle and shared-runner route checks."""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import statistics
import sys
import tempfile
from unittest.mock import patch

import torch
sys.path.insert(0, str(Path('scripts/scratch').resolve()))
import j_lens_additive_concepts as runner

ROOT = runner.PROJECTION_ROOT

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    torch.set_num_threads(1)
    protected = [Path('data/results.csv'), *Path('results').glob('index.*'), *Path('results').glob('plot*.png')]
    manifest_path = Path('slop/logs/20260907_j_lens_judged_display/manifest.json')
    for artifact in json.loads(manifest_path.read_text())['artifacts']:
        protected += [Path(artifact['generation']), Path(artifact['judgments'])]
    before = {str(p): sha(p) for p in set(protected)}
    source, direction = runner.source_contrast(True)
    positive = source['construction']['components']['positive']
    weights = torch.tensor(positive['weights'], dtype=torch.float64)
    dictionary = torch.tensor(positive['dictionary_rows'], dtype=torch.float64)
    if len(weights) != len(dictionary):
        weights = weights[positive['nonzero_ids']]
    reproduced = weights @ dictionary
    component = torch.tensor(positive['component'], dtype=torch.float64)
    torch.testing.assert_close(reproduced, component, atol=1e-5, rtol=1e-4)
    # Normalize the exact saved FP32 single-concept direction in FP64, independently of patch arithmetic.
    unit = direction.double() / direction.double().norm()
    torch.testing.assert_close(unit, component/component.norm(), atol=1e-7, rtol=1e-5)
    transfer = json.loads(runner.STATES.read_text())
    reference = json.loads(runner.norm.REFERENCE.read_text())
    assert transfer['model_revision'] == source['model_revision'] == runner.gap.REVISION
    assert sha(runner.norm.REFERENCE) == runner.norm.REFERENCE_SHA
    bare = [r for r in transfer['records'] if r['condition'] == 'bare']
    assert len(bare) == 3
    states = [('source', str(i), torch.tensor(h, dtype=torch.float64)) for i, h in enumerate(source['construction']['source_states'])]
    assert len(states) == 102
    expected = dict(zip(('syco_bullshit_v2_leg_pnf_01', 'syco_bullshit_v2_sw_pnf_02', 'syco_bullshit_v2_sw_pnf_03'), (.241139, .288525, .064328)))
    coordinates = {}
    for r in bare:
        baseline = next(b for b in reference['records'] if b['condition']=='bare' and b['scenario']==r['scenario'])
        assert r['input_ids'] == baseline['input_ids']
        h = torch.tensor(r['final_states']['17'], dtype=torch.float64)
        coordinates[r['scenario']] = float(h @ unit)
        assert abs(coordinates[r['scenario']] - expected[r['scenario']]) < 1e-6
        states.append(('bare_prefill', r['scenario'], h))
    rows = []
    for group, name, saved in states:
        h = saved.to(torch.bfloat16)
        torch.testing.assert_close(h.double(), saved, atol=0, rtol=0)
        hd = h.double()
        ideal = hd - unit*(hd @ unit)
        second = ideal - unit*(ideal @ unit)
        torch.testing.assert_close(second, ideal, atol=1e-12, rtol=0)
        assert abs(float(ideal @ unit)) < 1e-12
        for fraction in (0., 1.):
            after, metrics = runner.intervention_patch(h[None], direction, fraction, projection_removal=True)
            actual = after[0].double()-hd
            requested = -fraction * unit*(hd @ unit)
            error = actual-requested
            residual = after[0].double() @ unit
            orthogonal = actual-unit*(actual @ unit)
            # Independent, elementwise bound for one final BF16 rounding and FP32 projection arithmetic.
            coordinate_error = 8*torch.finfo(torch.float32).eps*(hd.abs() @ unit.abs())
            rounding_bound = (torch.finfo(torch.bfloat16).eps*(hd+requested).abs() + coordinate_error*unit.abs()).norm()
            assert error.norm() <= rounding_bound
            assert abs(residual-(1-fraction)*(hd @ unit)) <= error.norm()+1e-12
            assert orthogonal.norm() <= error.norm()+1e-12
            if fraction == 0:
                assert torch.equal(after[0], h) and actual.norm() == 0
            else:
                assert actual.norm() > 0
            rows.append({'group':group, 'state':name, 'fraction':fraction, 'fp64_coordinate_before':float(hd@unit),
                'fp64_requested_norm':float(requested.norm()), 'fp64_actual_norm':float(actual.norm()),
                'fp64_residual_coordinate':float(residual), 'fp64_orthogonal_change_norm':float(orthogonal.norm()),
                'fp64_error_norm':float(error.norm()), 'independent_rounding_bound':float(rounding_bound), **metrics})
    # Projection removal is invariant to direction sign, unlike negative addition.
    test_h = states[0][2].to(torch.bfloat16)[None]
    assert torch.equal(runner.projection_patch(test_h,direction,1)[0],runner.projection_patch(test_h,-direction,1)[0])
    try:
        runner.projection_patch(test_h,direction,-1)
        raise RuntimeError('negative removal fraction was accepted')
    except AssertionError:
        pass
    from transformers import Qwen3_5TextConfig, Qwen3_5ForCausalLM
    config = Qwen3_5TextConfig(vocab_size=64,hidden_size=32,intermediate_size=64,num_hidden_layers=3,
        num_attention_heads=2,num_key_value_heads=1,head_dim=16,layer_types=['linear_attention','full_attention','linear_attention'],
        linear_num_key_heads=2,linear_num_value_heads=2,linear_key_head_dim=8,linear_value_head_dim=8,pad_token_id=0,eos_token_id=63)
    torch.manual_seed(17)
    model = Qwen3_5ForCausalLM(config).eval()
    inputs = {'input_ids':torch.tensor([[1,2,3,4]]),'attention_mask':torch.ones(1,4,dtype=torch.long)}
    v = direction[:32].clone()
    def generate():
        return model.generate(**inputs,max_new_tokens=4,do_sample=False,use_cache=True)
    calls = []
    with torch.inference_mode():
        baseline = generate()
        for fraction in (0., 1.):
            ms = []
            with patch.object(runner, 'additive_patch', side_effect=RuntimeError('wrong additive route')):
                with runner.intervention(model,v,fraction,ms,layer=1,projection_removal=True):
                    out = generate()
            assert len(ms)==out.shape[1]-4
            assert [m['sequence_length'] for m in ms] == [4]+[1]*(len(ms)-1)
            assert all(m['operator']=='projection_removal' and m['removal_fraction']==fraction and m['next_block_exact'] and m['nonfinal_exact'] for m in ms)
            if fraction == 0:
                assert torch.equal(out, baseline)
            calls += ms
        assert torch.equal(generate(),baseline)
        try:
            with runner.intervention(model,v,1.,[],layer=1,projection_removal=True):
                raise RuntimeError('cleanup probe')
        except RuntimeError:
            pass
        assert not model.model.layers[1]._forward_hooks and not model.model.layers[2]._forward_pre_hooks
    active = [r for r in rows if r['fraction']==1]
    result = {'source_sha256':sha(runner.SOURCE), 'transfer_sha256':sha(runner.STATES), 'reference_sha256':sha(runner.norm.REFERENCE),
        'implementation_sha256':sha(runner.__file__), 'model_revision':runner.gap.REVISION,
        'fixed_alpha':1, 'projection_removal':True, 'single_concept':False, 'vector':direction.tolist(), 'unit_direction_fp64':unit.tolist(),
        'source_states':102, 'bare_states':3, 'cases':len(rows), 'zero_updates':sum(r['actual_norm']==0 for r in active),
        'bare_coordinates':coordinates, 'real_hybrid_calls':calls, 'rows':rows,
        'summary':{'requested_min':min(r['fp64_requested_norm'] for r in active), 'requested_median':statistics.median(r['fp64_requested_norm'] for r in active), 'requested_max':max(r['fp64_requested_norm'] for r in active),
            'actual_min':min(r['actual_norm'] for r in active), 'actual_median':statistics.median(r['actual_norm'] for r in active), 'actual_max':max(r['actual_norm'] for r in active),
            'max_abs_residual':max(abs(r['fp64_residual_coordinate']) for r in active), 'max_orthogonal_change':max(r['fp64_orthogonal_change_norm'] for r in active),
            'nonzero_residuals':sum(r['fp64_residual_coordinate']!=0 for r in active)},
        'scope':'102 source and three bare final-prefill states only; no DEV decode trajectories or paid calls; ideal idempotence, not BF16 exact zero.'}
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/'offline-bf16.json').write_text(json.dumps(result,indent=2)+'\n')
    route_test(source, reference, direction)
    assert all(sha(p)==h for p,h in before.items())
    # Run all existing additive CPU variants, redirecting artifact writes to temporary directories.
    regression_output = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp, redirect_stdout(regression_output):
        with patch.object(runner, 'dose_root', side_effect=lambda a,s=False:Path(tmp)/f'{a}-{s}'):
            for alpha,single in ((1,False),(2,False),(4,False),(4,True)):
                runner.self_test(alpha,single)
    (ROOT/'additive-regression.log').write_text(regression_output.getvalue())
    assert all(sha(p)==h for p,h in before.items())
    print('ADDITIVE_REGRESSION_PASS alpha1/2/4 difference and alpha4 single; temporary artifacts only')
    result['immutable_hashes'] = before
    result['actual_runner_route_pass'] = True
    result['existing_additive_regressions_pass'] = True
    (ROOT/'offline-bf16.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PROJECTION_PRECHECK_PASS',json.dumps({k:v for k,v in result.items() if k not in ('rows','vector','unit_direction_fp64','real_hybrid_calls','immutable_hashes')}))
    print('IMMUTABLE_HASHES_PASS',len(before))


def route_test(source, reference, direction):
    """Exercise run() minus-only routing with local transport fixtures; real hybrid tested above."""
    from transformers import BatchEncoding
    records = [r for r in reference['records'] if r['condition']=='bare']
    class Tokenizer:
        eos_token_id = 0
        current = None
        def __call__(self, rendered, **kwargs):
            self.current = next(r for r in records if r['rendered']==rendered)
            ids = torch.tensor([self.current['input_ids']])
            return BatchEncoding({'input_ids':ids,'attention_mask':torch.ones_like(ids)})
        def decode(self, ids, **kwargs):
            return self.current['text']
    tokenizer = Tokenizer()
    class FixtureModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.model = torch.nn.Module()
            self.model.layers = torch.nn.ModuleList([torch.nn.Identity() for _ in range(19)])
            self.device = torch.device('cpu')
        def to(self, device):
            return self
        def generate(self, input_ids, **kwargs):
            ids = tokenizer.current['generated_ids']
            for i in range(len(ids)):
                h = torch.ones(1,input_ids.shape[1] if i==0 else 1,len(direction),dtype=torch.bfloat16)
                self.model.layers[18](self.model.layers[17](h))
            return torch.cat((input_ids,torch.tensor([ids])),dim=1)
    original_sha = runner.gap.sha
    def fixture_sha(path):
        if Path(path).name == 'config.json': return source['model_config_sha256']
        if Path(path).name == 'model.safetensors.index.json': return source['model_index_sha256']
        return original_sha(path)
    with tempfile.TemporaryDirectory() as tmp:
        args = argparse.Namespace(output=Path(tmp)/'generation.json',single_concept=False,projection_removal=True,alpha=1,source_revision='offline-route-fixture')
        with patch('huggingface_hub.snapshot_download',return_value='/offline/'+runner.gap.REVISION), patch('transformers.AutoModelForCausalLM.from_pretrained',return_value=FixtureModel()), patch.object(runner,'generation_tokenizer',return_value=tokenizer), patch.object(runner.gap,'sha',side_effect=fixture_sha), patch.object(runner.gap.walk,'generation_inputs',side_effect=lambda t,rs:[next(r['rendered'] for r in records if r['scenario']==rs[0]['scenario'])]), patch.object(runner.gap.walk,'health',return_value=[{},[]]), patch.object(runner,'additive_patch',side_effect=RuntimeError('run used additive instead of removal')), patch('torch.cuda.get_device_name',return_value='OFFLINE_FIXTURE'), patch('torch.cuda.max_memory_allocated',return_value=0):
            runner.run(args)
        data = json.loads(args.output.read_text())
        assert len(data['records'])==15 and len(data['identity_controls'])==1
        assert all(r['side']=='-C' and r['method']=='sycophancy_gp_projection_removal' for r in data['records'])
        assert all(m['operator']=='projection_removal' and m['removal_fraction']==1 for r in data['records'] for m in r['measurements'])
        print('ACTUAL_RUNNER_ROUTE_PASS 15minus+1identity; old additive poisoned; fixture generation is not behavioral evidence')

if __name__=='__main__':
    main()
