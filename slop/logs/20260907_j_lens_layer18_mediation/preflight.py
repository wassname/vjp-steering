"""Actual tiny hybrid cached-generation and exact diagnostic transport fixtures; CPU only."""
import asyncio
import copy
import inspect
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
sys.path[:0] = ['scripts/scratch', 'scripts', 'src']
import torch
import j_lens_layer18_mediation as run
import judge
import export
from transformers import Qwen3_5TextConfig, Qwen3_5ForCausalLM, AutoTokenizer, BatchEncoding

api = run.api_provenance()
protected = {str(p): run.gap.sha(p) for p in [*map(Path, run.HASHES),
    Path('results/plot.png'), Path('results/plot_pareto.png'), Path('results/index.md'),
    Path('results/index.html'), Path('data/results.csv'), Path('scripts/judge.py')]}
assert all(protected[p] == h for p, h in run.HASHES.items())
ref, factorial = run.load(run.REFERENCE), run.load(run.DONOR_REFERENCE)
tokenizer = AutoTokenizer.from_pretrained(run.gap.MODEL, revision=run.gap.REVISION, local_files_only=True)
tokenizer.pad_token = tokenizer.eos_token
for r in ref['records']:
    if r['condition'] in ('bare', 'direct_minus'):
        assert tokenizer(r['rendered'], add_special_tokens=False)['input_ids'] == r['input_ids']
print('LAYER18_API_SOURCE_PASS', json.dumps(api), flush=True)

# Cache snapshot mutation control: a retained view would fail this check.
sample = torch.arange(4.)
cloned = run.clone_tree({'states': [sample]})
before = run.digest(cloned)
sample.add_(1)
assert run.digest(cloned) == before and not torch.equal(sample, cloned['states'][0])

torch.manual_seed(18)
config = Qwen3_5TextConfig(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=4,
    num_attention_heads=2, num_key_value_heads=1, head_dim=16,
    layer_types=['linear_attention', 'linear_attention', 'full_attention', 'linear_attention'],
    linear_num_key_heads=2, linear_num_value_heads=2, linear_key_head_dim=8, linear_value_head_dim=8,
    pad_token_id=0, eos_token_id=63)
model = Qwen3_5ForCausalLM(config).eval().bfloat16()
# Suppress EOS only on this synthetic model to force multiple cached decode calls.
model.generation_config.eos_token_id = None
contexts = {'B': [1, 2, 3, 4], 'D': [1, 8, 7, 6, 5, 2, 3, 4]}
encoded = {k: BatchEncoding({'input_ids': torch.tensor([v]),
    'attention_mask': torch.ones(1, len(v), dtype=torch.long)}) for k, v in contexts.items()}

def clean():
    assert not any(m._forward_hooks or m._forward_pre_hooks for m in model.modules())

def natural(context):
    states, handles = {}, []
    def observe(i):
        def hook(module, args, output):
            if str(i) not in states: states[str(i)] = run.row(output)
        return hook
    try:
        for i, block in enumerate(model.model.layers): handles.append(block.register_forward_hook(observe(i)))
        with torch.inference_mode():
            output = model.generate(**encoded[context], do_sample=False, temperature=None, top_p=None, top_k=None,
                pad_token_id=model.config.eos_token_id, max_new_tokens=4, use_cache=True,
                return_dict_in_generate=True, output_logits=True)
    finally:
        for h in handles: h.remove()
    return {'generated_ids': output.sequences[0, len(contexts[context]):].tolist(),
            'first_logits': output.logits[0][0].float().tolist(), 'final_states': states,
            'patch': {'after': states['0']}}

