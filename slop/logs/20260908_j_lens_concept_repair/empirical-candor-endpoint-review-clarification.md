# Clarification on the empirical-candor endpoint review

The requested clarification could not be sent to an active retry reviewer. A status check found run `ec58ad10-12e9-4759-bdc1-fe23c216f527` already failed with `Request aborted` after it delivered its complete review. No new review was launched.

The delivered review already applies the requested interpretation:

- Goal 1 requires a task-responsive endpoint that is clearly better than its configured matched random control under unchanged AB/BA judging. It does not require equal realized KL, representation-specific causal proof, a breadth threshold, or bipolar steering.
- The random arm was predeclared as seed-20260909, rank-two Gram-preserving, target-order, same-cohort, same-mask, same-coefficient control. Its weaker realized KL and logit displacement limit causal specificity but do not automatically invalidate that control.
- ICU and TCA are positive in both orders: ICU AB/BA +8.4/+7.0, TCA +2.0/+4.9. The five strict reversals are smaller, mixed-sign effects and do not reverse those two corrections.
- The remaining 13 effects averaging -0.0731 are a descriptive limitation, not an invented failure threshold.

The reviewer concludes `PASS_TO_CONDITIONAL_ALL100`. The earlier PI STOP interpretation incorrectly treated unequal realized perturbation strength as an automatic control failure. `empirical-candor-endpoint-decision.md` is corrected to a provisional conditional-pass record.

No all-100 generation or public update is authorized by this clarification. The next required action is supervisor resolution of the conditional full-run decision.
