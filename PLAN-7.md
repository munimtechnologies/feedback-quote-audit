# Audit 7 plan: a powered re-test of audit 6 (does saying "English language learner" change how AI feedback quotes the student?)

Preregistered by MV2 of Munim, Inc. on 2026-10-31, before any audit-7 feedback was generated. Made with AI
agents working in his name. Text CC BY 4.0, code Apache-2.0. This file and `audit7.py` are committed to the
repository before the sealed runs start; each run's setup waits until both exact files are public and stops
if they never are.

## Why a second try

Audit 6 ([`PLAN-6.md`](PLAN-6.md), [`RESULTS-6.md`](RESULTS-6.md)) asked two questions on PERSUADE 2.0 and
answered neither: every verdict was "underpowered". For Qwen2.5-1.5B the cause was the token limit, not the
model: 145 of 438 replies (33%) ran out of its 450 tokens and could not be read, and the loss differed by
side (59 / 42 / 44 cut replies). The design note ([`groundwork/audit-7/DESIGN.md`](groundwork/audit-7/DESIGN.md))
sets out the re-test. No published work we could find measures quote fidelity under a student-attribute
prompt (search of 2026-10-30, repeated for the design note on 2026-10-31); related work measures scores
(Park et al., AIED 2026) or the wording of feedback (*Marked Pedagogies*, Tan, Phalen and Demszky, LAK 2026,
arXiv:2603.12471).

## What was known before writing this

- **Audit 6, Qwen (146 pairs).** Word-changed rates 8.81% (ELL essay, baseline prompt; 261 located
  excerpts), 7.07% (same essays, label prompt; 311) and 12.71% (matched non-ELL essays; 299). S1's point
  estimate went *against* its prediction (-3.90 points, CI -10.57 to +2.76) and L1's was small (-1.74,
  CI -5.08 to +1.40). Neither had a verdict. These numbers come from pairs 1-146, which audit 7 does not use.
- **The sizing probe** (`groundwork/audit-7/probe7.py`, job `audit7-probe-v1`; its counts are committed
  with this plan as `groundwork/audit-7/probe7.json`). It re-ran audit 6's first 20 pairs (60 calls) with audit 6's
  own code, prompt, model, seed and threads, changing only the limit from 450 to 1,024 tokens:
  - Determinism: all 47 calls that finished both times came back with the same token count and the same
    excerpt categories.
  - Length: finished replies needed a median of 268 tokens (90th percentile 468, 95th 536, longest 594).
    5 calls, all on the non-ELL side, still had not finished at 1,024 tokens; the same 5 were unfinished at
    every limit from 600 up, so a limit above about 600 rescues nothing more in the probe.
  - Of the 13 calls audit 6 had lost at 450 tokens, 8 now finished. Their excerpts changed the student's
    words in 4 of 24 located (16.7%), against 11 of 141 (7.8%) in calls that finished both times. This tiny,
    exploratory gap is the basis of prediction T1 below.
  - Speed: 67.6 s per call on average, 203 s per pair, about 141 pairs in 480 minutes.

## Data and pairs

PERSUADE 2.0 training CSV (Crossley et al. 2024, CC BY 4.0), SHA-256
`f61319edd8bf16a982711ea0399fad59c05afaec05cdf0767f16a2c05c467e23`, fetched and hash-checked by
`groundwork/audit-6/fetch.py`. Pairs are made by audit 6's own `make_pairs` (salt `audit6-plan-2026-10-30`,
150-700 words, the 10 audit-6 probe essays left out, each ELL essay matched to the first unused non-ELL essay
with the same writing prompt and holistic score), so the pair list is audit 6's: 1,179 pairs (the run stops
if it finds another number). **Audit 7 starts at pair 147**, the first pair audit 6's Qwen run did not reach.

**Shards.** Four disjoint shards of 160 pairs, one sealed CPU job each (2 threads): pairs 147-306, 307-466,
467-626 and 627-786. Within a shard, pairs run in their salted order.

## Model and generation

Qwen2.5-1.5B-Instruct, Q4_K_M GGUF (Apache-2.0, `91cad511`, SHA-256 `6a1a2eb6...`, pinned in
`groundwork/audit-6/models.json`), llama-cpp-python 0.3.36 CPU wheel, context 4,096, temperature 0, seed 0.
`audit7.py` imports `audit6.py` and stops unless its SHA-256 (LF) is
`bb582d88a058c02a30ff06fedbea4b0b97ea48a51b279f9328d9fd23379f63fb`, the file audit 6 ran. System prompt,
label sentence, user message, JSON schema (exactly 3 items), call order (yes_base, yes_label, no_base) and
excerpt classifier are audit 6's, unchanged. SmolLM2 is not used (about half its audit-6 excerpts were not
in the essay at all).

