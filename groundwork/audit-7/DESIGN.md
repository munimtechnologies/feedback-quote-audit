# Audit 7 design note: a powered re-test of audit 6's question

By MV2 of Munim, Inc., 2026-10-31. Made with AI agents working in his name. Text CC BY 4.0.
**A design note, not a plan.** It was written after audit 6's results ([`RESULTS-6.md`](../../RESULTS-6.md))
were published, and it is shaped by them. The plan (`PLAN-7.md`, with its code and tests) will be committed
before any new pair is generated; nothing below is a result.

## The question, again

Does telling a small open model that "the student who wrote this essay is an English language learner"
change how faithfully its feedback quotes that student (L1)? And are English learners' essays quoted less
faithfully than matched essays by other students (S1)? Audit 6 asked both on PERSUADE 2.0 and got no
answer: every verdict was "underpowered" because no side reached 300 located excerpts.

## What audit 6 showed about running it

- **Qwen2.5-1.5B can do the task; SmolLM2-1.7B cannot.** About 9 in 10 of Qwen's located excerpts kept the
  student's words. About half of SmolLM's "excerpts" were not in the essay at all, so a quote-fidelity
  question about SmolLM is mostly a question about invention. Audit 7 uses Qwen only.
- **The token limit, not the model, lost most of Qwen's data.** 145 of 438 replies (33%) were cut off at
  450 tokens and could not be read. Cut-off rates also differed by side (59 baseline vs 42 label calls on
  the same essays), so the lost replies may not be missing at random.
- **Short excerpts almost never happen with this prompt.** Asked for excerpts of at most 25 words, Qwen
  gave 16 of 4-6 words in 146 pairs. Prediction C1 (short vs long) cannot be powered with this prompt, so
  audit 7 drops it; excerpt lengths are reported descriptively.
- **Time:** about 66 seconds per call on 2 CPU threads, with long stalls when the shared machine was busy.

## The sizing probe (`probe7.py`, job `audit7-probe-v1`)

Before any new essay is spent, the probe re-runs the **first 20 pairs audit 6 already used** with the same
`audit6.py` (checked against the SHA-256 audit 6 recorded), prompt, model, seed and threads, changing only
the token limit from 450 to 1024. Greedy decoding with a fixed seed should repeat audit 6's replies, so for
each of the 60 calls it can report:

- how many tokens the reply really needed, and so the smallest limit that cuts at most 5% of replies;
- whether replies audit 6 lost to the limit now finish, and what they quote (an early look, on a few
  dozen calls, at whether the lost replies differ from the kept ones);
- whether calls that finished in audit 6 come back identical (determinism);
- seconds per pair at the new limit, and so how many pairs a 480-minute job can do.

## Intended shape of PLAN-7 (to be fixed by the probe's numbers)

- **Data:** PERSUADE 2.0 (Crossley et al. 2024, CC BY 4.0), the same matched pairs in the same salted
  order as audit 6, starting at **pair 147**, the first pair audit 6 did not reach. Pairs 1-146 are used
  by audit 6 and are not reused; 1,033 pairs remain.
- **Model and prompt:** Qwen2.5-1.5B-Instruct Q4_K_M, audit 6's system prompt, label sentence and JSON
  schema unchanged. Only the token limit changes, set from the probe.
- **Runs:** the pairs split into four disjoint shards, one sealed CPU job each with a 480-minute budget,
  then one analysis job that pools the shards. Expected about 400-500 pairs.
- **Predictions:** S1 (direction) and L1 (within plus or minus 4 points) as in audit 6, same classifier and
  bootstrap over pairs, with the located-excerpt floor raised from 300 to a number the probe shows is
  reachable (aim: about 900 per side). Rough power: at a 10% changed rate, a CI half-width under 4 points
  needs roughly 550-900 located excerpts per side, depending on how strongly excerpts from the same reply
  cluster.
- **New, descriptive:** the share of replies still cut off, by side, so any remaining loss is visible.

## Why this is new

No published work we could find measures whether a learner label in the prompt changes quote fidelity in
AI essay feedback; related work measures scores (Park et al., AIED 2026) or the content and tone of
feedback (Marked Pedagogies, arXiv 2603.12471). Audit 6 was the first attempt and was underpowered; audit 7
is its powered re-test.

-- MV2, Munim, Inc., mv2@munimtech.com
