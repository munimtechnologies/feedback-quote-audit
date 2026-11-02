# Audit 7 results: with enough room to finish, AI feedback changed English learners' words more often

By MV2 of Munim, Inc. Made with AI agents working in his name. Text CC BY 4.0. Plan: [`PLAN-7.md`](PLAN-7.md)
(committed in 9890cb4 before any audit-7 feedback was generated). Counts: [`audit7-pooled.json`](audit7-pooled.json)
and the four shard reports `audit7-shard-1.json` to `audit7-shard-4.json`. No essay or feedback text is read
or published.

## The question

Audit 6 asked whether a small open model's essay feedback quotes English language learners (ELL) less
faithfully, and whether telling the model "this student is an English language learner" changes that. It got
no answer: too many replies hit its 450-token limit. Audit 7 re-ran the same test on 292 new matched pairs from
PERSUADE 2.0 (Crossley et al. 2024, CC BY 4.0) with one change, an 800-token limit. Model: Qwen2.5-1.5B-Instruct
(Q4_K_M GGUF, CPU, temperature 0). Each pair is an ELL student's essay and a non-ELL essay with the same
writing prompt and the same holistic score. Each essay got excerpt-style feedback that asks for exact excerpts:

- **yes_base**: the ELL essay, baseline prompt;
- **yes_label**: the same ELL essay, with the one label sentence added;
- **no_base**: the matched non-ELL essay, baseline prompt.

An excerpt "changes the student's words" when it can be placed in the essay but at least one word differs
(audit 6's classifier, unchanged). Rates are changed / located excerpts.

## Verdicts

| ID | Prediction | Observed | 95% CI | Verdict |
|---|---|---|---|---|
| S1 | With the baseline prompt, ELL essays' excerpts change words more often than matched non-ELL essays' | 15.82% (106 / 670) vs 9.97% (68 / 682), +5.85 pts | +1.26 to +10.41 | **held** |
| L1 | Adding the label sentence moves the ELL rate by less than 4 points | 12.64% (91 / 720) vs 15.82% (106 / 670), -3.18 pts | -6.16 to -0.31 | **inconclusive** |
| T1 | Excerpts in replies over 450 output tokens change words more often than excerpts in shorter replies | 20.73% (79 / 381) vs 11.00% (186 / 1,691), +9.74 pts | +3.40 to +16.47 | **held** |

CIs are percentile bootstraps over pairs (10,000 replicates, seeds fixed in the plan). All three comparisons
met their floors (600 located excerpts a side for S1 and L1, 150 for T1).

- **S1 held.** For this model and prompt, an ELL student's words were changed in about 1 in 6 located
  excerpts, against about 1 in 10 for a non-ELL student whose essay had the same prompt and score.
- **L1 is inconclusive.** The label sentence *lowered* the ELL rate by 3.18 points, and the whole interval is
  below zero, but the interval reaches past the -4-point edge of the band, so the plan's "less than 4 points"
  claim can be neither confirmed nor ruled out. The label left all three excerpts identical in 84 of the 215
  pairs where both ELL replies could be read (39%).
- **T1 held.** Long replies, the ones audit 6's 450-token limit cut off, changed the student's words about
  twice as often (20.7% vs 11.0%). A token limit can hide the least faithful feedback.

## How this fits audit 6

Audit 6 (pairs 1-146, 450 tokens) had S1's point estimate on the other side: -3.90 points (CI -10.57 to
+2.76, underpowered). Audit 7's +5.85 is outside that interval. Two things differ: the pairs (audit 7 starts
at pair 147) and the token limit. T1 shows that the replies a 450-token limit removes are the less faithful
ones, and audit 6 lost them unevenly by side (59 / 42 / 44 cut replies), so audit 6's estimate was probably
pulled by what it could not read. That is an explanation, not a tested result.

## Checks on the main result

- **Only pairs where all three replies could be read** (177 pairs, reported without a verdict): S1 14.20%
  (75 / 528) vs 7.56% (40 / 529), +6.64 pts (CI +2.06 to +11.21); L1 -1.54 pts (CI -4.45 to +1.18). S1 does not
  depend on the replies that never finished.
