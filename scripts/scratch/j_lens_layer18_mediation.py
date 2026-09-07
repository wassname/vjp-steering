"""Fixed common-h17 layer18 mixer-output mediation; not a DEV steering test."""
import argparse
import asyncio
from contextlib import contextmanager
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SCRIPT_ROOT = Path('/repo/scripts') if Path('/repo/scripts').is_dir() else Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SCRIPT_ROOT), str(SCRIPT_ROOT/'scratch')]
import torch
import j_lens_donor_context as donor

gap = donor.gap
ROOT = Path('slop/logs/20260907_j_lens_layer18_mediation')
DESIGN = Path('slop/logs/20260907_j_lens_retained_context_design')
REFERENCE = donor.REFERENCE
DONOR_REFERENCE = donor.ROOT/'generation.json'
HASHES = {str(REFERENCE): 'b69925310ad2b2744e107442b1d283569d106365fda73c5a1ec98f857bf169e9',
          str(DONOR_REFERENCE): '15a47785bb245ef5ca1eb0388fe013d78036ed12593532875b2cdff3384a2de6'}
API_HASHES = {'modeling': '0e2cd8dc50885b2701d26b116c585eedcdc62a24080ec34345af55b963126ded',
              'cache': 'ee7902fbd031ed332b5e26d07756a33f09b5c90a435b8363b9330876dc33ce0e'}
ARMS = ('B-native', 'D-native', 'B0', 'D0', 'B-self', 'D-self', 'B-cross', 'D-cross')
PAIRS = (('sensitivity', 'D-native', 'D0'), ('necessity', 'D0', 'D-cross'),
         ('sufficiency', 'B0', 'B-cross'))
load, save = donor.load, donor.save


def api_provenance():
    from transformers.models.qwen3_5 import modeling_qwen3_5
    from transformers import cache_utils
    paths = {'modeling': inspect.getfile(modeling_qwen3_5), 'cache': inspect.getfile(cache_utils)}
    hashes = {k: gap.sha(v) for k, v in paths.items()}
    assert hashes == API_HASHES, ('API source drift', hashes)
    return {'paths': paths, 'sha256': hashes}