old = {'bare': natural('B'), 'direct_minus': natural('D')}
x = torch.tensor(old['bare']['patch']['after'], dtype=torch.bfloat16)
# Count actual cached calls outside the intervention separately.
prior, measurements = {}, []
for arm in run.ARMS:
    context = arm[0]
    endpoint = None
    if arm.endswith(('self', 'cross')):
        origin = context if arm.endswith('self') else ('D' if context == 'B' else 'B')
        endpoint = torch.tensor(prior[origin+'0']['mixer_before'], dtype=torch.bfloat16)
    observed_calls = []
    observer = model.model.layers[1].linear_attn.register_forward_pre_hook(
        lambda module, args, kwargs: observed_calls.append(kwargs['hidden_states'].shape[1]), with_kwargs=True)
    try:
        record = run.generate(model, encoded[context], None if arm.endswith('native') else x, endpoint, max_tokens=4, layer=0)
    finally:
        observer.remove()
    assert observed_calls == [len(contexts[context]), 1, 1, 1]
    if arm.endswith('native'):
        assert record['first_logits'] == old['bare' if context == 'B' else 'direct_minus']['first_logits']
    # D0's independent common-input reference uses only a layer0 output clamp, no mixer seam.
    if arm == 'D0':
        state = {}
        handles = []
        def clamp(module, args, output):
            if output.shape[1] == len(contexts['D']):
                replacement = output.clone(); replacement[0, -1] = x
                return replacement
        def observe(i):
            def hook(module, args, output):
                if str(i) not in state: state[str(i)] = run.row(output)
            return hook
        try:
            handles.append(model.model.layers[0].register_forward_hook(clamp))
            for i, block in enumerate(model.model.layers): handles.append(block.register_forward_hook(observe(i)))
            with torch.inference_mode():
                independent = model.generate(**encoded['D'], do_sample=False, temperature=None, top_p=None, top_k=None,
                    pad_token_id=model.config.eos_token_id, max_new_tokens=4, use_cache=True,
                    return_dict_in_generate=True, output_logits=True)
        finally:
            for h in handles: h.remove()
        neither = {'generated_ids': independent.sequences[0, len(contexts['D']):].tolist(), 'final_states': state}
        assert independent.logits[0][0].float().tolist() == record['first_logits']
    run.check_arm(arm, record, prior, old, neither if 'neither' in globals() else {}, layer=0)
    prior[arm] = record
    measurements.append({'arm': arm, 'prefill_length': len(contexts[context]), 'observed_mixer_calls': observed_calls,
        'mixer_norm': record['mixer_update_norm'], 'hook_calls': record['hook_calls'],
        'cache_through_mixer': record['prefill_cache_through18_sha256'],
        'cache_per_layer': record['cache_layer_sha256'],
        'full_prefill_cache': record['full_prefill_cache_sha256'], 'final_decode_cache': record['final_decode_cache_sha256'],
        'endpoint_exact': record.get('endpoint_exact'),
        'identity_exact': record.get('identity_exact'), 'h17': record['h17_after'],
        'h18': record['final_states']['1'], 'mixer_before': record['mixer_before'], 'mixer_after': record['mixer_after']})
    clean()
assert prior['B0']['h17_after'] == prior['D0']['h17_after']
assert prior['B0']['mixer_before'] != prior['D0']['mixer_before']
assert prior['B-cross']['prefill_cache_through18_sha256'] != prior['D0']['prefill_cache_through18_sha256']
assert prior['B-cross']['full_prefill_cache_sha256'] != prior['B0']['full_prefill_cache_sha256']
assert prior['D-cross']['full_prefill_cache_sha256'] != prior['D0']['full_prefill_cache_sha256']
assert prior['B0']['full_prefill_cache_sha256'] != prior['B0']['final_decode_cache_sha256']
# Exceptional cleanup both before execution and after hooks have started, including a poisoned wrong seam.
for failure in ('before', 'wrong_block_output'):
    poison = None
    if failure == 'wrong_block_output':
        def wrong(module, args, output):
            changed = output.clone(); changed[0, -1] += 1
            return changed
        poison = model.model.layers[1].register_forward_hook(wrong)
    try:
        if failure == 'before':
            with run.intervention(model, 4, x, None, {}, layer=0):
                raise RuntimeError('intentional context failure')
        else:
            run.generate(model, encoded['B'], x, torch.tensor(prior['D0']['mixer_before'], dtype=torch.bfloat16), max_tokens=4, layer=0)
    except (RuntimeError, AssertionError):
        pass
    else:
        raise AssertionError('negative control was not rejected: '+failure)
    finally:
        if poison is not None: poison.remove()
    clean()
# Padding not allowed; the actual generation API rejects it before any forward.
bad = copy.deepcopy(encoded['B']); bad.attention_mask[0, 0] = 0
try: run.generate(model, bad, x, None, max_tokens=4, layer=0)
except AssertionError: pass
else: raise AssertionError('padding accepted')
again = run.generate(model, encoded['B'], None, None, max_tokens=4, layer=0)
assert again['first_logits'] == prior['B-native']['first_logits'] and again['generated_ids'] == prior['B-native']['generated_ids']
clean()
print('LAYER18_REAL_TINY_PASS', json.dumps(measurements), flush=True)