- **By holistic score** (changed / located, ELL baseline vs non-ELL): score 1 (28 pairs) 10/63 vs 5/57; score 2
  (102) 29/209 vs 26/220; score 3 (105) 41/254 vs 26/252; score 4 (51) 21/132 vs 7/135. The ELL side is higher
  at every score with more than a handful of pairs (scores 5 and 6 have 6 pairs between them).
- **Lost replies, by side:** 66 (yes_base), 44 (yes_label) and 62 (no_base) of 292 replies ran out of tokens;
  110 pairs had at least one cut reply. Finished replies needed a median of 295 / 257 / 270 tokens (95th
  percentile 584 / 565 / 597, longest 791).

## Everything else the plan said to report

| | yes_base | yes_label | no_base |
|---|---|---|---|
| calls | 292 | 292 | 292 |
| parsed | 225 | 244 | 228 |
| cut off (out of tokens) | 66 | 44 | 62 |
| excerpts | 675 | 732 | 684 |
| located | 670 | 720 | 682 |
| exact | 489 | 549 | 565 |
| format only | 75 | 80 | 48 |
| changed (near + loose) | 106 (97 + 9) | 91 (84 + 7) | 68 (66 + 2) |
| word-changed rate | 15.82% | 12.64% | 9.97% |
| tight rate | 14.48% | 11.67% | 9.68% |
| not in the essay (% of excerpts) | 0.74% | 1.64% | 0.15% |
| median excerpt words | 41 | 34 | 37 |
| seconds per call | 153.7 | 141.0 | 148.3 |

By excerpt length (changed / located), excerpts of 26+ words changed words more often than 11-25-word ones on
every side: 85/462 vs 18/180 (yes_base), 70/453 vs 18/231 (yes_label), 50/431 vs 15/209 (no_base). Excerpts of
10 words or fewer were rare (28, 36 and 42 located), so nothing can be said about short excerpts. This is
the opposite of the short-quote pattern in audits 2-4, but there the feedback chose its own quotes; here the
model was asked for 25-word excerpts and many ran longer.

## What happened during the runs

- Four shards of 160 pairs, each with a 480-minute budget fixed in advance. Shard 3 (on one machine) ran all
  160 pairs. Shards 1, 2 and 4 (on another) each had one model call that took about six hours, apparently a
  stalled host, and stopped at the budget after 47, 28 and 57 pairs. The plan's stopping rule depends only on
  time and count, so the shards were pooled as they were and not re-run after their counts were seen. The plan
  expected 450-560 pairs; 292 still met every floor.
- Earlier attempts stopped before generating any feedback: one shard because the plan was not yet public (an
  earlier commit of the plan had been held back by our own failing unit test), and two at a unit-test error in
  a test helper. The fixed tests were committed together with the plan (9890cb4), and the shards that produced
  these counts ran from that commit.
- The pooling job checked that all four shards share the same code (`audit7.py` SHA-256 `f7228826...ef87e`),
  plan (`edbcecf8...f4f4a`) and settings.

## Limits

- One small CPU model (1.5B parameters) and one prompt, not the tools schools use. The result describes this
  model only.
- S1 compares different essays, matched on writing prompt and score only. ELL essays may simply hold more
  non-standard forms for a model to "fix" while copying; the audit counts changes, it does not say why.
- The checker cannot tell a deliberate correction from a slip; no excerpt was read by a person.
- About a fifth of replies still never finished. The complete-pairs check above shows S1 does not rest on them,
  but L1 moves closer to zero on complete pairs.
- T1 compares replies, not essays: long replies may come from particular essays, and length may not be the cause.
- One greedy sample per call.

## What it means in practice

If a tool like this one writes feedback that quotes students, English learners' quotes are the ones to check
first: in this test their words were changed more often than a matched classmate's, and nothing in the
feedback marks the change. Telling the model the student is a learner did not make it worse here; if anything
it helped a little. And cutting replies short to save time hides the least faithful feedback rather than
removing it.

-- MV2, Munim, Inc., mv2@munimtech.com
