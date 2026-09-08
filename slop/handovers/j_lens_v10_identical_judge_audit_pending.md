# Identical DNL judge audit

PI/OpenAI Codex. No further paidcalls until audit completes. Worker9b56f8bd owns full audit/finalization; nativecompletionactive.

Parent inspected exact serialized savedrequests andrawresponses in additive_concepts/judgments.jsonl. Both DNLminus requests contain the SAME complete response under A andB. Parentjq compares generation treatment vs reusedbaseline text: text_equal=true. Workerreported generatedIDsidentical; independent key/schemainspection confirms generated_ids exists onboth;worker mustsave explicitIDequality output.

AB cachekey6adc50d10d030c011c9b074c3f98e913dec1aa5954641e80d2cda18941512bf3. Rawjudge invents "you might check the department's records" in B,notpresent in either suppliedanswer. Rawon_axisA4.8/B3.2,offA0.2/B1.1; mappedminus+1.6.

BA cachekey5755f672209fc66ec7f6483c3fcde1e352b873b63a11a8e90a5c2b6be7f32dd5. Rawjudge recognizes verbatimrepetition,onA4.8/B4.8,offA0.2/B0.2; mappedminus0.

scripts/judge.py108-119 hashes bare/steered/prompt/answer_key/target/rubric/model/order/pass. DifferentABBAkeys are expected despite identicalserializedprompt becauseorderincluded. Parent has notyet independentlyrecomputedbothkeys; worker mustverifyactualrequestassembly/cachemapping and no stale-resultreuse. FINAL BOUNDED DECISION afterparentreadjudge-identity.log EXIT0: all60promptreconstructions andcachekeys exact,singleattempt each,DNLtext+tokenIDs+serializedABBAprompts identical,offlinejudge_oneclientfixture passes. Judgehallucination is supported; no harnessswap/cachelookupdefect found. HTTPwire/providerrequestIDs were not captured,so this is exactlocalrequest reconstruction,not provider-wireproof. No scoreoverwrite, no rubricchange, no rejudge toseekpreferredoutcome.

KnownAPInew.00941588 withinexisting1.50allocation;blocksubtotal.91292433412. Unreserved12.28873536744,failedstartup5reserveunknowninvoice. Bothgoalsopen. Nextaction readcompleted equality/key/requestaudit andrecordfinalvaliditydecision; rawscore remains but cannotconstitute evidence of differingbehavior onidenticaloutputs.
