"""Read-only labels, split and overlap audit AFTER immutable candidate freeze.
Only source prompts/IDs and benchmark prompts/IDs are inspected; no answer keys.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--version', type=int, choices=(1,2), default=1)
args = parser.parse_args()
ROOT = Path(__file__).parent / ('v2' if args.version==2 else '')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def norm(text):
    return ' '.join(re.findall(r'[a-z0-9]+', text.lower()))

def grams(text, n=5):
    words = norm(text).split()
    return {' '.join(words[i:i+n]) for i in range(len(words)-n+1)}

def oracle(row):
    # Independent of generator function: evaluate stored declarative evidence.
    f, x = row['cue_family'], row['facts']
    if f in ('seal_match', 'roster'):
        return x['observed'] in {x['required']}
    if f == 'capacity':
        return (x['observed'] - x['threshold']) * (1 if x['relation']=='at least' else -1) >= 0
    if f == 'parity':
        return (x['observed'] - x['remainder']) % 2 == 0
    if f == 'precedence':
        return x['sequence'] == [x['first'], x['second']]
    assert f == 'link'
    return x['edge'][0] == x['start'] and x['edge'][1] == x['end']

freeze = json.loads((ROOT/'freeze.json').read_text())
assert sha(ROOT/'corpus.jsonl') == freeze['corpus_sha256']
assert sha(ROOT/'build.py') == freeze['generator_sha256']
rows = [json.loads(line) for line in (ROOT/'corpus.jsonl').read_text().splitlines()]
assert len(rows) == freeze['rows'] and len({r['id'] for r in rows}) == freeze['rows']
pairs = collections.defaultdict(list)
for r in rows:
    assert oracle(r) == r['valid']
    assert r['options']['AB'.index(r['expected'])] == r['actions_valid_invalid'][0 if r['valid'] else 1]
    assert r['id'] in freeze['split_ids'][r['split']]
    assert r['rule'] in r['prompt'] and r['evidence'] in r['prompt']
    pairs[r['pair_id']].append(r)
for pair in pairs.values():
    a,b = pair
    assert a['valid'] != b['valid'] and a['expected'] != b['expected']
    assert a['split'] == b['split'] and a['rule'] == b['rule']
    assert a['prompt'].replace(a['evidence'],'<EVIDENCE>') == b['prompt'].replace(b['evidence'],'<EVIDENCE>')
    assert len(a['prompt'].split()) == len(b['prompt'].split())
splits = {}
for split in freeze['split_ids']:
    subset = [r for r in rows if r['split']==split]
    balance = {str(v): dict(collections.Counter(r['expected'] for r in subset if r['valid']==v)) for v in (True,False)}
    assert all(b['A']==b['B'] for b in balance.values())
    splits[split] = {'rows':len(subset),'validity_answer_balance':balance,
        'cue_families':sorted({r['cue_family'] for r in subset}),
        'consumers':sorted({r['consumer'] for r in subset})}
consumer_balance = []
for split in freeze['split_ids']:
    for consumer in sorted({r['consumer'] for r in rows if r['split']==split}):
        for valid in (True,False):
            counts=collections.Counter(r['expected'] for r in rows if r['split']==split and r['consumer']==consumer and r['valid']==valid)
            consumer_balance.append({'split':split,'consumer':consumer,'valid':valid,'counts':dict(counts),'balanced':counts['A']==counts['B']})
held_tasks={'storage','notification'}
leaks=[r['id'] for r in rows if r['consumer'] in held_tasks and r['split']!='withheld_source']
cue_groups=collections.defaultdict(list)
for r in rows:
    cue_groups[norm(r['rule']+' '+r['evidence'])].append(r)
shared_cues=[{'ids':[r['id'] for r in group], 'splits':sorted({r['split'] for r in group})} for group in cue_groups.values() if len({r['split'] for r in group})>1]
internal={'per_consumer_label_balance':consumer_balance,'withheld_consumer_leaks':leaks,
          'unique_rule_evidence_cues':len(cue_groups),'cross_split_reused_cues':shared_cues}
if args.version==2:
    assert all(c['balanced'] for c in consumer_balance)
    assert not leaks
    assert held_tasks <= {r['consumer'] for r in rows if r['split']=='withheld_source'}
    original={r['id']:r for r in map(json.loads,(ROOT.parent/'corpus.jsonl').read_text().splitlines())}
    assert {r['v1_parent_id'] for r in rows}==set(original)
    assert all(all(r[k]==original[r['v1_parent_id']][k] for k in ('rule','evidence','facts','valid','split','cue_family')) for r in rows)
else:
    (ROOT/'internal-design-failure.json').write_text(json.dumps(internal,indent=2)+'\n')
# Do not treat source labels as model-inferred states. No model is loaded.
cohort_path = Path('data/bullshit_bench_v2.jsonl')
raw_cohort = [json.loads(line) for line in cohort_path.read_text().splitlines()]
cohort = [{'id':r['scenario'], 'prompt':r['prompt']} for r in raw_cohort]
del raw_cohort
assert len(cohort)==100
cohort_digest = hashlib.sha256(json.dumps([[r['id'],r['prompt']] for r in cohort],separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
inputs = [{'role':'full', 'path':str(cohort_path),'sha256':sha(cohort_path),'ids':[r['id'] for r in cohort],
           'input_projection_sha256':cohort_digest,'selector':'all100; walk.read_cohort, scripts/walk.py'},
          {'role':'DEV','path':str(cohort_path),'sha256':sha(cohort_path),'ids':[r['id'] for r in cohort[:15]],
           'selector':'first15; src/vjp_steering/experiment.py DEV; scripts/experiment.py'}]
comparison = [{**r,'dataset':'full'} for r in cohort]
missing = []
for version in ('components-source-v13','components-source-v15','full-components-source-v16'):
    p = Path('outputs/experiments/j-lens-persona-'+version+'/extraction/metadata.json')
    if not p.exists():
        missing.append(str(p)); continue
    m = json.loads(p.read_text())
    ids, prompts, nfit = m['source_ids'], m['source_prompts'], m['source_fit_count']
    assert len(ids)==nfit+m['source_holdout_count']
    for role,start,end in [('historical_fit',0,nfit),('historical_source_holdout',nfit,len(ids))]:
        inputs.append({'role':role,'path':str(p),'sha256':sha(p),'ids':ids[start:end],
                       'selector':f'source_prompts per condition indices[{start}:{end}]'})
        for condition, texts in prompts.items():
            assert len(texts)==len(ids)
            comparison.extend({'id':sid,'prompt':text,'dataset':version+'/'+role+'/'+condition} for sid,text in zip(ids[start:end],texts[start:end]))
for version in ('components-calibration-v15','full-components-calibration-v16'):
    p=Path('outputs/experiments/j-lens-persona-'+version+'/calibration.json')
    if not p.exists():
        missing.append(str(p)); continue
    m=json.loads(p.read_text())
    assert m['cohort_sha256']==cohort_digest and m['cohort_size']==15
    inputs.append({'role':'historical_calibration','path':str(p),'sha256':sha(p),
        'ids':[r['id'] for r in cohort[:15]],'selector':'cohort_size15, cohort_sha256 matches full ordered input projection'})
# Exact duplicate source prompt observations are retained with all dataset provenance.
findings = {'exact_id':[], 'normalized_content':[], 'substring_40_chars':[], 'shared_5grams':[], 'entities':[], 'relation_templates':[]}
relations = {'capacity':('capacity','at least'), 'roster':('member','roster'),
             'seal_match':('seal','requires'), 'parity':('odd','even'),
             'precedence':('before','event'), 'link':('directed','connection')}
for r in rows:
    a=norm(r['prompt']); ag=grams(r['prompt'])
    for other in comparison:
        b=norm(other['prompt'])
        ref={'corpus_id':r['id'],'other_id':other['id'],'dataset':other['dataset']}
        if r['id']==other['id']:
            findings['exact_id'].append(ref)
        if a==b:
            findings['normalized_content'].append(ref)
        if min(len(a),len(b))>=40 and (a in b or b in a):
            findings['substring_40_chars'].append(ref)
        shared=sorted(ag & grams(other['prompt']))
        if shared:
            findings['shared_5grams'].append({**ref,'phrases':shared})
        entities=[e for e in r['entities'] if re.search(r'\b'+re.escape(e)+r'\b',r['prompt']) and re.search(r'\b'+re.escape(e)+r'\b',other['prompt'],re.I)]
        if entities:
            findings['entities'].append({**ref,'entities':entities})
        terms=relations[r['cue_family']]
        if all(re.search(r'\b'+re.escape(t)+r'\b',b) for t in terms):
            findings['relation_templates'].append({**ref,'terms':terms})
protected = {str(p):sha(p) for p in map(Path, ['results/plot.png','results/index.md','results/index.html','data/results.csv','scripts/judge.py'])}
result = {'frozen_corpus_sha256':sha(ROOT/'corpus.jsonl'),'split_summary':splits,
          'internal_design':internal,
          'overlap_inputs':inputs,'missing_inputs':missing,'comparison_records':len(comparison),
          'overlap_findings':findings,'overlap_counts':{k:len(v) for k,v in findings.items()},
          'limits':['Lexical/template audit is not a semantic-independence proof.',
                    'Audited full100 local benchmark; upstream future/withheld private inputs unknown.',
                    'Historical fit v13/v15/v16 and calibration v15/v16 only; not every historical fit.',
                    'JSON containers parsed, but only prompt/ID/source metadata projected; answer keys and generated responses never inspected.',
                    'No rows removed or edited after freeze; all relation hits retained.',
                    'Synthetic entities and instruction scaffold recur across source splits; no entity-disjoint claim.'],
          'protected_sha256':protected}
(ROOT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
assert sha(ROOT/'corpus.jsonl')==freeze['corpus_sha256']
print('TASK_VALIDITY_V2_CORPUS_PASS' if args.version==2 else 'V1_RULE_LABELS_PASS_INTERNAL_DESIGN_FAIL',json.dumps({'rows':len(rows),'pairs':len(pairs),'splits':splits,'overlap_counts':result['overlap_counts'],'missing_inputs':missing,'protected_files':len(protected),'per_consumer_balance_pass':all(c['balanced'] for c in consumer_balance),'withheld_consumer_leaks':len(leaks)}))
