"""PI synthetic closed-world corpus. Run once to freeze, never curate by overlap."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
FAMILIES = ('seal_match', 'capacity', 'roster', 'parity', 'precedence', 'link')
CONSUMERS = {
    'routing': ('route through gate', 'route through bypass'),
    'allocation': ('allocate two counters', 'allocate zero counters'),
    'storage': ('store in upper drawer', 'store in lower drawer'),
    'notification': ('notify team amber', 'notify team violet'),
}

def make_world(family, world, valid):
    # Both possible evidence words occur equally on either label across worlds.
    reverse = world % 2
    names = [f'Vek{world}', f'Zum{world}']
    if family == 'seal_match':
        rule = f'The operation requires a {names[reverse]} seal.'
        facts = {'required': names[reverse], 'observed': names[reverse if valid else 1-reverse]}
        evidence = f'The item carries a {facts["observed"]} seal.'
    elif family == 'capacity':
        relation = 'at least' if not reverse else 'at most'
        observed = (7 if valid else 3) if not reverse else (3 if valid else 7)
        rule = f'The operation requires a capacity of {relation} 5 units.'
        facts = {'relation': relation, 'threshold': 5, 'observed': observed}
        evidence = f'The item has a capacity of {observed} units.'
    elif family == 'roster':
        member = names[reverse if valid else 1-reverse]
        rule = f'The operation requires a member of roster {names[reverse]}.'
        facts = {'required': names[reverse], 'observed': member}
        evidence = f'The item belongs exclusively to roster {member}.'
    elif family == 'parity':
        desired = reverse
        count = (4 if valid else 5) if not reverse else (5 if valid else 4)
        rule = f'The operation requires an {"even" if not reverse else "odd"} bead count.'
        facts = {'remainder': desired, 'observed': count}
        evidence = f'The item has {count} beads.'
    elif family == 'precedence':
        first, second = names[reverse], names[1-reverse]
        sequence = [first, second] if valid else [second, first]
        rule = f'The operation requires event {first} before event {second}.'
        facts = {'first': first, 'second': second, 'sequence': sequence}
        evidence = f'The complete event order is {sequence[0]}, then {sequence[1]}.'
    else:
        start, end = names[reverse], names[1-reverse]
        edge = [start, end] if valid else [end, start]
        rule = f'The operation requires a directed connection from {start} to {end}.'
        facts = {'start': start, 'end': end, 'edge': edge}
        evidence = f'The only connection runs from {edge[0]} to {edge[1]}.'
    return rule, evidence, facts

def label(family, facts):
    if family in ('seal_match', 'roster'):
        return facts['required'] == facts['observed']
    if family == 'capacity':
        return facts['observed'] >= facts['threshold'] if facts['relation']=='at least' else facts['observed'] <= facts['threshold']
    if family == 'parity':
        return facts['observed'] % 2 == facts['remainder']
    if family == 'precedence':
        return facts['sequence'].index(facts['first']) < facts['sequence'].index(facts['second'])
    return facts['edge'] == [facts['start'], facts['end']]

rows = []
for fi, family in enumerate(FAMILIES):
    for world in range(4):
        split = ('train' if world < 2 else 'source_calibration' if world == 2 else 'withheld_source') if fi < 3 else ('source_calibration' if fi == 3 else 'withheld_source')
        consumers = ('routing', 'allocation') if world < 3 else ('storage', 'notification')
        for ci, consumer in enumerate(consumers):
            # Reverse action semantics and answer position independently across worlds/tasks.
            actions = list(CONSUMERS[consumer])
            if world % 2:
                actions.reverse()
            options = list(actions)
            if (world // 2 + ci) % 2:
                options.reverse()
            for valid in (True, False):
                rule, evidence, facts = make_world(family, world, valid)
                cue = f'{rule}\n{evidence}' if world % 2 == 0 else f'{evidence}\n{rule}'
                policy = f'When the requirement holds, {actions[0]}; otherwise, {actions[1]}.'
                prompt = ('This is a self-contained rule world; the stated requirement is the only criterion for this operation.\n'
                          + cue + '\n' + policy + '\n'
                          + f'Which action follows? A: {options[0]}. B: {options[1]}. Reply with one letter only.')
                assert label(family, facts) == valid
                rows.append({'id': f'tv1_{family}_{world}_{consumer}_{int(valid)}',
                    'pair_id': f'tv1_{family}_{world}_{consumer}', 'split': split,
                    'cue_family': family, 'world': world, 'consumer': consumer,
                    'facts': facts, 'valid': valid, 'rule': rule, 'evidence': evidence,
                    'actions_valid_invalid': actions, 'options': options,
                    'expected': 'AB'[options.index(actions[0 if valid else 1])],
                    'prompt': prompt, 'entities': [f'Vek{world}', f'Zum{world}'],
                    'provenance': 'PI synthetic rule-world, deterministic v1; not an external factual assertion'})
corpus = ''.join(json.dumps(r, sort_keys=True, ensure_ascii=False)+'\n' for r in rows).encode()
if (ROOT/'freeze.json').exists():
    assert (ROOT/'corpus.jsonl').read_bytes() == corpus, 'Frozen corpus differs; do not overwrite'
else:
    (ROOT/'corpus.jsonl').write_bytes(corpus)
    manifest = {'version': 1, 'author': 'PI/OpenAI Codex', 'phase': 'frozen before benchmark input audit',
                'corpus_sha256': hashlib.sha256(corpus).hexdigest(),
                'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'rows': len(rows), 'split_ids': {s: [r['id'] for r in rows if r['split']==s] for s in ('train','source_calibration','withheld_source')},
                'rule': 'Any later revision requires new version/hash and reports all audit findings; no outcome-driven removal.'}
    (ROOT/'freeze.json').write_text(json.dumps(manifest, indent=2)+'\n')
print('CORPUS_FREEZE_PASS', hashlib.sha256(corpus).hexdigest(), len(rows))
