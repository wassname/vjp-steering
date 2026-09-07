"""Preserve all 72 TCA cells with supplied answers/rubric, no score rewriting."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).parent
manifest=json.loads(Path('slop/logs/20260907_j_lens_judged_display/manifest.json').read_text())
records=[]
for item in manifest['artifacts']:
    p=Path(item['judgments']); assert hashlib.sha256(p.read_bytes()).hexdigest()==item['judgments_sha256']
    for line in p.read_text().splitlines():
        j=json.loads(line)
        if j['vignette']!='syco_bullshit_v2_sw_pnf_02': continue
        a,b=j['prompt'].split('\nResponse A:\n')[1].split('\n\nResponse B:\n')
        records.append({'source':str(p),'method':item['method'],'seed':item['seed'],'response_A':a,'response_B':b,'record':j})
assert len(records)==72 and sum(r['method']=='named-GP additive' for r in records)==12
(root/'tca-exact-cells.json').write_text(json.dumps(records,indent=2))
lines=['# All72 TCA order cells: complete answers and unchanged raw judgments','Full exact serialized rubric/request and raw records: tca-exact-cells.json. No rescore or exclusions.']
for i,r in enumerate(records):
    j=r['record']
    lines.extend([f"## {i+1} {r['source']} {j['side']} {j['order']}", 'A: '+r['response_A'],'B: '+r['response_B'],f"Mapped effect: {j['exported_effect']}",j['raw']])
(root/'tca-grounding-input.md').write_text('\n\n'.join(lines))
print('TCA_INPUT_PASS 72cells=12source+60random; hashes checked; full supplied answers/request/rubric retained; no score edits')
