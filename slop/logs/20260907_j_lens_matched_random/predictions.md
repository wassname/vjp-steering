# Frozen matched-random prelaunch gate

PI/OpenAI Codex. First draw per seed0–9 of CPU torch.randn(d_model,generator=torch.Generator().manual_seed(seed)), divided by g.norm()+1e-8. No orthogonalization. Layers=(17,), not historical band6–24 vectors/cone. Exact vectors in sampler.json SHA da8ff2a8442d0c59d744bba234385c3b96f5d4a54b119c6188954978140ce610. Same persistent final-position additive hook, pinned model/DEV15/prompts/greedy512 as source. Requested norms alpha*.7216137051582336 at alpha1,2,4; actual BF16 norms measured separately, not equal bitwise.

CPU: cpu.log PASS;6120signed saved-source-state cases,0zeros,actualrange.72077948–2.88795447. Actual DEV delivery remains unknown. Reuses tested realhybrid hook (source CPU alpha0 identity/nextblock/nonfinal/cleanup); each random run also checks fullmodel alpha0 token identity twice, nextblock receipt and cached sequence lengths on every call.

Counts verified in runner: 10seeds*15scenarios*2signs*3doses=900treatments;2identities/seed=20;920generations total. 1800randomABBA+120sourceABBA=1920newjudgments. Source120 complete, reportedcost.01884664, not retried; immutablealpha1scores preserved.

## Budget gate

Allocation$6, otherunreserved$3.28873536744 unchanged. Saved live pricing.html/txt from https://modal.com/pricing: H100$.001097/sec,CPU$.0000131/physicalcore/sec,memory$.00000222/GiB/sec,volumes$.09/GiB/month (freequota not counted). TimedGPU10*360*.001097=$3.9492; estimatedAPI$0.30131; remaining$1.74949 reserve. CPU/memory usage can burst beyond reservations. Pricing confirms rates but does not bound startup time/allocation/storage.

Therefore ONLY seed0 first call is launched, with $0.60 reserved for360s timedcompute+CPU/memory/startup/storage and ~$0.03judging; this is a conservative allocation, not a proven billing limit. Reconcile actual wallclock/available usage after seed0 and ask supervisor before remaining9. No automatic ten-call loop. No retries. If output times out preserve partial artifacts and stop.

Exact first command: `PYTHONUNBUFFERED=1 PYTHONPATH=src uv run --no-sync modal run scripts/scratch/j_lens_matched_random.py::launch --seed 0`.

Predictions: overlap with namedsource effects leaves transfer weak; consistent source separation across all retained doses supports further confirmation only. Random fluctuations/ABBA disagreement may be comparable to the small source effects. Delivery assertions failing localizes a harness issue, not a method result. Health failures are retained, not selected away. All dose/source prompts and fixed judge rubric unchanged. Source/tablecoherence eligibility remains unknown and no frontier will be inferred.
