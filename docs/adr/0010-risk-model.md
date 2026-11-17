# 0010: Risk classifier: ordinal score with provider effects and macro-F1 cutoffs

**Context.** The POC's random forest scored 0.35 macro-F1. Reading the data generator
showed why: the label is `bucket(0.00015·billed + 0.08·LOS + 0.05·prior + 3·provider_risk
+ N(0, 0.6))`. The provider's risk, the largest term, was not a feature, while age and
procedure code (no signal) were. The Gaussian noise caps every model: an oracle that knows
the hidden provider risk reaches only about 0.61 macro-F1.

**Decision.**
* Features: billed amount, length of stay, prior claims and `provider_id`. The provider's
  hidden `risk_baseline` is never used: a payer cannot observe it. The model learns a
  regularized per-provider effect from the provider's past reviewed claims, and providers
  never seen in training get the average effect.
* Model: multinomial logistic regression (correctly specified for a noisy linear score),
  collapsed into an expected ordinal risk score; Low/Medium/High cutoffs are tuned for
  macro-F1 on out-of-fold scores so they never fit the rows they are evaluated on.
* Evaluation: 5-fold cross-validated macro-F1 (mean and std) is the headline metric, next
  to the single 20% holdout (noisy at 300 rows) and, on synthetic data, the oracle ceiling
  computed on the same folds. Training fails below `MIN_MACRO_F1`.

**Results** (1,500 claims): CV macro-F1 0.602 ± 0.023, oracle 0.607; holdout 0.566,
oracle on that split 0.550. Larger datasets (3,000 / 6,000 claims) do not raise it
meaningfully, confirming that the remaining error is label noise, not data volume.

**Consequences.** Risk predictions now depend on provider history, so the out-of-distribution
profile includes `provider_id`: a claim from a provider with no history is flagged and the
policy guardrail will not auto-approve it. Retraining keeps provider effects current; a
provider's behaviour change shows up after the next training run.
