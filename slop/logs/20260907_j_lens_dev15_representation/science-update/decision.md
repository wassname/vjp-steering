# One proposed repair: match J-GP16's delivered norm before changing its source

PI/OpenAI Codex. Bounded independent GLM5.3Flash and KimiK3 updates completed. They received the actual pseudocode, original source messages, all75rawresponses/all120scores and unchanged rubric, not parent hypotheses or a preferred repair. Raw reports/traces are adjacent. This is an update after the earlier comprehension/independent/seminar procedure,not a fresh pilot. Kimi hit1800tokens then used the runner's one1400-token forced-answer continuation;both phases are preserved. No newGPU run.

## Independent observations

GLM:
> Averaging over 52 heterogeneous fit prompts (fiction, code, personal anecdotes) assumes one linear persona direction. This is an assumption, not shown.

Kimi:
> The comparison is confounded by dose and construct validity.

Kimi independently proposes:
> For j_gp16, match patch norm to full_residual before comparing effects, to deconfound representation from dosage.

GLM asks to inspect actual inserted norms before declaring the representation inert. This measurement ALREADY exists:target-impact.json shows medianfull+5.645744vsGP+2.754957 andfull−3.978192vsGP−1.124482 on their own trajectories. These are not equal doses despite both alpha1. Both reviewers also discuss source/task mismatch;neither establishes its causal primacy.

## Source-resolvable errors retained, not adopted

- GLM calls GP16 a16-dimensional readout;actual two normalizedGPvectors form a rank2basis. Each reconstructed vector uses up to16dictionaryatoms. No new16Dcoordinateoperator ran.
- GLM says round-trip error is unmeasured;3937actualnext-block/targetchecks and offline Gram checks oppose a delivered-coordinate bug. They do not establish semantic efficacy.
- Kimi suggests original eos==pad contamination;historical source pad248044 differs from eos248046. Replay uses exactsavedmasks and savedfinalposition=sum(mask)-1. Generation-onlypadchange occurs aftermetrology. This particular off-by-one explanation has contrary source evidence.
- Kimi suggests the symmetric2Dupdate injects coordinate-sum components. Actual delta=.5*(target−currentgap)*(B0−B1) preserves the two-coordinate sum algebraically;shared-coordinate-sum injection is not this implementation.
- Neither denialofavailability nor omissionoffakename proves rejectionofexistence. Both reports sometimes use stronger “refuses/correctly-ish” wording than CSNtext warrants.
- Recommendations for alpha/k sweeps plus a newjudge are broader than needed;do not adopt these as one experiment or change the rubric.

## Evidence-separated hypothesis/bet table

|hypothesis|for|against|next distinguishing observation|subjective nonexclusive bet|
|---|---|---|---|---:|
|GPdose is substantially smaller, confounding representation comparison|actualmedianGPminus1.124vsfull3.978;GPplus2.755vsfull5.646|fullitselfmostlyfails;normisnotsemanticdose|same-state counterfactualnormmatchedGPretainsfullpartialchallenge ornot|70%|
|Broadsource contrast misses factual-premise correction|sourcegenericmessages;14/15premisespersist in allarms|negativeinstructionexplicitlydemandscorrection;partialTCA/CSNeffect|if dosecontrolledGPstillfails, then source-construct test gainspriority|70%|
|Judgeoverstates some effects|phys01GPAB−.2/BA−5.5withsameanswernevernamesflaw|somegradedchallengeislegitimatecontinuousmetric|retainABBA/textdistinction;noalteredscore|85%|
|Actualhook/basisornewadapterbug|newresearchcode;earlierpadbug/wrappertimeoutreal|3937actualchecks,GPcomponentexact,FP64dual,identities|independentFP64normadapter/zero/signtests before nextgeneration|10%|
|Historicalmodel/batch mismatch|revisionnull,batch8→1coordsdiffer|0targetcounterfactualsignflips;smalllinearupdatechanges|notuniquelyresolvedwithoutsamebatchhistoricalreplay|15%|

## ONE selected next proposal for parent decision

A **pointwise norm-matched J-GP16 persistent intervention** on the SAME fixedDEV15,bothsigns,layer17,greedy512,pinnedmodel;no source fitting,layer search,k sweep,or rubric change. This is a dose-control repair of the comparison,not a claim that higherdosewillcorrectfiction.

At each actual GPtrajectory hiddenstateh,compute its frozen-targetGPdelta and the full-residualcounterfactualdelta on THAT SAMEh using the existingfullbasis/target. Apply the GPdelta direction with norm equal to the realizedBF16fullcounterfactualnorm. Record nominalandrealizednorms,directioncosines,zero-GPdelta/nonzero-reference exceptions,andactualforward/mask/nextblockchecks. Do not pretend this matches the originalfulltrajectory'sdosehistory. It intentionally neednotreach the oldGPtarget afterrescaling;the claimed invariant is norm/direction,notgapclamping. This must be named as a distinct diagnosticmethod.

If GPdelta exactlyzero while fullcounterfactualnonzero,do not silentlyinvent direction:recordandstopthatarm for parentdecision. Existing3937stateshavenozeroactualupdates but newtrajectoriescan. For zero-reference norm,applyzero andrecord. CPU independentFP64formula and tinyhybridalpha0/cached-call/nonfinaltests beforeGPU;actualBF16normerror recorded ratherthanassertedzero. Reusepriorbare/fullcontrols onlyafterhash/configchecks;freshalpha0identity if hookchanges.

Predictions:
1. NormmatchedGPapproachesfullpartialchallenge with similardamage:dosageexplains some priorrepresentationgap. Stillnotfullcorrectionorfrontier.
2. NormmatchedGPstillnearzero or samefiction whilefullpartialchallenge remains:representationorientation/sourceconstruct remain;nextsource-taskcontrasttest is motivated,not provennecessary.
3. HighernormGPbecomesincoherent:direction-dependentdamage confoundsnormequivalence;calibration required,notpositivecausalevidence.
4. Algebra/mask/zerodirectioncheckfails:implementation first,no behavioralinterpretation.

Cheapest boundedrun:30newtreatmentresponses (15x2signs),60ABBAjudgments,2necessaryidentityreplays;reusesexistingbaseline/full data exactly. Proposedcap$1.50,onecontainer360s,retries0,downloadviaexistingvolumeasprimaryrecoverypath. Recordstage timings/commit path to localizewrapperoverhead. This is PROPOSALONLY;noGPUauthorizedbyreviewcompletion. Parent must readandapprove. No additionalold3selectedquestiontest.

## Cost

GLMproviderreported0.003356175;Kimi0.1242618+0.1125618=0.2368236;total0.240179775under.50authorizedreviewcap. UpdatedblockreportedAPI0.60156776256. Keepwhole.50reservation untilreconciliation;globalunreserved19.78873536744 afterDEV3andreview.50allocations,failedstartup5stillreserved. Proposed1.50NOTallocatedorlaunchedbyworker.
