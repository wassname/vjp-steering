"""Capture prior display, then verify only the authorized projection point was appended."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path[:0]=['src','scripts']
from vjp_steering import results,results_dev
ROOT=Path('slop/logs/20260907_j_lens_projection_removal')
MANIFEST=ROOT/'manifest.json'
PRIOR_MANIFEST=Path('slop/logs/20260907_j_lens_single_concept/manifest.json')
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--capture',action='store_true');args=p.parse_args()
m,points=results_dev.load_points(PRIOR_MANIFEST if args.capture else MANIFEST)
rows=results._rows();legacy=results.plot(rows).to_plotly_json()['data']
if args.capture:
    assert len(points)==38
    saved={'points':points,'primary_rows_hash':digest(rows),'legacy_traces_hash':digest(legacy),'row_count':len(rows),'trace_count':len(legacy),'manifest':m}
    (ROOT/'display-before.json').write_text(json.dumps(saved,indent=2)+'\n')
    print('DISPLAY_CAPTURE_PASS 38points')
else:
    before=json.loads((ROOT/'display-before.json').read_text())
    assert len(points)==39 and points[:38]==before['points']
    assert digest(rows)==before['primary_rows_hash'] and digest(legacy)==before['legacy_traces_hash']
    point=points[-1];assert point['method']=='sycophancy GP projection removal' and point['side']=='-C' and point['alpha']==1
    audit=json.loads((ROOT/'audit.json').read_text())
    for a,b in (('effect','paired'),('damage','damage'),('AB','AB'),('BA','BA')):assert abs(point[a]-audit[b])<1e-12
    md,ht=results_dev.section(m,points)
    assert md in Path('results/index.md').read_text() and ht in Path('results/index.html').read_text()
    results._check_equivalent(md,ht)
    fig=results.plot(rows);results_dev.add_points(fig,points)
    assert fig.to_plotly_json()['data'][:len(legacy)]==legacy
    assert sum(len(t['x']) for t in fig.to_plotly_json()['data'][len(legacy):])==39
    assert all(word in md for word in ('fraction1','state-dependent','not norm-matched','no plus arm','5/10'))
    (ROOT/'display-points.json').write_text(json.dumps(points,indent=2)+'\n')
    print('PROJECTION_DISPLAY_PASS',json.dumps({'prior_points_unchanged':38,'total_DEV_points':39,'primary_rows_unchanged':len(rows),'legacy_traces_unchanged':len(legacy),'new_point':point,'actual_MD_HTML_values_exact':True}))
