# Audit 6 results: does saying "English language learner" change how faithfully AI feedback quotes the student?

By MV2 of Munim, Inc., 2026-10-31. Made with AI agents working in his name. Text CC BY 4.0.
Plan: [`PLAN-6.md`](PLAN-6.md), committed before any audit-6 feedback was generated. Counts:
[`audit6-qwen.json`](audit6-qwen.json) and [`audit6-smollm.json`](audit6-smollm.json) (per-pair category
counts with the essay's score; no ids, no essay or feedback text). Both runs record the SHA-256 of the plan
(`1f7a2a3a...`) and of `audit6.py` (`bb582d88...`) they ran against, and their unit tests passed first.

## Short answer

**All six preregistered verdicts are "underpowered".** Neither model gave the plan's floor of 300 located
excerpts on both sides of any comparison, so none of S1, L1 or C1 gets a verdict for either model. This is
the plan working as written: the floors were fixed so that a small sample could not be read as a finding.

The two models failed the floor for different reasons, and those reasons are the clearest result:

- **Qwen2.5-1.5B quotes faithfully but runs long.** About 9 in 10 of its located excerpts keep the
  student's words, but it ignored the "at most 25 words" request (median excerpt 29-34 words), so 30-40% of
  its replies ran out of the 450-token limit before the JSON closed and could not be read. The time budget
  also stopped it at 146 of 200 pairs.
- **SmolLM2-1.7B mostly does not quote.** About half of what it labelled an excerpt copied from the essay
  could not be found in that essay at all (word-level similarity under 0.5 to any passage), and 51-61% of
  the excerpts that could be placed changed the student's words. About one excerpt in five kept the
  student's words.

## Runs

| | Qwen2.5-1.5B-Instruct (Q4_K_M) | SmolLM2-1.7B-Instruct (Q4_K_M) |
|---|---|---|
| Pairs completed | 146 (stopped by the 480-minute budget) | 200 (the maximum) |
| Pairs available | 1,179 (88 ELL essays had no match) | same |
| Calls (yes_base / yes_label / no_base) | 146 / 146 / 146 | 200 / 200 / 200 |
| Replies parsed | 87 / 104 / 100 | 191 / 192 / 193 |
| Replies cut off at 450 tokens | 59 / 42 / 44 | 9 / 7 / 6 |
| Mean seconds per call | 69.4 / 55.4 / 73.4 | 43.4 / 60.8 / 40.4 |

Both ran on 2 CPU threads on a shared machine (peak memory 1.18 GB for Qwen). A few calls took far longer
than usual (up to about 31 minutes for one call) while the machine was busy; the plan's budget counts wall
time, so this cost Qwen some pairs. The stopping rule depends only on time and count, as preregistered.

## Excerpts by side

yes_base = ELL essay, baseline prompt; yes_label = same ELL essay, prompt says the student is an English
language learner; no_base = matched non-ELL essay (same writing prompt and holistic score), baseline prompt.
Word-changed rate = (changed_near + changed_loose) / located.

| Model, side | Excerpts | Exact | Format only | Changed near | Changed loose | Not found | Located | Word-changed |
|---|---|---|---|---|---|---|---|---|
| Qwen, yes_base | 261 | 209 | 29 | 22 | 1 | 0 | 261 | 8.81% |
| Qwen, yes_label | 312 | 249 | 40 | 22 | 0 | 0 | 311 | 7.07% |
| Qwen, no_base | 300 | 241 | 20 | 35 | 3 | 1 | 299 | 12.71% |
| SmolLM, yes_base | 573 | 75 | 31 | 90 | 71 | 306 | 267 | 60.30% |
| SmolLM, yes_label | 576 | 83 | 27 | 100 | 70 | 296 | 280 | 60.71% |
| SmolLM, no_base | 579 | 126 | 24 | 85 | 71 | 273 | 306 | 50.98% |

(One Qwen yes_label excerpt was empty. No excerpt from either model used "..." to join pieces.)

## Verdicts

Differences are a minus b in percentage points, with 95% percentile bootstrap CIs over pairs (10,000
replicates; 9,464 usable for SmolLM's C1, where some resamples had no short excerpts).

| Model | ID | Prediction | a vs b (changed / located) | Diff (95% CI) | Verdict |
|---|---|---|---|---|---|
| Qwen | S1 | ELL essays' excerpts change words more than matched non-ELL essays' | 23/261 (8.81%) vs 38/299 (12.71%) | -3.90 (-10.57 to +2.76) | underpowered |
| Qwen | L1 | The label moves the ELL rate by less than 4 points | 22/311 (7.07%) vs 23/261 (8.81%) | -1.74 (-5.08 to +1.40) | underpowered |
| Qwen | C1 | Short (4-6-word) excerpts change words more than long (11+) | 1/16 (6.25%) vs 79/810 (9.75%) | -3.50 (-12.12 to +13.94) | underpowered |
| SmolLM | S1 | as above | 161/267 (60.30%) vs 156/306 (50.98%) | +9.32 (-1.04 to +19.67) | underpowered |
| SmolLM | L1 | as above | 170/280 (60.71%) vs 161/267 (60.30%) | +0.41 (-7.50 to +8.04) | underpowered |
| SmolLM | C1 | as above | 2/6 (33.33%) vs 456/765 (59.61%) | -26.27 (-63.34 to +41.75) | underpowered |

Which side fell short: S1, Qwen both sides (261 and 299), SmolLM the ELL side (267). L1, the baseline side
for both (261 and 267). C1, the short side for both (16 and 6 excerpts of 4-6 words, against a floor of
100): asked for excerpts of at most 25 words, neither model wrote short ones.

Without a verdict the point estimates are only directions to look at again, and they disagree: on S1, Qwen
leans toward ELL essays being quoted *more* faithfully, SmolLM toward less. Even had the floors been met,
neither S1 nor L1 CI would have given a clear result for either model: every S1 CI spans zero, and every L1
CI reaches past the plus-or-minus 4-point band.

## Reported without a prediction (descriptive only, no CIs)

- **Share of excerpts that keep the student's words** (exact + format only, out of all excerpts):
  Qwen 91.2% (yes_base), 92.6% (yes_label), 87.0% (no_base); SmolLM 18.5%, 19.1% and 25.9%. On SmolLM the
  ELL side has both more excerpts it could not place (53.4% vs 47.2%) and a higher changed rate among those
  it could; no test was planned for this.
- **How often the label left the three excerpts identical** (pairs where both ELL calls parsed): Qwen 35 of
  84 (42%); SmolLM 9 of 185 (5%). One added sentence changed almost every SmolLM reply, yet its
  word-changed rate on those essays moved by 0.4 points.
- **Median excerpt length**, words: Qwen 34 / 29 / 30, SmolLM 25 / 28 / 23 (yes_base / yes_label / no_base).
- **By holistic score** (changed / located; yes_base, yes_label, no_base):

| Score | Qwen pairs | Qwen | SmolLM pairs | SmolLM |
|---|---|---|---|---|
| 1 | 20 | 1/39, 3/50, 3/27 | 24 | 17/28, 14/29, 28/42 |
| 2 | 50 | 12/78, 8/102, 16/105 | 73 | 60/97, 68/98, 58/116 |
| 3 | 41 | 5/75, 6/81, 14/89 | 60 | 48/75, 38/63, 41/81 |
| 4 | 32 | 4/63, 5/72, 5/72 | 39 | 32/62, 45/82, 27/59 |
| 5 | 3 | 1/6, 0/6, 0/6 | 4 | 4/5, 5/8, 2/8 |

## Deviations from the plan

None in method: the code, prompts, models, pairs, stopping rule, classifier and comparisons ran as
committed. The only departure from what PLAN-6.md expected is in scale: it sized the run on a 10-essay probe
and did not foresee that a 450-token cap would cut off a third of Qwen's replies, or that half of SmolLM's
excerpts would not be in the essay.

## What this means

- **For the question:** audit 6 does not say whether telling these models a student is an English learner
  changes how they quote. It says the test needs more located excerpts per side than 146-200 pairs of these
  two models give: about 1.8-2.1 per pair for Qwen and 1.3-1.5 per pair for SmolLM against a floor of 300.
- **For anyone choosing a model for feedback:** the gap between the two models (about 9 in 10 excerpts
  keeping the student's words against about 1 in 5) is far larger than any ELL or label difference seen here,
  as audit 4 also found across six larger models (0.22% to 13.2% word-changed). Check the model you use;
  the free [quote-check](https://github.com/munimtechnologies/quote-check) page does this offline.
- **For audit 6b** (the label on non-ELL essays, [`groundwork/audit-6b/DESIGN.md`](groundwork/audit-6b/DESIGN.md)):
  its design reuses audit 6's pairs and the same 300-excerpt floor, so on these numbers it would almost
  certainly be underpowered too. Its plan will not be written as designed; a follow-up must first get enough
  excerpts per side, and any new design will be preregistered before it runs.

## Limits

Those stated in PLAN-6.md: two small CPU models, not the models schools use; one true label sentence; S1
compares different essays matched only on prompt and score; similarity is a proxy and no one read an
excerpt; one greedy sample per call. Add: replies cut off by the token limit are lost rather than scored, so
if cut-off replies differ from finished ones, the located excerpts are not a random sample of what the model
would have quoted.

-- MV2, Munim, Inc., mv2@munimtech.com
