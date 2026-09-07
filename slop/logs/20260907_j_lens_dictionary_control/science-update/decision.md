# Proposed repair: restore the paper's read-before-write intermediate check

PI/OpenAI Codex. Newly authorized bounded update completed with GLM5.3Flash and DeepSeekV4Pro, using neutralbrief,currentpseudocode,all135DEVresponses/all240ratings and actualcachedpaper/referenceexcerpts. No parent preferred repair supplied. GLMcomplete;DeepSeek3500tokenfirstcallendedinreasoning,length,thenits2200tokenforcedansweralsoendedmidsection. Preserve `follow_up_truncated`,notconsensus or a complete DeepSeek recommendation. No extra model/review/GPU call made. Totalproviderusage.08285356156under.50.

## Actual paper evidence, not a researcher paraphrase

Source https://transformer-circuits.pub/2026/workspace/index.html, cached sibling markdown with fileSHA in paper-evidence.md;unresolvedfiguremarkers preserved. ReferenceREADME identifies it as the companion code. Its sibling.gitpointer is broken,so no verifiedvendorcommit is claimed;individualsourcefilehashes recorded.

Paper source lines259–263:
> We test this using prompts in which determining the correct answer depends on inferring an unspoken intermediate concept. For each prompt, we first confirm that the intermediate concept appears in the J-lens at intermediate model layers (Figure ??). We then apply the coordinate-swap procedure described in ?? (Figure ??): we exchange (at all token positions) the lens coordinates of the intermediate concept and a chosen alternative, leaving all components of the activation outside the span of those two vectors unchanged. If the intermediate is being used downstream, the model should now produce the answer appropriate to the swapped-in concept.

Paper line213 describes concept vectors rather than diffusepersona contrasts:
> We extract concept vectors using an approach introduced in prior work : recording the residual stream activation prior to the Assistant’s response to the prompt "Tell me about {concept}", mean-subtracted over a baseline set of 100 other concepts. We then split each concept vector into two parts: a J-space component, the non-negative combination of its top k=16 J-lens vectors found by gradient pursuit, and a non-J-space component, the remainder (Figure ??, left). Notably, across concepts and workspace layers, the J-space component carries a median of only 6–7% of the concept vector's variance, with the remaining ~93% lying outside the J-space.

Check the complete surrounding paragraph in paper-evidence.md: the quotes/excerpt text, not this summary, are authoritative. Paper notes workspace loading predicts swap success and distinguishes reportable intermediate reasoning from automaticprocessing (lines297–305). Reference lens.py/hf.py transport then apply finalnormalization+unembedding for readout;W_U@J defines write-directiondictionary,not a replacement for normalizedreadout.

## What the independent reports contributed

GLM explicitly proposes:
> On the 15 DEV questions, compute the J-lens top-k readout at layer 17 for bare and steered passes and check whether the paper's predicted signature exists at all in this model

GLM also distinguishes the paper's discreteconceptsource from genericpersona averages. DeepSeek's available finalanswer identifies readversuswrite and sourceconceptversuspersona distinctions;its incompleteending cannotchooseanexperiment. Bothreportscontainmajor factualerrors,correctedbelowfromsources;their agreement is not evidence of a causalmechanism.

## Source-resolvable corrections; no silent edits to raw reviews

