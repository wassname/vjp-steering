We need answer user: review docs/slop/spec/20260815_public_repo.md before implementation. Need check requirements each has check failing on stated likely and silent failure modes. Check VJP math, use steering-lite, fresh-clone test, four-method result plot. Find copied code, hidden local dependency, missing data provenance, work can be deleted. Do not edit files. Return <300 words with APPROVE or REQUEST CHANGES.

We don't have tools. Need infer from user message? We need review doc but content not provided. We only have user prompt. We are supposed to read files but no tools. We must answer entirely from user message. But user asks review specific file. We don't have file content. Need maybe say unable? But instruction: no tools, answer entirely from user message. We can only know references listed. We cannot actually inspect. We need produce review? Hmm.

We must be skeptical reviewer with NO tools. Answer entirely from user message. That means we cannot read the file. We need maybe request changes due to insufficient info? But user expects review. We should not fabricate. We can state cannot verify VJP math etc because file contents not provided in prompt. But maybe we must compose review based on names? Need be honest.

Let's read prompt: "Review `docs/slop/spec/20260815_public_repo.md` before implementation. ... Do not edit files. Return fewer than 300 words with `APPROVE` or `REQUEST CHANGES`." They provided path and refs. No file content. As no tools, we cannot read. We must answer from user message. The correct response is REQUEST CHANGES because no requirements/check content provided? But maybe we need pretend? The system says "Answer entirely from the user message." So we cannot say will read. Need deliver review now. We can say CANNOT APPROVE: required file content not present, so cannot check VJP/math etc. But need output <300 with APPROVE/REQUEST CHANGES. Likely "REQUEST CHANGES: cannot review file because its content was not included in prompt." That is honest.

But perhaps the user implicitly wants us to use files from working dir? The initial says current working directory. But no tools. "You are a skeptical reviewer with NO tools. Answer entirely from user message." So yes.

We should produce concise review. We need maybe list what could not be verified. No more than 300 words. Start with REQUEST CHANGES? Need say "REQUEST CHANGES" to avoid approving unverifiable. But maybe file might be good; cannot approve without content. Provide reasons: missing plan body. Mention references listed are not content. Need mark.

Could also mention likely issues from plan names? We don't know. Don't fabricate.

Let's craft: "REQUEST CHANGES. The prompt asks to verify specific items (VJP math, steering-lite import, fresh-clone test, four-method plot, provenance, hidden deps, copy/paste) but does not include the content of docs/slop/spec/20260815_public_repo.md or referenced files. With no tools and no pasted content I cannot inspect them. Any approval would be unsupported. Please paste the spec and relevant snippets, or provide tool access. Fail-closed: checklist cannot be confirmed, and silent failure modes cannot be checked." Need maybe mention no evidence.

Could we include "I did not find copied code..."? No.

Need keep under 300.