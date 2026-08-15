REQUEST CHANGES.

Cannot approve: the prompt lists a file to review but does not include the content of `docs/slop/spec/20260815_public_repo.md` or the referenced files. With no tools and no pasted text, I cannot verify the spec, its checks, or the listed references.

Unverified items:

- Requirement checks and whether each fails on stated likely and silent failure modes.
- VJP math in `vjp.py` and `vjp_delta.py`.
- Use of `steering-lite`, including import/path correctness.
- Fresh-clone test behavior, hidden local dependencies, or missing data provenance.
- Four-method result plot in `render_noise_cone.py`.
- Copied code or deletable work.

Fail-closed: the review cannot confirm any of the requested properties, so implementation should not proceed on this review. Provide the spec text and relevant code/plot excerpts, or grant tool access.