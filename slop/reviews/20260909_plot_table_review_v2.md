# Fresh-eyes review v2 — plot/table endpoint fix (2026-09-09)

**Verdict: PASS.**

All four fixed endpoints now match the `results/index-dev.md` table on both PNGs, verified by pixel calibration against gridlines (x: 1033.5px+149.5/unit; y: 127.5px+685/unit):

- **Green L16 -C X (Pareto): detected at data (-0.453, 0.323)** — exactly the table's `0.453 | 0.323` under the "clean steer -> abrasive" (negative-x) -C convention; it is *not* at the old wrong (1.013, 0.223).
- **Green L16 +C X: present at (1.787, 0.375)** in both plots — visibly overlapped by the gray "null zone of random directions" text but confirmed as a clear X in a 4x zoom crop; matches table `1.787 | 0.367` (within marker half-width), not the old 0.413.
- **Blue coordinate-swap Xs: (-0.514/-0.505, 0.130) -C and (~+0.08, 0.04, overlapped by the legend text) +C**, matching table `0.513/0.130` and `0.080/0.040`.

**Colors/labels:** Green #009e73 (L16) and blue #56b4e9 (coordinate swap) are pixel-verified distinct; legend reads "J-lens coordinate swap" for blue and paths/markers are not confusable.

**Gray random region:** Caption states "descriptive reference, not a confidence interval"; random peaks are gray open circles ("gray o random peak"), only method endpoints carry colored Xs — raw random peaks are not marked as accepted.

**Minor (non-blocking):** the +C green X sits under the annotation text in both plots; readable in the dev plot but partially obscured in the Pareto plot.
