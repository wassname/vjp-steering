# Named-source audit and next operator test

PI/OpenAI Codex. Parent read norm-audit.json and summary.json. Workerb7670e0c active34turns38tools,finalizingexistingaudit; no newpaidrun. BothgoalsOPEN.

## All60judgments

PlusABmean-0.08,BA-0.24,paired-0.16,offaxis0.4133,4strictreversals2ties. MinusAB+0.1667,BAapproximately0,paired+0.08333,offaxis1.1733,1strictreversal6ties. Nounfinished/roleleak/repetitionflags. DNLregression completepair andAB+2.4/BA+0.7 in named_concept_result_pending.md. These are unchangedbenchmarkmeasurements,not replaced bymanualexistencechecking.

## Actual delivery

Plus954calls,medianactualnorm0.215284,max1.283346,medianabsnormerror0.00076749,max0.00311804.53calls exceed5%relativeerror,allwithdesirednorm<=0.05329736. OneTCAdecodecalldesired3.069587e-5 rounds tozero. This doesnot establish a globaladapterfailure. Minus962calls,median2.6737826,min1.8612523,max3.5160635,maxrelativeerror0.09423%,nozeros. DNLminus69callsmedian2.9065232:regressioncannotbeexplainedbyabsentminusdelivery. Full/GPnominalsignopposition200plus/49minus is cross-representationgeometry,not automaticallywrongindexing.

## Chosen next repair hypothesis

Paper also describes additive steering h<-h+alpha*v. Currentgap-targetadapter uses source-coordinate ordering and state-dependent norm,not plain additive steering. Named-topic source success is unproven,so do not renameconcepts posthoc. Cheapestoperator test keeps these exactsources and fixedlayer/schedule but uses the raw GPconcept contrast as constant signedaddition: +C adds GP_sycophancy-GP_skepticism; -C adds itsnegative,alpha1. No full-reference norm matching or gap target. This changes ONLY operator/dose definition as a single explicit natural contrast,not token/source/layerselection. It is a newdiagnosticmethod,not equivalentdose comparison.

Beforepaidrun,compute exact rawcontrastnorm and direction fromsaved102sourceartifact,compare hypotheticalupdates with existingcalls,verify targetside mapping and independentCPUcachedalpha0 tests. If rawcomponents notsaved recover fromexistingartifact/sourceweights offline,not newsourceinference. If contrastidenticallyzero orcannotreconstruct report exactblocker; do not invent normalization/fallback. Save own-code checks: componentorder,index/reconstruction,pinvnotusedintheadditivepath,sign ofeachupdate. Thevariant removes a researchedadapter ratherthanaddinganotherbalancingterm.

Predictions:broaderintendedscoreswithlowerdamage supports state-dependentclamping/normadapteraslimitation atthissource,not proof ofnamedconcept validity. Sameweak/adverseeffect implies operatorchange insufficient; no alpha sweepfollows. Numericalzero/shape/signfailure requires own-codecorrection beforebehavior. Verysmallactualcontrast thatroundsaway makes thistestuninformative; decidefromofflineBF16currentstates BEFORElaunch,not afterpaying.

Authorize atmost1.50 afterofflinepositive-deliverycheck,32freshresponses60ABBA,fixedDEV15/pinnedmodel/layer17/currentpersistentpositions,onecontainer360s/retries0. No sourcefit/names/dictionary/layersweep. Sourceextractionmustnotrepeat. Save prelaunchpredictions+CPU output+command,incrementalpersist/pathreturn,completeaudit. Priorworker shouldfinalizehandover before newexecution if time/contextlimited.

Budget unreserved13.78873536744 beforethisreservation,12.28873536744 after1.50. APIknown0.90350845412;failedstartup5reserve intact,actualbillingunknown. This is not calibrateddosefrontier;bothfinalgoalsremainopen.