fixture = {'runtime': {'offline_fixture': True}, 'records': []}
for scenario in run.gap.SCENARIOS:
    rs = {r['condition']: r for r in ref['records'] if r['scenario'] == scenario}
    for arm in run.ARMS:
        origin = rs['bare' if arm[0] == 'B' else 'direct_minus']
        fixture['records'].append({**origin, 'condition': arm, 'gates_pass': True,
                                  'identity_exact': arm in ('B0', 'B-self', 'D-self'),
                                  'endpoint_exact': arm in ('B-cross', 'D-cross')})
rows = run.judge_rows(fixture)
assert judge.MODEL == 'deepseek/deepseek-v4-flash-0731' and judge.RUBRIC == 'results-demo-perresponse-syco-v7'
for mutation in ('missing', 'context', 'identity', 'endpoint', 'gate'):
    bad = copy.deepcopy(fixture)
    if mutation == 'missing': bad['records'].pop()
    elif mutation == 'context': bad['records'][2]['input_ids'] = []
    elif mutation == 'identity': bad['records'][4]['identity_exact'] = False
    elif mutation == 'endpoint': bad['records'][6]['endpoint_exact'] = False
    else: bad['records'][0]['gates_pass'] = False
    try: run.judge_rows(bad)
    except AssertionError: pass
    else: raise AssertionError('invalid artifact accepted: '+mutation)

async def transport_check():
    calls = []
    raw = json.dumps({'on_axis_A': 1.2, 'on_axis_B': 2.3, 'off_axis_A': .1, 'off_axis_B': .2, 'evidence': 'offline fixture'})
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=raw))],
        usage=SimpleNamespace(cost=0), model_dump=lambda: {'offline_fixture': True})
    async def create(**kwargs):
        calls.append(kwargs); return response
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    with tempfile.TemporaryDirectory() as temp:
        for r in rows:
            for order in ('AB', 'BA'):
                cell = await run.donor.judge_cell(client, r, order, Path(temp)/'trace.jsonl')
                assert cell['prompt'] == judge.judge_prompt(r, order) and cell['cache_key'] == judge.cache_key(r, order, 0)
                assert calls[-1] == {'model': judge.MODEL, 'messages': [{'role': 'user', 'content': cell['prompt']}],
                    'temperature': .7, 'max_tokens': 1024, 'response_format': judge.FORMAT,
                    'extra_body': {'reasoning': {'enabled': False}, 'provider': judge.provider_route(0)}}
                effect = export.signed_axis_effect('-C', [export.score_cell(cell)])
                assert abs(effect - (-1.1 if order == 'AB' else 1.1)) < 1e-12
        assert len(calls) == 18
        response.choices[0].message.content = 'invalid JSON'
        try: await run.donor.judge_cell(client, rows[0], 'AB', Path(temp)/'trace.jsonl')
        except run.donor.NoRetry: pass
        else: raise AssertionError('invalid output retried')
        assert len(calls) == 19  # 18 valid fixture calls +1 deliberate failure, no paid requests.
asyncio.run(transport_check())
from runner_fixture import check as check_runner
runner_calls = check_runner(run, tokenizer, ref, factorial)
print('LAYER18_ACTUAL_RUNNER_FIXTURE_PASS', json.dumps(runner_calls), flush=True)
assert protected == {p: run.gap.sha(p) for p in protected}
result = {'implementation_sha256': run.gap.sha(run.__file__), 'donor_helper_sha256': run.gap.sha(run.donor.__file__),
    'api': api, 'protected_hashes': protected, 'tiny_measurements': measurements,
    'tiny_hybrid_cached_route': True, 'actual_run_orchestration_fixture': runner_calls, 'exception_cleanup': True, 'wrong_block_route_rejected': True,
    'cache_snapshot_no_alias': True, 'tokenizer_inputs_exact': 6, 'fixture_responses': 24, 'requests': 18,
    'judge_model': judge.MODEL, 'rubric': judge.RUBRIC, 'unchanged_requests': True, 'no_retry_transport': True,
    'scope': 'CPU synthetic hybrid only; no real model generation, GPU app, or judge call'}
run.save(run.ROOT/'preflight.json', result)
print('LAYER18_PREFLIGHT_PASS', json.dumps({k:v for k,v in result.items() if k != 'tiny_measurements'}), flush=True)
