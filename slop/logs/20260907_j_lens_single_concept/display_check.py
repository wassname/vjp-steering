"""Check real rendered output and preserve the previous 36-point evidence."""
import json
from pathlib import Path
import sys
sys.path[:0]=['src','scripts']
import export
from statistics import mean
from vjp_steering import results
from vjp_steering.results_dev import add_points,load_points,section,sha
root=Path(__file__).parent
manifest,points=load_points(root/'manifest.json')
_,old=load_points('slop/logs/20260907_j_lens_judged_display/manifest.json')
assert len(points)==38 and points[:-2]==old
rows=results._rows();snapshot=json.dumps(rows,sort_keys=True)
f=results.plot(rows);legacy=f.to_plotly_json()['data'];add_points(f,points)
assert f.to_plotly_json()['data'][:len(legacy)]==legacy and json.dumps(rows,sort_keys=True)==snapshot
single=[t for t in f.to_plotly_json()['data'] if t.get('name','').startswith('single sycophancy GP')]
assert len(single)==2 and all(t['marker']['color']=='#176a9a' for t in single)
for p in points:
 js=[json.loads(l) for l in Path(p['judgments']).read_text().splitlines()]
 groups={}
 for j in js:
  if j['side']==p['side']:groups.setdefault(j['vignette'],[]).append(export.score_cell(j))
 assert len(groups)==15 and all(len(c)==2 for c in groups.values())
 assert abs(mean(export.signed_axis_effect(p['side'],c) for c in groups.values())-p['effect'])<1e-12
 assert abs(mean(abs(mean(v[1] for v in c)) for c in groups.values())-p['damage'])<1e-12
md,ht=section(manifest,points)
assert md in Path('results/index.md').read_text() and ht in Path('results/index.html').read_text()
results._check_equivalent(md,ht)
assert sha('data/results.csv')==json.loads((root/'comparisons.json').read_text())['summary']['primary_sha']
assert '5/10' in md and 'alpha4-only' in md and 'BA effects were -1.7 and -7.7' in md
print('SINGLE_DISPLAY_PASS',json.dumps(dict(points=len(points),prior_points_unchanged=len(old),primary_rows=len(rows),legacy_traces=len(legacy),actual_markdown_html_exact=True,distinct_blue_traces=2,primary_sha=sha('data/results.csv'))))
