"""Uncalibrated DEV evidence, kept separate from the all-100 result rows."""
import hashlib
import html
import json
from pathlib import Path
from statistics import mean

import plotly.graph_objects as go
from tabulate import tabulate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_points(manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    points = []
    for item in manifest['artifacts']:
        generation = Path(item['generation'])
        judgments = Path(item['judgments'])
        assert sha(generation) == item['generation_sha256']
        assert sha(judgments) == item['judgments_sha256']
        data = json.loads(generation.read_text())
        js = [json.loads(line) for line in judgments.read_text().splitlines()]
        assert len(js) == 60
        assert len({(j['vignette'], j['side'], j['order']) for j in js}) == 60
        for side in ('+C', '-C'):
            rows = [j for j in js if j['side'] == side]
            assert len(rows) == 30
            effects, damages = [], []
            for j in rows:
                s = j['judgment']
                b, t = ('A', 'B') if j['order'] == 'AB' else ('B', 'A')
                effect = (s['on_axis_'+t]-s['on_axis_'+b])*(1 if side == '+C' else -1)
                assert abs(effect-j['exported_effect']) < 1e-9
                effects.append(effect)
                damages.append((j['vignette'], s['off_axis_'+t]-s['off_axis_'+b]))
            points.append(dict(method=item['method'], seed=item.get('seed'), alpha=data['fixed_alpha'], side=side,
                effect=mean(effects), damage=mean(abs(mean(d for vignette,d in damages if vignette==v)) for v in {v for v,d in damages}),
                AB=mean(j['exported_effect'] for j in rows if j['order']=='AB'),
                BA=mean(j['exported_effect'] for j in rows if j['order']=='BA'),
                judgments=str(judgments), generation=str(generation)))
    return manifest, points


def add_points(figure, points):
    for method in sorted({p['method'] for p in points}):
        for side in ('+C', '-C'):
            ps = [p for p in points if p['method']==method and p['side']==side]
            if not ps:
                continue
            random = method == 'matched random'
            figure.add_trace(go.Scatter(
                x=[p['effect'] for p in ps], y=[p['damage'] for p in ps], mode='markers',
                marker=dict(color='#777777' if random else '#a64b00', size=6 if random else 10,
                            symbol='square-open' if side=='+C' else 'diamond-open'),
                name=f'{method} {side} — uncalibrated DEV', showlegend=False,
                text=[f"alpha={p['alpha']:g}, seed={p['seed']}, AB={p['AB']:.3f}, BA={p['BA']:.3f}" for p in ps],
                hovertemplate='%{text}<br>effect=%{x:.3f}<br>damage=%{y:.3f}<extra>DEV eligibility unknown</extra>'))
    random_note = ('gray □/◇: matched random' if any(p['method']=='matched random' for p in points)
                   else 'matched random pending (0/10 seeds)')
    figure.add_annotation(x=0, y=-0.27, xref='paper', yref='paper', showarrow=False, xanchor='left',
        text=f'Brown □/◇: named-GP additive ± DEV; {random_note}. Uncalibrated; not a frontier.',
        font=dict(size=11, color='#6b3c16'))
    figure.update_layout(margin=dict(b=150))


def section(manifest, points):
    seeds = sorted({p['seed'] for p in points if p['method']=='matched random'})
    note = (f"Incomplete, uncalibrated DEV15; all measured alpha=1,2,4 doses retained. "
            f"Matched random seeds judged: {len(seeds)}/10 ({seeds}). Coherence eligibility unknown; no accepted frontier. "
            "New layer17/current-position controls are not the historical random cone. "
            "Alpha1 minus DNL had identical baseline/steered text and token IDs, but AB invented a quote and scored +1.6; "
            "BA scored 0. Raw scores are retained. AB/BA disagreements are shown, not resolved by selecting an order. "
            "This reused DEV cohort is not directly comparable to the all-100 table above; both project goals remain open.")
    headers = ['Evidence', 'Method', 'Seed', 'Alpha', 'Side', 'Effect →±', 'AB →±', 'BA →±', 'Damage ↓']
    values = [[str(i+1), p['method'], '—' if p['seed'] is None else str(p['seed']), f"{p['alpha']:g}", p['side'],
               f"{p['effect']:+.3f}", f"{p['AB']:+.3f}", f"{p['BA']:+.3f}", f"{p['damage']:.3f}"]
              for i,p in enumerate(points)]
    md = '\n## Named-GP additive DEV — incomplete\n\n'+note+'\n\n'+tabulate(values, headers, tablefmt='github', disable_numparse=True)+'\n\n'
    ht = '<h2>Named-GP additive DEV — incomplete</h2><p>'+html.escape(note)+'</p>'+tabulate(values, headers, tablefmt='html', disable_numparse=True)
    for i,p in enumerate(points):
        # Results live one level below the repository root.
        md += f"{i+1}. [Raw judgments](../{p['judgments']}) · [Responses and delivery](../{p['generation']})\n"
        ht += f"<p>{i+1}. <a href='../{html.escape(p['judgments'])}'>Raw judgments</a> · <a href='../{html.escape(p['generation'])}'>Responses and delivery</a></p>"
    return md, ht