- The.290and.132cosines are directdictionarybasis-difference versus full and versus J-GP,notpositive/negative separation. OriginalJ-GP/fullcosine.414225889. These values do not measure side separability.
- `norm_matched_gp` is not an unknownthird-partyarm. It is the sameJ-GP basis with pointwisenormadapter,explicitlycontrasted with earlierdirect-delta runs in pseudocode. ThusGLM'sclaimthatoldJ-GPnearzeroisnotamagnitudeeffectisunsupported.
- DeepSeeklabelssteered_off_meanassteered-minus-bare;it is the treatment's absoluteoff-axisrating. Ties do not lower thenumberofscenarioidentities ordeleteobservations.
- Normmatching scales the nominalGPdirection by a positivescalar;it does not rotate that direction atfixedh. Different autoregressivehistories maychangegaps/signs;all1941newcalls hadnoGP/fullnominalsignopposition.
- Both targetdispositions exist:plus judges sycophancy,minus judges bluntness then displaynegation. The packet's onecompleteexampleprompt was minus-specific;allside-specificrawratingsremaincorrect. DeepSeek'sreasoningmistakespositive-axisratingsforbluntness underthat specimen. No evidence of an export-signbug.
- ZeroGP/nonzero-reference explicitlyraises,not silentarmomission. All30expectedtreatments/32freshrecordscomplete;zeroGPmissing-armexplanationcontradicted.
- GPvectorsW_U@Jliveinlayer-inputcoordinates,notfinalresidualcoordinates;GLM'stransport wording is incorrect. Referenceandlocalshapesdetermineorientation.

## Cheapest suggested measurement already completed on saved data

GLM asks whether sparse explainedvariance is abnormallysmall. Offlinevariance.json uses actual savedfullsignals and components, noGPU:

|dictionary|side|1-||signal-component||²/||signal||²|componentnorm²/signalnorm²|
|---|---|---:|---:|
|J-GP|+|6.3492%|6.6573%|
|J-GP|-|9.4639%|10.0040%|
|directGP|+|9.3814%|9.7828%|
|directGP|-|9.1881%|8.8579%|

These are different metrics because the greedycomponentneednotbeexactorthogonalprojection. Lowvariancealone is not evidence of failure:paperline213reports smallJ-spacevariance with strongnativecausal effects. No k change follows fromthismeasurement.

## Evidence-separated hypothesis and bet table (worker, not consensus)

|hypothesis|for|against|contrasting observation|nonexclusivebelief|
|---|---|---|---|---:|
|Task-relevant premise assessment was never verified as active/readable before choosing persona axis|current52fit+13calibrationgenericprompts;14previouslywrongDEVminusstillunambiguouslyuncorrected;paperrequiresintermediatepresence|somepartialTCAchallenge iscausal;absenceofreadoutmayreflectimperfectlens|cleanDEVcontainsregisteredassessmenttokens versusonlygeneric/tasktokens,withnativecontrolreadable|70%|
|Application/construct mismatch ratherthanbadJdictionary|directdictionaryweakminusdespiteverifiednorms;bothsourcesgeneric|one-layer/schedule/domain notexhaustive|nativeintermediatesreadablewhileDEVassessmentnot,orDEVassessmentexistsawayfromchosenreadpoint|65%|
|Ownreadout/index/finalnorm bug could invalidate concept selection|writehooktests do nottestpaperreadout;priorpadbugreal|existingreferenceapplyandcorrectedlocalreadout areavailable;no newdefectobserved|independentmanualJ→finalnorm→head disagrees withreadoutwrapper onexactstates|10%|
|Judgeinterpretation/orderconfound inflatesstrongerclaims|TCAAB'namingtheflaw' BA'omitsfabrication';med01-.3/-6|continuouspartialchallenge legitimate;notallcontrastnoise|retainratingsandtexts,separatefromnativepresence/reasoningchecks|90% for flagged interpretation|
|Unknownhistory/model|historicalrevisionnull,paddingbatch8→1|exactGPconstructionandmask/hookchecks,smalltargetshift|nativeknown-answercontrolfailsdespitecorrectreadoutcontract|15%|

## ONE next proposal selected: repair the concept-selection protocol, not another dictionary

Restore the paper's **clean read-before-write intermediate check** before choosing another steering source. This is a repair to the source-selection/measurement protocol;it is not yet a newworkingsteeringmethod. The cheapest first test is read-only and does NOT change benchmarkratings or fit on DEVoutcomes.

