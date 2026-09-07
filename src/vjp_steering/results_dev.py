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
        projection = item['method'] == 'sycophancy GP projection removal'
        if projection:
            assert data.get('projection_removal') and data['fixed_alpha']==1
            assert len(data['records'])==15 and len({r['scenario'] for r in data['records']})==15
            assert all(r['side']=='-C' for r in data['records'])
        expected = 30 if projection else 60
        assert len(js) == expected
        assert len({(j['vignette'], j['side'], j['order']) for j in js}) == expected
        for side in (('-C',) if projection else ('+C', '-C')):
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
            single = method == 'single sycophancy GP'
            projection = method == 'sycophancy GP projection removal'
            figure.add_trace(go.Scatter(
                x=[p['effect'] for p in ps], y=[p['damage'] for p in ps], mode='markers',
                marker=dict(color='#b00060' if projection else '#777777' if random else '#176a9a' if single else '#a64b00', size=6 if random else 10,
                            symbol='cross-open' if projection else 'square-open' if side=='+C' else 'diamond-open'),
                name=f'{method} {side} — uncalibrated DEV', showlegend=False,
                text=[('fraction1, state-dependent, not norm-matched' if projection else f"alpha={p['alpha']:g}")+f", seed={p['seed']}, AB={p['AB']:.3f}, BA={p['BA']:.3f}" for p in ps],
                hovertemplate='%{text}<br>effect=%{x:.3f}<br>damage=%{y:.3f}<extra>DEV eligibility unknown</extra>'))
    seed_count = len({p['seed'] for p in points if p['method']=='matched random'})
    random_note = (f'gray □/◇: matched random ({seed_count}/10 seeds)' if seed_count
                   else 'matched random pending (0/10 seeds)')
    single_note = ('<br>Blue □/◇: single sycophancy GP ±, alpha4 only, matched update norm.'
                   if any(p['method']=='single sycophancy GP' for p in points) else '')
    projection_note = ('<br>Magenta cross: projection removal − only, fraction1, state-dependent; NOT norm-matched to random.'
                       if any(p['method']=='sycophancy GP projection removal' for p in points) else '')
    figure.add_annotation(x=0, y=-0.27, xref='paper', yref='paper', showarrow=False, xanchor='left',
        text=f'Brown □/◇: named-GP additive ± DEV; {random_note}. Uncalibrated; not a frontier.'+single_note+projection_note,
        font=dict(size=11, color='#6b3c16'))
    figure.update_layout(margin=dict(b=170 if projection_note else 150))


def section(manifest, points):
    seeds = sorted({p['seed'] for p in points if p['method']=='matched random'})
    note = (f"Incomplete, uncalibrated DEV15; all measured alpha=1,2,4 doses retained. "
            f"Matched random seeds judged: {len(seeds)}/10 ({seeds}). Coherence eligibility unknown; no accepted frontier. "
            "New layer17/current-position controls are not the historical random cone. "
            "Alpha1 minus DNL had identical baseline/steered text and token IDs, but AB invented a quote and scored +1.6; "
            "BA scored 0. Random seed0 alpha1 minus legal-pnf03 also had identical answers but BA scored -0.3. "
            "Random seed4 CSN minus at alpha1 and alpha2 had identical text, token IDs and same-order judge requests; "
            "BA effects were -1.7 and -7.7, while AB was +0.3 at both doses. "
            "Raw scores are retained. AB/BA disagreements are shown, not resolved by selecting an order. "
            "This reused DEV cohort is not directly comparable to the all-100 table above; both project goals remain open.")
    if any(p['method']=='single sycophancy GP' for p in points):
        note += (' Single sycophancy GP is a distinct alpha4-only direction at the old alpha4 update norm, not another dose of the contrast. '
                 'Its minus mean remains adverse (+0.180); the direction change does not uniquely isolate a skepticism mechanism. '
                 'Prior TCA seed0 alpha1 minus BA also invented a baseline quote; all raw scores remain unchanged.')
    if any(p['method']=='sycophancy GP projection removal' for p in points):
        note += (' Projection removal is minus-only, fraction1 with state-dependent update norms; no plus arm was measured. '
                 'It is not norm-matched to the existing random controls. Its effect is +0.040 (AB +0.100, BA -0.020). '
                 'Change from prior constant subtraction is -0.140 = unchanged-baseline rescoring -0.283333 + steered-score change +0.143333; this is not established steering success.')
    headers = ['Evidence', 'Method', 'Seed', 'Alpha / fraction', 'Side', 'Effect →±', 'AB →±', 'BA →±', 'Damage ↓']
    values = [[str(i+1), p['method'], '—' if p['seed'] is None else str(p['seed']), 'fraction1' if p['method']=='sycophancy GP projection removal' else f"{p['alpha']:g}", p['side'],
               f"{p['effect']:+.3f}", f"{p['AB']:+.3f}", f"{p['BA']:+.3f}", f"{p['damage']:.3f}"]
              for i,p in enumerate(points)]
    md = '\n## Named-GP additive DEV — incomplete\n\n'+note+'\n\n'+tabulate(values, headers, tablefmt='github', disable_numparse=True)+'\n\n'
    ht = '<h2>Named-GP additive DEV — incomplete</h2><p>'+html.escape(note)+'</p>'+tabulate(values, headers, tablefmt='html', disable_numparse=True)
    for i,p in enumerate(points):
        # Results live one level below the repository root.
        md += f"{i+1}. [Raw judgments](../{p['judgments']}) · [Responses and delivery](../{p['generation']})\n"
        ht += f"<p>{i+1}. <a href='../{html.escape(p['judgments'])}'>Raw judgments</a> · <a href='../{html.escape(p['generation'])}'>Responses and delivery</a></p>"
    return md, ht
