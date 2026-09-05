Read both at full size plus two crops (`/tmp/crop_origin.png`, `/tmp/crop_bottom.png`).

## Structure: preserved

Same comparison plot as the reference. All prior methods still there with the same colors and labelled final-dose ×: VJP-delta (blue), mean difference (orange), PCA (pink), per-side VJP ±C (purple), MLP-up VJP ±C (yellow), J-word ±C (green), bare diamond at origin, grey null zone, both "clean steer ->" corner annotations, "mostly side effects", "× selected/final dose". Axes identical (−4.7…4.7, 0…1.27).

Two right-edge improvements over the reference: "MLP-up VJP +C" is no longer clipped at the frame, and the "MLP-up VJP -C" / "per-side VJP -C" labels that were stacked on top of each other in the reference are now separated.

## Cyan J-lens: all measurements visible

- solid +C: short path from bare to a cyan × at ≈(0.1, 0.07)
- dotted -C: path from bare to a cyan × at ≈(−0.35, 0.31)
- rejected high-dose: pale open cyan circles scattered ≈(−0.8…0.5, 0.1–0.65)
- off-scale: 5 open ▽ at y≈1.24, x ≈ −3.3, −3.0, −1.65, −1.1, −0.3 — inside the frame, above the spine, not clipped

Both short paths ending near the origin read fine; the small effect is legible as small, not as missing data.

## Material defects

1. **Dotted−C encoding collides with the new baseline dash tails.** In the reference every baseline was solid end-to-end. In current, most baselines' final segment is dash-dot (mean difference to its × at (−1.3,1.2), VJP-delta to (−1.17,1.02), MLP-up −C, PCA, per-side −C, J-word −C, VJP-delta/mean-difference on the right at x≈3.8–4.4). So the plot now contains two broken line styles: cyan dotted meaning "−C", and everyone else's dash-dot meaning something else that the key never states. A reader applying "dotted = −C" to the orange or blue dashed tails gets a wrong reading. This is the one I'd fix.

2. **Unexplained pale dot haze.** A field of low-alpha dots in every series color sits between and off the drawn paths (densest around (−1.5…1.5, 0.1–0.45)). Nothing in the figure says what they are. They also compete with the pale cyan circles, which is the one series where "loose dots, not a frontier" is carrying meaning.

3. **Cyan is the only series with no inline label.** Every other final × has a colored text label with a leader line; both cyan × marks have none, so identifying them requires reading the top-left key and matching by color. The reference had an explicit cyan sentence ("J-lens DEV: no accepted dose; both collapse off-scale ↓"); the replacement key is more compact but pushed the identification off the marks.

Minor, not material: one pale cyan circle sits under the right edge of the white "J-word -C" label box, and another sits immediately left of the grey null-zone open circle at ≈(0.45,0.40), where the two open circles are easy to confuse at a glance.

No clipping anywhere; no text-on-text collision.

---
Files: `/workspace/2026/jspace/j-steer_pub/results/plot.png`, `/tmp/reference-plot.png`, crops `/tmp/crop_origin.png`, `/tmp/crop_bottom.png`

-- Claude Opus 5 (`claude-opus-5[1m]`), fresh-eyes visual review, no edits made