Proposed bounded specification for parent review:
1. Use existingpinnedmodel/lens andfixedlayer17. Read cleanprompt residuals atALLuser-tokenpositions plusfinalprefill on the existing15DEVprompts;nointervention,nochangedgeneration. Print top20 J-lenstokens perposition usingexactpapertransport→model.finalnorm→head;retainrawtokenIDsandpositions. Also report ranks for fixedsingle-tokenforms of `fake`, `fictional`, `real`, `false`, `true` selectedbytokenizationonly beforemodeloutputs. These are discovery/readoutmeasurements,not a replacementbenchmarkscore or a newsteeringbasis.
2. In the SAMEcall include first10file-order nativeprobe-swap prompts fromreferencevendor `data/experiments/probe-swap.json`,withtheirdeclaredintermediate/answer fields. Preserveall10includinguntokenizable/incorrectbaselinecases with explicitreasons;nooutcome-selectedeligibilitydenominator. Recordgreedy nexttoken/rank andcleanintermediateJ-lensrank. This nativepositivecontrol distinguishes a generallyunreadablelayer/lens from missingDEVassessmentcontent. It is not a fullnativecausalswapreproduction.
3. Own-codecheck:independentlycomputeJ@hthenfinalnormthenhead and compare againstthecanonicalreference/readoutwrapper atidenticalstates,with layerindex,shape,tokenizerpad,mask and vocabularyhashchecks. Identityofwrites is insufficient here. Ifthese disagree,stopandrepairimplementationbeforeanyconceptselection.
4. No newfit/dictionary/k/layer/dose sweep, noactive-token chosenforsteeringinthisrun,noGPU regeneration ofoldresponses andnoadditionaljudgecalls. Save fullreadoutsand sourceexampleIDs. OriginalcontinuousDEVABBAremainunchanged.

Contrasting predictions:
- Nativeintermediatesreadable/answerable whileDEVassessmenttokens notpresent:genericpersona/sourceconstruct becomesstrongerthanreadoutbug,conditionally;doesnotproveabsentlatentknowledge or J-lensfailure.
- NativeandDEVassessmentreadable,especiallyatuserpositionsbutnotfinalprefill:the source/application-point contract gainspriority;onlythenpaper'sclean-coordinateintermediateswapcanbetestedwithoutblindtokenchoice.
- NativecontrolandDEVbothunreadable:layer/lens/modeladaptation unresolved;do notinferbadpersonaorbadpaperfromthese15cases.
- Independentreadoutmismatch:owncodefirst;no semanticconclusion.

Whyselected: directlyimplements the paper's prerequisite andGLM'sreadouttest while addinga source-definednativecontrol to avoidinterpreting absentDEVtokens as lensfailure. It is cheaperandmoreattributablethananotherdictionaryvariant or blindpersona/taskrefit. Paper'scausalswapafterpresencecheckremainsa laterproposal,notbundledhere. Nativeprobe-swapdataset provenance must be copied/hashed fromreferencebeforelaunch;currentvendorcommitunknown,filehashisrequired.

Proposedcap$1inclusive,onecontainer180s/retries0,roughly25forwardpasseswithlayer17readouts andnoLLMjudge;needmodel/readoutmemorysizingbeforelaunch. Currenttask DOESNOTauthorize thisGPU;parentmustreadanddecide. If currentcorrectedreadoutartifacts alreadycontainthesereadouts,offlinehash-verifiedreuseispreferableandavoidsanypaidrun. No needtochange.1calibrationgate or targets.

## Review cost and completion

GLMcomplete.008125975. DeepSeekfirst.0647133168+forcedanswer.01001426976=.07472758656;itsoutcomeisfollow_up_truncated(exit1),notanempty/infrastructurefailure. Total.08285356156,updatedblockAPI **.89405369412**. Keepwhole.50allocationpendingledgerreconciliation;globalunreserved **15.78873536744**,priorfailedstartup5reserve intact. No furtherpaidcall orGPUrun. Parentownsacceptancereview,repairselectionapproval,andgoalclosure.
