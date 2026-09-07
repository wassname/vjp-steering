# Verification and evidence map

PI/OpenAI Codex. Generation source c4afe23. Exact executed script bytes and every imported diagnostic dependency match generation.json SHA fields. ArtifactSHA21b845cd60399fa1587dffd9a6966408d41caacd1a8060f526ccfea2e3183f6b. ReferenceDEV SHA b5ebc369ad048844e64456e1949206af0450383f40c33f891f27b9a47727c985;matchedGP SHA f980ba598b72030c5f798042ac19cbdffab032131d8259a50f351b4bac946c6c.

Reproduction commands:
- `OMP_NUM_THREADS=1 PYTHONPATH=src uv run --no-sync scripts/scratch/j_lens_dictionary_control.py --self-test`
- `PYTHONPATH=src uv run --no-sync scripts/scratch/j_lens_dictionary_control.py --report slop/logs/20260907_j_lens_dictionary_control`

Additional independent check in verification.log ran Python using json/hashlib/subprocess/torch, separate from report():
1. Expected set={(baseline scenario,side) for15baseline scenarios x2sides};compare exact30treatmentkeys.
2. Check60unique(vignette,condition,order) judgekeys,methoddirect_dictionary_gp and unchangedrubricv7.
3. Parse32DICTIONARY_RESPONSE loglines and fieldwise match text/rendered/identitymarker against30treatments+2identities.
4. Rehash each imported dependency path and compare artifactstoredSHA.
5. Reconstruct each of2components inFP64 as savednonzeroweights @ savedselecteddictionaryrows;compare savedcomponent andnormalizedbasis(atol1e-6,rtol1e-5).
6. ComputeFP64dual=solve(B@B.T,B);compare saveddual(atol1e-6,rtol1e-5),rank2.
7. Forall39source states,computeFP64coords=H@D.T;compare allstoredcoordinates(atol1e-5,rtol1e-5),and each13rowmean gapto owncontroltarget(<1e-5).
Output: `DICTIONARY_INDEPENDENT_PASS coverage30 identities2 log32 judgment_keys60 reconstructed_components2 source_coordinate_rows39 hashes_exact=true`.

Actualconstructionvalues:positive/negative16nonzeros,componentreconstructionerror2.3836e-8/2.9317e-8;dualGrammax6.8764e-8. No dictionarysupport truncation or frozenfull-targetchange. Summarycounts1941treatment+110identity;925plus/1016minus;no nominalGP/fullsignopposition. Per-callnominal andrealizednorms/coords preservedsteps.csv;full masks/inputs inartifact.

Logs read completely: modal81capturedlines;judge62lines (60raw request/response JSON lines),including all60evidence rationales;cpu/cpu-final/recovery/report/verificationcomplete. All32freshoutputtextsreadplus105prioroutputs in3scenariochunks;all240per-orderscoresread. Full newjudgerawprompts repeat unchangedrubric and actualpair;no hidden dropped attempts. `run` metadata retains importedhelperlabelnorm-matched-gp16-dev15;correctmethod/condition/source disambiguate newcontrol,not silently relabeled.

Whitespace policy: generated CSV uses LF. RawModal ANSI/progress/trailing spaces retained ratherthanmodifyingprimaryevidence. Source diff check passed beforelaunch;final indexempty checked separately. Parent-owned handovers/dirtyfiles untouched. Native final acceptance review remains parent-owned;approvedpreflight is parentassertion,not inventedreviewtext.