def clone_tree(value):
    """No mutable tensor views: snapshots survive later in-place decode writes."""
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {k: clone_tree(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clone_tree(v) for v in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def digest(value):
    h = hashlib.sha256()
    def visit(x):
        if isinstance(x, torch.Tensor):
            h.update(str((str(x.dtype), tuple(x.shape))).encode())
            h.update(x.contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
        elif isinstance(x, dict):
            for k in sorted(x, key=str):
                h.update(str(k).encode()); visit(x[k])
        elif isinstance(x, (list, tuple)):
            for item in x: visit(item)
        else:
            h.update(repr(x).encode())
    visit(value)
    return h.hexdigest()


def cache_snapshot(cache, last_layer):
    assert cache is not None and len(cache.layers) > last_layer
    # Include tensor state and scalar/list initialization metadata, not only K/V.
    return [clone_tree(vars(layer)) for layer in cache.layers[:last_layer+1]]


def row(tensor):
    return tensor[0, -1].detach().float().cpu().tolist()


@contextmanager
def intervention(model, length, x, mixer_endpoint, record, layer=17):
    """Two first-prefill output seams; never writes to the hybrid cache."""
    layers = model.model.layers
    mixer_layer = layer + 1
    block = layers[mixer_layer]
    assert block.block_type == 'linear_attention'
    assert type(block.linear_attn).__name__ == 'Qwen3_5GatedDeltaNet'
    assert length > 1
    handles = []
    seen = set()
    live = {}
    record.update(hook_calls={}, final_states={})

    def once(name):
        assert name not in seen, ('hook active in decode/repeated prefill', name)
        seen.add(name)
        record['hook_calls'][name] = 1

    def clamp(module, args, kwargs, output):
        once('h17')
        assert isinstance(output, torch.Tensor) and output.shape[:2] == (1, length)
        before = output.detach().clone()
        after = output.clone()
        if x is not None:
            assert x.shape == after[0, -1].shape and x.dtype == after.dtype
            after[0, -1] = x
        assert torch.equal(after[:, :-1], before[:, :-1])
        record['h17_before'], record['h17_after'] = row(before), row(after)
        record['h17_nonfinal_exact'] = True
        live['x'] = after[:, -1].detach().clone()
        return after

    def block_input(module, args, kwargs):
        once('block18_input')
        hidden = kwargs.get('hidden_states', args[0] if args else None)
        assert torch.equal(hidden[:, -1], live['x'])
        live['block_kwargs'] = kwargs
        live['block_metadata'] = clone_tree({k: v for k, v in kwargs.items()
                                             if k not in ('hidden_states', 'past_key_values')})
        record['block_metadata_sha256'] = digest(live['block_metadata'])
        record['block18_input_exact'] = True

    def mixer_input(module, args, kwargs):
        once('mixer18_input')
        assert not args  # Installed decoder uses explicit keywords; fail on API drift.
        hidden = kwargs['hidden_states']
        assert hidden.shape[:2] == (1, length)
        live['cache'] = kwargs['cache_params']
        live['mixer_kwargs'] = kwargs
        live['mixer_metadata'] = clone_tree({k: v for k, v in kwargs.items()
                                             if k not in ('hidden_states', 'cache_params')})
        record['mixer_metadata_sha256'] = digest(live['mixer_metadata'])
        record['mixer_input_last'] = row(hidden)
        record['cache_before_mixer_sha256'] = digest(cache_snapshot(live['cache'], mixer_layer))

    def mixer_output(module, args, kwargs, output):
        once('mixer18_output')
        assert output.shape[:2] == (1, length) and isinstance(output, torch.Tensor)
        cache = live['cache']
        cache_layer = cache.layers[mixer_layer]
        assert all(cache_layer.is_conv_states_initialized.values()) and all(cache_layer.is_recurrent_states_initialized.values())
        assert all(cache_layer.has_previous_state.values())
        snapshot = cache_snapshot(cache, mixer_layer)
        fingerprint = digest(snapshot)
        assert fingerprint != record['cache_before_mixer_sha256'], 'no internal prefill cache writes observed'
        before = output.detach().clone()
        after = output.clone()
        if mixer_endpoint is not None:
            assert mixer_endpoint.shape == after[0, -1].shape and mixer_endpoint.dtype == after.dtype
            after[0, -1] = mixer_endpoint
            assert torch.equal(after[0, -1], mixer_endpoint)
        assert torch.equal(after[:, :-1], before[:, :-1])
        assert digest(cache_snapshot(cache, mixer_layer)) == fingerprint
        assert digest(clone_tree({k: v for k, v in live['mixer_kwargs'].items()
                                  if k not in ('hidden_states', 'cache_params')})) == record['mixer_metadata_sha256']
        assert digest(clone_tree({k: v for k, v in live['block_kwargs'].items()
                                  if k not in ('hidden_states', 'past_key_values')})) == record['block_metadata_sha256']
        record.update(mixer_before=row(before), mixer_after=row(after),
                      mixer_nonfinal_exact=True, cache_at_hook_unchanged=True,
                      cache_written_before_hook=True, positions_masks_unchanged=True,
                      prefill_cache_through18_sha256=fingerprint,
                      cache_layer_sha256=[digest(s) for s in snapshot],
                      mixer_update_norm=float((after[:, -1].double()-before[:, -1].double()).norm()))
        # Retain a cloned snapshot until final prefill observation, never the live cache tensors.
        live['snapshot'] = snapshot
        live['cache_digest'] = fingerprint
        live['residual'] = live['x'] + after[:, -1]
        return after

    def residual_input(module, args):
        once('postnorm18_input')
        assert torch.equal(args[0][:, -1], live['residual'])
        record['receiving_residual'] = row(args[0])
        record['residual_exact'] = True

    def mlp_output(module, args, output):
        once('mlp18_output')
        live['h18'] = live['residual'] + output[:, -1]
        record['mlp18_output'] = row(output)

    def next_input(module, args, kwargs):
        once('block19_input')
        hidden = kwargs.get('hidden_states', args[0] if args else None)
        assert torch.equal(hidden[:, -1], live['h18'])
        record['block19_input_exact'] = True

    def observe(index):
        def hook(module, args, output):
            once('block'+str(index)+'_output')
            record['final_states'][str(index)] = row(output)
            if index == mixer_layer:
                assert torch.equal(output[:, -1], live['h18'])
            if index == len(layers)-1:
                assert digest(live['snapshot']) == live['cache_digest']
                assert digest(cache_snapshot(live['cache'], mixer_layer)) == live['cache_digest']
                record['cache_preserved_through_prefill'] = True
                record['full_prefill_cache_sha256'] = digest(cache_snapshot(live['cache'], len(layers)-1))
                for handle in handles: handle.remove()
        return hook

    try:
        handles.append(layers[layer].register_forward_hook(clamp, with_kwargs=True))
        handles.append(block.register_forward_pre_hook(block_input, with_kwargs=True))
        handles.append(block.linear_attn.register_forward_pre_hook(mixer_input, with_kwargs=True))
        handles.append(block.linear_attn.register_forward_hook(mixer_output, with_kwargs=True))
        handles.append(block.post_attention_layernorm.register_forward_pre_hook(residual_input))
        handles.append(block.mlp.register_forward_hook(mlp_output))
        handles.append(layers[mixer_layer+1].register_forward_pre_hook(next_input, with_kwargs=True))
        for index in sorted({layer, mixer_layer, mixer_layer+1, len(layers)-1}):
            handles.append(layers[index].register_forward_hook(observe(index)))
        yield
    finally:
        for handle in handles: handle.remove()


def generate(model, encoded, x=None, mixer_endpoint=None, max_tokens=512, layer=17):
    assert encoded.input_ids.shape[0] == 1
    assert bool((encoded.attention_mask == 1).all()), 'no padding or positional equalization authorized'
    inputs = clone_tree(dict(encoded))
    record = {}
    with torch.inference_mode(), intervention(model, encoded.input_ids.shape[1], x, mixer_endpoint, record, layer):
        output = model.generate(**encoded, do_sample=False, temperature=None, top_p=None, top_k=None,
            pad_token_id=model.config.eos_token_id, max_new_tokens=max_tokens, use_cache=True,
            return_dict_in_generate=True, output_logits=True)
    assert digest(inputs) == digest(clone_tree(dict(encoded)))
    record['generated_ids'] = output.sequences[0, encoded.input_ids.shape[1]:].tolist()
    record['first_logits'] = output.logits[0][0].float().cpu().tolist()
    record['inputs_unchanged'] = True
    record['final_decode_cache_sha256'] = digest(cache_snapshot(output.past_key_values, len(model.model.layers)-1))
    return record


def check_arm(arm, record, prior, old, historical_neither, layer=17):
    """Same function checks tiny fixtures and the paid runner's saved observations."""
    context = arm[0]
    native = 'B-native' if context == 'B' else 'D-native'
    if arm.endswith('native'):
        previous = old['bare' if context == 'B' else 'direct_minus']
        assert record['generated_ids'] == previous['generated_ids'], 'native replay IDs'
        assert record['h17_after'] == previous['patch']['after'], 'native h17 replay'
        for index, value in record['final_states'].items():
            assert value == previous['final_states'][index], ('native block replay', index)
    else:
        assert record['h17_after'] == old['bare']['patch']['after']
        assert record['mixer_input_last'] == prior['B0' if arm != 'B0' else 'B-native']['mixer_input_last']
    if arm == 'D0':
        assert record['generated_ids'] == historical_neither['generated_ids'], 'D0 prior neither IDs'
        for index, value in record['final_states'].items():
            assert value == historical_neither['final_states'][index], ('D0 prior neither states', index)
    if arm == 'B0' or arm.endswith('self'):
        baseline = prior[native if arm == 'B0' else context+'0']
        for key in ('generated_ids', 'first_logits', 'final_states', 'prefill_cache_through18_sha256',
                    'block_metadata_sha256', 'mixer_metadata_sha256', 'full_prefill_cache_sha256', 'final_decode_cache_sha256'):
            assert record[key] == baseline[key], ('identity', arm, key)
        record['identity_exact'] = True
    if arm.endswith(('self', 'cross')):
        base = prior[context+'0']
        endpoint = prior[('D' if context == 'B' else 'B')+'0'] if arm.endswith('cross') else base
        assert record['mixer_after'] == endpoint['mixer_before']
        assert record['prefill_cache_through18_sha256'] == base['prefill_cache_through18_sha256']
        assert record['block_metadata_sha256'] == base['block_metadata_sha256']
        assert record['mixer_metadata_sha256'] == base['mixer_metadata_sha256']
        assert record['final_states'][str(layer+1)] == endpoint['final_states'][str(layer+1)], 'h18 endpoint mismatch'
        assert record['receiving_residual'] == endpoint['receiving_residual']
        assert record['mlp18_output'] == endpoint['mlp18_output']
        if arm.endswith('cross'): assert record['mixer_update_norm'] > 0
        record['endpoint_exact'] = True


def run(args):
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    start = time.monotonic()
    assert not args.output.exists()
    api = api_provenance()
    assert all(gap.sha(p) == h for p, h in HASHES.items())
    reference, factorial = load(REFERENCE), load(DONOR_REFERENCE)
    preflight = load(ROOT/'preflight.json')
    assert preflight['implementation_sha256'] == gap.sha(__file__)
    assert preflight['donor_helper_sha256'] == gap.sha(donor.__file__)
    snapshot = Path(snapshot_download(gap.MODEL, revision=gap.REVISION))
    assert snapshot.name == gap.REVISION
    assert gap.sha(snapshot/'config.json') == reference['model_config_sha256']
    assert gap.sha(snapshot/'model.safetensors.index.json') == reference['model_index_sha256']
    tokenizer = AutoTokenizer.from_pretrained(snapshot)
    tokenizer.pad_token = tokenizer.eos_token
    encoded_inputs = {}
    for r in reference['records']:
        if r['condition'] in ('bare', 'direct_minus'):
            encoded = tokenizer(r['rendered'], return_tensors='pt', add_special_tokens=False)
            assert encoded.input_ids[0].tolist() == r['input_ids']
            encoded_inputs[r['scenario'], r['condition']] = encoded
    model = AutoModelForCausalLM.from_pretrained(snapshot, dtype=torch.bfloat16).to('cuda').eval()
    assert [model.model.layers[i].block_type for i in (17, 18, 19)] == ['linear_attention', 'linear_attention', 'full_attention']
    data = {'schema': 'layer18_mediation_v1', 'source_revision': args.source_revision,
            'implementation_sha256': gap.sha(__file__), 'api': api, 'source_hashes': HASHES,
            'model_revision': gap.REVISION, 'settings': {'h17_layer': 17, 'mixer_layer': 18,
            'dtype': 'bfloat16', 'batch': 1, 'max_new_tokens': 512, 'one_shot': True, 'cache_swap': False},
            'arms': ARMS, 'records': [], 'argv': sys.argv}
    print('LAYER18_CONFIG', json.dumps(data), flush=True)
    print('SHOULD:24responses;18judgments later;commonh17,mixer-only/final-only/first-only;self identities;crossh18 endpoint exact;upstream cache unchanged;no DEV-success inference.', flush=True)
    for scenario in gap.SCENARIOS:
        old = {r['condition']: r for r in reference['records'] if r['scenario'] == scenario}
        neither = next(r for r in factorial['records'] if r['scenario'] == scenario and r['condition'] == 'neither')
        prior = {}
        x = torch.tensor(old['bare']['patch']['after'], dtype=torch.bfloat16, device=model.device)
        for arm in ARMS:
            source = old['bare' if arm[0] == 'B' else 'direct_minus']
            encoded = encoded_inputs[scenario, source['condition']].to(model.device)
            endpoint = None
            if arm.endswith(('self', 'cross')):
                origin = arm[0] if arm.endswith('self') else ('D' if arm[0] == 'B' else 'B')
                endpoint = torch.tensor(prior[origin+'0']['mixer_before'], dtype=torch.bfloat16, device=model.device)
            record = generate(model, encoded, None if arm.endswith('native') else x, endpoint)
            record.update(scenario=scenario, condition=arm, prompt=source['prompt'], rendered=source['rendered'],
                          input_ids=source['input_ids'], text=tokenizer.decode(record['generated_ids'], skip_special_tokens=True).strip())
            record['health'] = gap.walk.health(tokenizer, [record['text']])
            data['records'].append(record)
            save(args.output, data)  # Persist observations before any gate that can fail.
            check_arm(arm, record, prior, old, neither)
            record['gates_pass'] = True
            prior[arm] = record
            save(args.output, data)
            print('LAYER18_RESPONSE', json.dumps({k: record[k] for k in ('scenario', 'condition', 'rendered', 'text', 'health', 'mixer_update_norm', 'gates_pass')}), flush=True)
    data['runtime'] = {'seconds': time.monotonic()-start, 'gpu': torch.cuda.get_device_name(),
                       'peak_memory_bytes': torch.cuda.max_memory_allocated(), 'torch': torch.__version__}
    save(args.output, data)
    print('LAYER18_COMPLETE', json.dumps(data['runtime']), flush=True)


def judge_rows(data):
    assert len(data['records']) == 24
    assert {(r['scenario'], r['condition']) for r in data['records']} == {(s, a) for s in gap.SCENARIOS for a in ARMS}
    rows = []
    for scenario in gap.SCENARIOS:
        rs = {r['condition']: r for r in data['records'] if r['scenario'] == scenario}
        for arm, r in rs.items():
            base = rs[arm[0]+'-native']
            assert r['gates_pass'] and r['input_ids'] == base['input_ids'] and r['rendered'] == base['rendered']
        assert all(rs[a]['identity_exact'] for a in ('B0', 'B-self', 'D-self'))
        assert all(rs[a]['endpoint_exact'] for a in ('B-cross', 'D-cross'))
        for name, baseline, treatment in PAIRS:
            b, t = rs[baseline], rs[treatment]
            rows.append({'bare': b['text'], 'steered': t['text'], 'prompt': t['prompt'], 'vignette': scenario,
                         'side': '-C', 'run': 'layer18-mixer-mediation', 'method': 'layer18_'+name,
                         'condition': name, 'source': str(ROOT/'generation.json')})
    assert len(rows) == 9
    return rows


async def judge_run():
    import judge
    import export
    from openai import AsyncOpenAI
    assert judge.MODEL == 'deepseek/deepseek-v4-flash-0731'
    assert judge.RUBRIC == 'results-demo-perresponse-syco-v7'
    data = load(ROOT/'generation.json')
    assert 'runtime' in data
    rows = judge_rows(data)
    out, trace = ROOT/'judgments.jsonl', ROOT/'judge-transport.jsonl'
    assert not out.exists() and not trace.exists()
    client = AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'], base_url='https://openrouter.ai/api/v1', timeout=60., max_retries=0)
    try:
        for r in rows:
            for order in ('AB', 'BA'):
                result = await donor.judge_cell(client, r, order, trace)
                result['exported_effect'] = export.signed_axis_effect('-C', [export.score_cell(result)])
                with out.open('a') as f: f.write(json.dumps(result, ensure_ascii=False)+'\n')
                print('LAYER18_JUDGMENT', json.dumps(result, ensure_ascii=False), flush=True)
    finally:
        await client.close()


if __name__ != '__main__':
    import modal
    from run_modal import image, cache, source_revision
    for path in (REFERENCE, DONOR_REFERENCE, ROOT/'preflight.json'):
        if path.exists(): image = image.add_local_file(str(path), '/repo/'+str(path))
    app = modal.App('jsteer-layer18-mediation', image=image)
    @app.function(gpu='H100', volumes={'/cache': cache}, timeout=360, max_containers=1, retries=0)
    def remote(revision: str):
        destination = Path('/cache/outputs/audits/20260907_j_lens_layer18_mediation/generation.json')
        try:
            subprocess.run([sys.executable, 'scripts/scratch/j_lens_layer18_mediation.py', '--output', str(destination),
                            '--source-revision', revision], cwd='/repo', check=True)
            return destination.read_text()
        finally:
            cache.commit()
    @app.local_entrypoint()
    def launch():
        assert not (ROOT/'generation.json').exists()
        assert load(ROOT/'preflight.json')['implementation_sha256'] == gap.sha(__file__)
        (ROOT/'generation.json').write_text(remote.remote(source_revision()))
        print('LAYER18_DOWNLOADED', ROOT/'generation.json', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'generation.json')
    parser.add_argument('--source-revision', default='unknown')
    parser.add_argument('--judge', action='store_true')
    args = parser.parse_args()
    if args.judge: asyncio.run(judge_run())
    else: run(args)
