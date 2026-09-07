# Independent local verification and handover seams

PI/OpenAI Codex. CPU tests passed twice (cpu.log,cpu-final.log); actualsource commitfc2cbfa. Fullmodal.log88lines read through EXIT0;fulljudge.log62lines read through EXIT0, all60rationales/perresponsefields and15bare+30treatment texts viewed. No failed/truncated outputs dropped. `verify.py` checks all32rawlogresponses againstartifact, all60rawlogjudgments againstJSONL, exactABBA promptresponse identities, unchangedrubric marker, singleattemptcount, 102exactsourceinputs, rank/Gram/sourcecalibration andrawpursuit reconstruction. verification.log ends EXIT_CODE0. Report validates all2026actualcalls and mapped export signs. This is local verification, not independent native reviewer acceptance.

ArtifactSHA2569b47dcb594efc67f9b3491013273106346a0afb8c32fea3a6111e6121ca34a53. Model/lens/baseline SHA in generation.json andinventory.json. SourceimplementationSHA checked against executedgitrevision by --report. Indexempty before evidencecommit; unrelatedworkingtreepreserved. RawModalstdout containsplatformcontrol/trailingwhitespace; retaincapturedbytes ratherthan normalizeevidence. CSVusesLF.

## Exact saved arrays for next owner (no additive work done here)

- `generation.json.construction.components.positive.component` and `.negative.component`: raw, UNNORMALIZED GP16 reconstruction vectors, each2560floats. `nonzero_ids`, `weights`, `dictionary_rows`, `tokens` retain their source dictionary support.
- `construction.basis`/`dual`: normalizedtwo-component geometry used in thisrun, not rawGPdifference.
- `construction.full_signals`, `full_basis`, `full_dual`, `baseline_mean`: ownnamedsource fullreference geometry.
- `construction.source_states`: all102FULL finalprefillhiddenstates; orderedtargetsfirstsycophancy/skepticism, then100baseline. `source_records` contains102renderedinputs/IDs/masks matching source-prompts.json.
- `records[].measurements[]`: actualDEVprepatch GP/fullcoordinates, norms,positions/callcounts,nextblock/roundingchecks. **Full per-step DEV hidden states are NOT saved**. Therefore exact prospectiveBF16rounding of a new rawadditive vector on everyDEVstate cannot be reconstructed fromthese coordinatesalone. Source102fullstates permit source-state roundingfeasibility only; do notlabelthat actualDEVdelivery.
- `records`30treatments,`identity_controls`2,`reused_records`75priorbridgecells. All15bare rows available fromthere withgeneratedIDs;targets in `targets` and sourcelabel `construction.calibration_label`.

No additive code/probe/GPUcalls performed afterparentcutoff. Parentfreshworker owns any furtherfeasibility/run;currentworkerends afterevidencecommit/authoritativehandoff.
