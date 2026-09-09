# Rebase audit 2026-09-09: ac0fdd6 removal

## Pre / post trees
- Pre-rebase tip: `d0d7978` (52 commits ahead of origin/dev3 `1494acc`, includes ac0fdd6)
- Post-rebase tip: `3d49a8e` (after dropping ac0fdd6, push succeeded to origin/dev3)
- Rebase command: `GIT_SEQUENCE_EDITOR=/tmp/drop_ac0fdd6.sh git rebase -i 1494acc` dropping line containing ac0fdd6

## Exact diff
`git diff --stat d0d7978 3d49a8e`:
```
 .../generation.json | 6641692 -----------------
 1 file changed, 6641692 deletions(-)
```
No other files changed. The removed file is `slop/logs/20260907_j_lens_layer18_mediation/generation.json` (121.70 MB, 6,641,692 JSON lines). GitHub rejected push with `GH001: Large files detected ... 121.70 MB exceeds 100.00 MB limit`.

## What ac0fdd6 added
```
commit ac0fdd60e2e3f318bfe29141489b74dac662d26a
 Archive layer18 raw mediation generation
 Raw 127 MB generation evidence; retained locally for provenance and not pushed.
 1 file changed, 6641692 insertions(+)
 slop/logs/20260907_j_lens_layer18_mediation/generation.json
```
Same file remains available as compressed `generation.json.gz` (16 MB, under limit) at same path, tracked and pushed. No non-oversized content was accidentally dropped; verified via `git diff --stat` between pre/post and `git show --stat ac0fdd6`.

## Local recoverability (no history rewrite needed)
The blob still exists in reflog:
- `git show ac0fdd6:slop/logs/20260907_j_lens_layer18_mediation/generation.json > /tmp/recovered_layer18.json` succeeds (first bytes: layer18_mediation_v1, source_revision 764...).
- `git cat-file -p ac0fdd6` shows tree intact.
- Reflog entry `d0d7978 HEAD@{...}: commit: Fix J-lens...` preserves it before rebase.
- File not GC'd: reflog retention 90 days. To restore locally without re-adding to git: `mkdir -p .local/recovered && git show ac0fdd6:slop/logs/20260907_j_lens_layer18_mediation/generation.json > .local/recovered/generation.json` (not committed, avoids push block). The gz remains in repo for provenance.

## Verification
- `ls -lh slop/logs/20260907_j_lens_layer18_mediation/` now shows `generation.json.gz` only, no uncompressed json tracked.
- `git ls-files | grep generation.json` no longer lists the 121 MB file.
- Push now succeeds without force: `git push origin dev3` with output logged to `slop/logs/20260909_j_lens_dev/push-origin-dev3.log`.

Do not rewrite history again or force-push. Recovery is local-only.
-- PI/OpenAI
