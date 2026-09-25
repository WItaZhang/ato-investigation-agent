# ATO investigation reproduction

Status: reference text and embedded workflow diagrams reviewed. Repository renamed
to ato-investigation-agent. The previous mock execution harness remains usable.
This plan does not claim reproduction of the reference's production outcomes.

## Agreed direction

Use synthetic login data for the first end-to-end implementation. A real LLM is
required for account adjudication and evidence synthesis. Offline deterministic
tests are verification tools, not a substitute for the agent. Provider, model,
credential configuration is pending. Selected GPT-5.4 mini (2026-03-17 snapshot),
with a US$1 per-run estimated reservation budget and automatic retries disabled.
Current process has no OPENAI_API_KEY; live model validation is outstanding.

Implemented first checkpoint: scan, merge, cards, structured LLM adapter with
evidence reconciliation, full-cohort adjudication gate, basic observed-rule
diagnosis, and evidence synthesis. The smaller synthetic census is an explicit
temporary deviation from the reference's stratified sequential sampling.
Do not report this checkpoint as a completed reproduction. Remaining stages are
listed in the README and below; real-model card validation is the next gate.

## Reference requirements

1. Scan new-environment login traffic by client-specific feature dimensions.
   Count distinct accounts per day and feature value. Use days [-9, -3] as the
   seven-day baseline, excluding the two immediately preceding days. Require at
   least three days of value history and at least 50 target-day accounts.
   Require BOTH ratio and absolute increment thresholds:

   | Baseline | Ratio | Increment |
   | --- | --- | --- |
   | below 100 | 2.0 | 100 |
   | 100 to below 1,000 | 1.8 | 200 |
   | 1,000 to below 10,000 | 1.5 | 800 |
   | 10,000 and above | 1.25 | 3,000 |

2. Merge candidates using intersection size divided by the smaller cohort size.
   Add concentrated features and ablate conditions to validate necessity.
3. Filter batch registrations by registration-month and country concentration.
   Sample single-login / multi-day / same-day-repeat histories (60/30/10 target).
   Generate evidence cards; classify takeover, not takeover, or uncertain with
   evidence and reasons. Evaluate the unblocked takeover proportion in batches
   against a 30% gate. Statistical passage is determined by scripts, not the LLM.
4. Reconstruct entry, takeover, and abuse timelines against pre-window devices
   and registration devices. Report per-stage blocking and missing evidence.
5. Propose stable retrospective anchors, inspect 60-180 days of history, require
   burst ratio at least 10, and inspect 15 newly matched plus 5 baseline accounts.
   Zero observed mistakes does not establish zero population errors. Output
   proposed actions without automatically enforcing real-account changes.
6. Diagnose existing rules: actual hits first, observation-only and overridden
   actions next, then missing hits and condition-level explanations. Use rule
   versions valid at the event time. Missing factor values remain unknown.
7. Keep versioned, source-attributed knowledge entries with unique IDs, resolved
   references, and validation before accepting an updated knowledge snapshot.

## Engineering and acceptance

- Separate loading, stateless features, detection, adjudication, and orchestration.
- Store experiment values in YAML; lock dependencies with uv.
- Keep raw inputs read-only. Generated fixtures go under data/staging, computed
  artifacts under data/processed, timestamped run evidence under logs.
- Record exact configuration, metrics, logs, and stage artifacts for every run.
- Models read generated cards only; they cannot query data or execute scripts.
- Deterministic gates reconcile IDs and counts before progressing.
- Hold labels out of model inputs; evaluate benign spikes, batch registrations,
  legitimate environment changes, blocked attacks, and uncertain accounts.
- Synthetic tests establish pipeline behavior, not real-world detection accuracy.

## Unspecified details requiring explicit assumptions

- Full mobile/web dimension lists and binning definitions are absent.
- Baseline treatment of absent values, history interpretation, and threshold
  boundary conventions need confirmation. Initial scanner assumptions: seven
  calendar days with zeros for absent values; at least three nonzero baseline
  days; inclusive gates; intervals as shown above.
- Cohort overlap cutoff, refinement objective, and stopping criteria are absent.
- Confidence method, sequential error control, stratum weighting, and treatment
  of uncertain labels are unspecified. Repeated ordinary confidence intervals
  alone do not establish a valid sequential test.
- Runtime latency needs definition: the reference consumes a full target day
  despite the project's real-time title. Start with daily batch investigation.

The private reference document and its business results are not bundled here.