**The one change: at most 800 output tokens** (audit 6: 450). Reason: in the probe no finished reply needed
more than 594 tokens, and the replies that had not finished by 600 had not finished by 1,024 either; 800
leaves a third more room than the longest finished reply and spends less time on replies that never finish.

**Stopping rule, fixed now.** Each shard runs its pairs in order until all 160 are done or 480 minutes
have passed (checked before each pair). The rule depends only on time and count, never on results.

**Interruptions.** A shard stopped from outside (a machine shutdown, exit 143 or 255) is re-run unchanged
from its first pair; greedy decoding repeats the replies (47 of 47 in the probe). A shard that fails because
of a code error is re-run only after the fix is committed here, and RESULTS-7 says so. A shard that still
cannot finish is left out, and RESULTS-7 says which.

**Pooling.** Each shard writes a counts-only report. When every shard has finished or been left out, the
reports are committed here (`audit7-shard-<n>.json`) and one sealed job runs `audit7.py pool`, which checks
they share the same code, plan, settings and pair numbering, joins them in pair order and judges the
predictions with 10,000 bootstrap replicates.

## Measures

As in audit 6. Each excerpt is classified against its own essay by `audit6.classify`. **Located** = exact +
format_only + ellipsis_join + changed_near + changed_loose. **Word-changed rate** = (changed_near +
changed_loose) / located. 95% CIs are percentile bootstraps over pairs (all shards together), with seeds
`feedback-quote-audit-7-20261031-S1`, `-L1` and `-T1`.

## Predictions (fixed now; one model, so three verdicts)

- **S1 (audit 6's S1, unchanged). With the baseline prompt, excerpts from ELL students' essays change the
  student's words more often than excerpts from matched non-ELL essays.** yes_base minus no_base: "held" if
  the whole CI is above zero, "reversed" if below, otherwise "no clear difference". We keep the direction
  audit 6 preregistered even though audit 6's point estimate went the other way; this is a re-test, not a
  new guess.
- **L1 (audit 6's L1, unchanged). On the same ELL essays, adding the label sentence moves the word-changed
  rate by less than 4 points.** yes_label minus yes_base: "held" if the whole CI lies within -4.0 to +4.0
  points, "did not hold" if the whole CI lies above +4.0 or below -4.0, otherwise "inconclusive".
- **T1 (new). Excerpts in long replies (more than 450 output tokens, the length audit 6 cut off) change the
  student's words more often than excerpts in replies of at most 450 tokens**, pooled over all three calls
  of each pair. Long minus short: "held" if the whole CI is above zero, "reversed" if below, otherwise "no
  clear difference". If it holds, audit 6's lost replies were not missing at random, and a token limit can
  hide the least faithful feedback.

**Floors.** S1 and L1 need at least **600** located excerpts on each side, T1 at least **150**; below that
the verdict is "underpowered". Expected: about 110-140 pairs per shard, so 450-560 pairs, which at the
probe's 3.0 / 3.0 / 2.25 located excerpts per call is roughly 1,300-1,700 per ELL side and 1,000-1,250 on
the non-ELL side. Audit 6's CI widths suggest that at about 1,000 excerpts a side the L1 interval would be
about +/-1.7 points wide and the S1 interval about +/-3.6.

## Reported without a prediction

Per call type: calls, parsed, cut off (out of tokens), excerpts by category, located, word-changed rate,
tight rate, not-found share, median excerpt length, seconds per call; output-token distribution of finished
replies and how many exceed 450; located and changed excerpts by excerpt length (1-3, 4-6, 7-10, 11-25,
26+ words); pairs with any cut-off reply; how often the label left the three excerpts identical; S1 and L1
again on only the pairs where all three replies were readable (no verdict); changed/located per holistic
score; per shard: pairs run and why it stopped.

## Honest limits, stated in advance

- One small CPU model, not the models schools use; results describe this model and this prompt only.
- Replies that never finish are still lost. In the probe they were all on the non-ELL side, so S1's
  non-ELL side may lose more replies than the ELL sides; the cut-off counts by side and the complete-pairs
  comparison are reported so this is visible.
- One label sentence, always true to the school record. Labelling non-ELL essays as ELL is not tested.
- S1 compares different essays, matched on writing prompt and score only; ELL status comes from school
  records.
- T1 compares replies, not essays: long replies may come from particular essays, and the comparison cannot
  say whether length causes the changes.
- The checker cannot tell a deliberate correction from a slip, or a loose paraphrase from a misquote. No
  excerpt or feedback text is read or published.
- One greedy sample per call; another seed or temperature could change single outputs.

## Outputs

`audit7-shard-1.json` to `audit7-shard-4.json` and `audit7-pooled.json` (counts only: per-pair category
counts with the essay's score and pair number, no ids, no text). Results will be written up in RESULTS-7.md
and added to PREDICTIONS.md whether the predictions hold or not.

-- MV2, Munim, Inc., mv2@munimtech.com
