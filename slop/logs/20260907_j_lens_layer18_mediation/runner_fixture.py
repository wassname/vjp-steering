"""Exercise run()'s 24-arm orchestration with explicitly mocked model transport.

The numerical hook is tested separately on a real tiny hybrid. These fabricated
records never escape the temporary directory and are not behavioral evidence.
"""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import torch


def check(run, tokenizer, reference, factorial):
    lookup = {}
    for r in reference['records']:
        if r['condition'] in ('bare', 'direct_minus'):
            lookup[tuple(r['input_ids'])] = (r['scenario'], 'B' if r['condition'] == 'bare' else 'D')
    progress, calls = {}, []
    fake_model = SimpleNamespace(device=torch.device('cpu'), model=SimpleNamespace(layers=[
        SimpleNamespace(block_type='full_attention' if i == 19 else 'linear_attention') for i in range(32)]))
    fake_model.to = lambda *a, **k: fake_model
    fake_model.eval = lambda: fake_model

    def generated(model, encoded, x, endpoint):
        assert model is fake_model
        scenario, context = lookup[tuple(encoded.input_ids[0].tolist())]
        arm = run.ARMS[progress.get(scenario, 0)]
        progress[scenario] = progress.get(scenario, 0)+1
        assert context == arm[0]
        old = {r['condition']: r for r in reference['records'] if r['scenario'] == scenario}
        neither = next(r for r in factorial['records'] if r['scenario'] == scenario and r['condition'] == 'neither')
        current = old['bare' if context == 'B' else 'direct_minus'] if arm.endswith('native') else old['bare'] if context == 'B' else neither
        width = len(old['bare']['patch']['after'])
        if arm.endswith('native'): assert x is None
        else: assert x.float().tolist() == old['bare']['patch']['after']
        origin = ('D' if context == 'B' else 'B') if arm.endswith('cross') else context
        expected_endpoint = torch.full((width,), 0. if origin == 'B' else 1., dtype=torch.bfloat16)
        if arm.endswith(('self', 'cross')): assert torch.equal(endpoint, expected_endpoint)
        else: assert endpoint is None
        final = {k: v for k, v in current['final_states'].items() if k in ('17', '18', '19', '31')}
        if arm.endswith('cross'):
            final['18'] = (neither if origin == 'D' else old['bare'])['final_states']['18']
        calls.append({'scenario': scenario, 'arm': arm, 'input_length': len(encoded.input_ids[0]), 'mock_transport': True})
        return {'generated_ids': current['generated_ids'], 'first_logits': [0.], 'final_states': copy.deepcopy(final),
            'h17_after': current['patch']['after'] if arm.endswith('native') else old['bare']['patch']['after'],
            'mixer_before': [0. if context == 'B' else 1.]*width,
            'mixer_after': expected_endpoint.float().tolist(), 'mixer_input_last': [0.]*width,
            'mixer_update_norm': 1. if arm.endswith('cross') else 0.,
            'prefill_cache_through18_sha256': 'fixture-'+context,
            'full_prefill_cache_sha256': 'fixture-'+context, 'final_decode_cache_sha256': 'fixture-'+context,
            'block_metadata_sha256': 'fixture-'+context, 'mixer_metadata_sha256': 'fixture-'+context,
            'receiving_residual': [0. if origin == 'B' else 1.],
            'mlp18_output': [0. if origin == 'B' else 1.]}

    original_sha = run.gap.sha
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        snapshot = root/run.gap.REVISION
        snapshot.mkdir()
        run.save(root/'preflight.json', {'implementation_sha256': original_sha(run.__file__),
            'donor_helper_sha256': original_sha(run.donor.__file__)})
        def fixture_sha(path):
            if Path(path) == snapshot/'config.json': return reference['model_config_sha256']
            if Path(path) == snapshot/'model.safetensors.index.json': return reference['model_index_sha256']
            return original_sha(path)
        with patch.object(run, 'ROOT', root), patch.object(run.gap, 'sha', fixture_sha), \
             patch('huggingface_hub.snapshot_download', return_value=str(snapshot)), \
             patch('transformers.AutoTokenizer.from_pretrained', return_value=tokenizer), \
             patch('transformers.AutoModelForCausalLM.from_pretrained', return_value=fake_model), \
             patch.object(run, 'generate', side_effect=generated), \
             patch.object(run.gap.walk, 'health', return_value=[{}, []]), \
             patch.object(torch.cuda, 'get_device_name', return_value='OFFLINE_FIXTURE'), \
             patch.object(torch.cuda, 'max_memory_allocated', return_value=0):
            run.run(SimpleNamespace(output=root/'generation.json', source_revision='offline-fixture'))
            result = run.load(root/'generation.json')
            assert len(result['records']) == 24 and len(run.judge_rows(result)) == 9
            assert result['runtime']['gpu'] == 'OFFLINE_FIXTURE'
    assert len(calls) == 24
    return calls
