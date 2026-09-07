"""Independent export-axis and legacy-preservation checks for the explicit DEV overlay."""
import argparse
import json
from pathlib import Path
import sys
sys.path[:0]=[str(Path(__file__).resolve().parents[2]/'src'),str(Path(__file__).resolve().parents[1])]
import export
from vjp_steering import results
from vjp_steering.results_dev import add_points,load_points,section,sha
from statistics import mean

parser=argparse.ArgumentParser()
parser.add_argument('--manifest',default='slop/logs/20260907_j_lens_judged_display/manifest.json')
manifest,points=load_points(parser.parse_args().manifest)
rows=results._rows();before=json.dumps(rows,sort_keys=True)
figure=results.plot(rows);traces=figure.to_plotly_json()['data']
add_points(figure,points)
assert figure.to_plotly_json()['data'][:len(traces)]==traces
assert before==json.dumps(rows,sort_keys=True)
for p in points:
    js=[json.loads(l) for l in Path(p['judgments']).read_text().splitlines()]
    by_v={}
    for j in js:
        if j['side']==p['side']:by_v.setdefault(j['vignette'],[]).append(export.score_cell(j))
    assert len(by_v)==15 and all(len(cells)==2 for cells in by_v.values())
    effect=mean(export.signed_axis_effect(p['side'],cells) for cells in by_v.values())
    damage=mean(abs(mean(c[1] for c in cells)) for cells in by_v.values())
    assert abs(p['effect']-effect)<1e-12 and abs(p['damage']-damage)<1e-12
md,ht=section(manifest,points);results._check_equivalent(md,ht)
assert sha('data/results.csv')==Path('slop/logs/20260907_j_lens_judged_display/primary-before.sha256').read_text().split()[0]
assert len(points)==sum(1 if item['method']=='sycophancy GP projection removal' else 2 for item in manifest['artifacts'])
print('DISPLAY_TEST_PASS',json.dumps({'primary_rows_unchanged':len(rows),'legacy_traces_unchanged':len(traces),'DEV_points':len(points),'export_axes_exact':True,'markdown_html_cells_exact':True,'primary_csv_sha256':sha('data/results.csv')}))
