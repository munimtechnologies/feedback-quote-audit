# Results, audit 5: does feedback ranked "more specific" quote the student more faithfully? (FeedEval SpecEval)

feedback-quote-audit, audit 5. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-30 from the sealed run's `speceval.json` (in this repository). Text CC BY 4.0.

**In one line:** in SpecEval, the LLM feedback almost never quotes the student at length. Only 0.60% of
71,586 distinct feedback texts contain a quote of 4 or more words that the checker finds in the essay.
Among the 519 such quotes, 6.17% change the student's words, so E1 (at most 5%) **did not hold**, narrowly:
the 95% CI is 4.10–8.30%. The other two predictions (short vs long quotes, and top-ranked vs bottom-ranked
feedback) are **underpowered** under the plan's floor of 100 quotes on each side, so neither gets a verdict.
Descriptively, feedback the specificity ranking puts on top changes words *less* often than feedback it puts at
the bottom (3.4% vs 12.2%), but that rests on 16 changed quotes and cannot carry a conclusion.

## Why this audit

Audits 1-3 measured one model on IELTS essays; audit 4 checked six models on university essays, and the two
core patterns replicated: most quotes keep the student's words, and short quotes change words more often. This
audit asks the same questions of a third dataset, plus a new one. FeedEval (Chu, Kim and Yi, ACL Findings
2026, arXiv:2601.04574) trains an evaluator of feedback **specificity** on SpecEval, a set of chosen/rejected
pairs of LLM feedback ranked by an LLM-computed score that counts the essay segments the feedback quotes. Does
the feedback the ranking prefers quote the student any more faithfully? As far as we could find (arXiv, GitHub
and web searches, 2026-10-14 to 2026-10-30), nobody had checked the quotes in SpecEval.

## What was run

- Plan: [PLAN-5.md](PLAN-5.md), committed 2026-10-30 before this pass. The sealed run's setup refused to read
  data until the public plan matched its own copy; the run recorded the plan's SHA-256 (`34ddfb6c...`).
- Data: `speceval_dataset.json` from the Google Drive folder linked in
  [github.com/BBeeChu/FeedEval](https://github.com/BBeeChu/FeedEval), SHA-256 `3d7e8852...`, identical to the
  schema probe's hash (`sha256_as_probed: true`). 41,730 records (37,557 train, 4,173 test), 10,398 essays,
  71,586 distinct (essay, feedback text) pairs. 0 records skipped; 0 essay-text conflicts. The essays come from
  ASAP/ASAP++; this audit read the file in memory for non-commercial research and republishes no essay or
  feedback text, only counts.
- Same checker and code as audits 1-4, imported and hash-checked in setup, not copied: feedback-commons v0.8.0
  checker (`d53b6b46...`), audit 1's `audit.py` at commit `0d1c75a` (`028c0d8d...`) and 1b's `explain.py` at
  commit `d298ed9` (`9f2959da...`). Code for this pass: `speceval.py`, tests in `test_speceval.py`.
- Python 3.12.15, CPU only, under 3 minutes wall for setup and run together. Unit tests passed in the sealed
  container first. 95% CIs are 10,000 bootstrap resamples over essays, paired by essay (seed
  `feedback-quote-audit-5-20261030`).

## Unit and filters (as preregistered)

A **feedback text** is one distinct `chosen` or `rejected` string for an essay. **Rank** comes from pair
membership only: **top** = only ever chosen, **bottom** = only ever rejected, **middle** = both. A **quote** is a
passage in double quotation marks on one line. It is in the **primary set** if the checker matches it to the
essay (exact, punctuation-only, or altered at word-level similarity at least 0.6), it has at least 4 words, and
no rewrite cue appears in the 60 characters before it. **Word-changed** is 1b's class: still not found after
Markdown emphasis, typography, spacing, edge punctuation, case and ellipsis are set aside. **Tight** = best
match similarity at least 0.8. **Short** = 4-6 words; **long** = 11+ words.

The pass found **14,413** double-quoted passages in 71,586 feedback texts, about one per five texts. The filters
set aside passages under four words (12,243), passages with a rewrite cue before them (11,446) and passages the
checker could not find in the essay (2,073); one passage can fail several filters, so these overlap. What
remains is the **primary set of 519 quotes**, in 433 feedback texts over 10,398 essays.

## The three predictions, exactly as planned

| test | measure | result | predicted | verdict |
|---|---|---|---|---|
| **E1** | pooled word-changed rate, all distinct feedback texts | 6.17% (32 / 519), 95% CI 4.10–8.30% | ≤ 5.0% (with ≥ 300 quotes) | **did not hold** |
| **E2** | word-changed rate, short − long quotes (paired by essay) | +4.54 pts (8.11% of 333 vs 3.57% of 56), CI −1.59 to +9.73 | > 0 | **underpowered** (56 long quotes; floor 100) |
| **E3** | word-changed rate, top-ranked − bottom-ranked feedback (paired by essay) | −8.78 pts (3.38% of 207 vs 12.16% of 74), CI −18.09 to −0.90 | not below −1.0 pt | **underpowered** (74 bottom-ranked quotes; floor 100) |

- **E1 did not hold.** The plan's rule uses the point estimate: 6.17% is above the 5.0% bound, with 519 quotes
  (floor 300). The CI includes 5%, so this is a narrow miss, not evidence that SpecEval's quotes are much worse
  than the earlier datasets. It is higher than both earlier pooled rates (IELTS/GLM-4.7 4.3%; FeedType 1.18%).
- **E2 is underpowered.** The direction matches audits 2, 3 and 4 (short quotes change words more), but with 56
  long quotes and 2 changed long quotes the plan gives no verdict, and the CI spans zero.
- **E3 is underpowered.** Had the bottom side reached 100 quotes, the plan's rule would have read "did not hold"
  (the CI's upper end, −0.90 points, is below zero): top-ranked feedback changed words less often. With 74
  bottom-ranked quotes and 9 changed ones it gets no verdict, and we do not claim one.

## By rank (no prediction beyond E3)

| rank | distinct texts | texts with a primary quote | primary quotes per 1,000 texts | primary quotes | word-changed | rate | 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|
| top (only chosen) | 29,856 | 173 (0.58%) | 6.9 | 207 | 7 | 3.38% | 1.01–5.94% |
| middle (both) | 11,874 | 196 (1.65%) | 20.0 | 238 | 16 | 6.72% | 3.73–10.04% |
| bottom (only rejected) | 29,856 | 64 (0.21%) | 2.5 | 74 | 9 | 12.16% | 5.06–21.25% |

Top-ranked texts quote the student almost three times as often as bottom-ranked ones (6.9 vs 2.5 primary
quotes per 1,000 texts), as expected if the ranking score counts quotes. Middle texts, which won one pair and
lost another, quote most of all; we do not know why, and do not resolve it. The rate ordering top < middle <
bottom is suggestive but rests on 32 changed quotes.

Observations made after seeing the results (labelled as such, not tests): top-ranked quotes are somewhat longer
(12.6% long vs 2.7% for bottom-ranked), and the plan noted that this would push top's rate down. But among short
4-6-word quotes alone the gap remains (top 4 of 128, 3.1%; middle 15 of 153, 9.8%; bottom 8 of 52, 15.4%), so
quote length alone does not explain it. These are small numbers.

## By essay set (no prediction)

| set | kind | primary quotes | word-changed | rate |
|---|---|---:|---:|---:|
| 1 | persuasive | 135 | 8 | 5.93% |
| 2 | persuasive | 72 | 10 | 13.89% |
| 3 | source-based | 111 | 5 | 4.50% |
| 4 | source-based | 97 | 4 | 4.12% |
| 5 | source-based | 65 | 4 | 6.15% |
| 6 | source-based | 39 | 1 | 2.56% |

The plan warned that in source-based sets a quote of the reading could look like a changed student quote. That
did not inflate the rate: sets 3-6 pool to 4.5% (14 / 312) against 8.7% (18 / 207) for persuasive sets 1-2.

## Tight and loose

27 of the 32 changed quotes are tight matches (similarity at least 0.8); only 5 (15.6%) are loose. That loose
share is far lower than on FeedType (34.5%) or IELTS (about half). In SpecEval a changed quote is usually a close
copy with a word altered, not a paraphrase in quotation marks. That is the kind of misquote a student is least
likely to notice.

## Honest limits and data notes

- **The primary set is small and filtered hard.** The filters were fixed in advance and imported unchanged from
  audits 1-4, which were tuned on IELTS feedback. Here 85% of quoted passages are under four words, and the
  rewrite-cue rule, whose cue list includes phrases like "for example" and "such as", sets aside 79% of
  passages. Some of those are probably genuine quotes of the student introduced by "for example". This audit
  does not count them, so its 519 quotes may not represent all of SpecEval's quoting. A follow-up could count
  them separately, with its own plan written first.
- **Only double-quoted passages are checked.** If the feedback quotes with single quotation marks, or
  paraphrases instead of quoting, those passages are invisible here. The very low quoting share (0.60% of texts)
  is a count of double-quoted, matched 4+-word passages, not a measure of how "specific" the feedback is.
- **Rank is pair membership.** The counts (29,856 top and bottom texts but 11,874 middle) show that candidates
  were not all paired in complete triples as the paper's description might suggest. "Top" and "bottom" mean
  only-chosen and only-rejected, nothing more. The score fields were not used.
- The generator is named from the paper (GPT-4o; an appendix also mentions GPT-5.1); we do not resolve this.
- The checker cannot tell a misquote from a suggested phrase that resembles the student's text; only a human
  reading a sample can, and this pass reads none and publishes none. ASAP anonymisation tokens (e.g. @PERSON1)
  count as words.

## What this means

- **Across three datasets, most feedback quotes keep the student's words**: GLM-4.7 on IELTS 95.7%, six models
  on FeedType 98.8%, SpecEval 93.8%. A small share changes the words silently, and in SpecEval most of those
  are close copies, one word off.
- **A specificity label that counts quotes is not a fidelity check.** SpecEval's ranking does prefer feedback
  that quotes more. In this data the preferred feedback also changed fewer words, but too few quotes exist to
  say so with the preregistered confidence. Anyone training on such labels should verify the quotes separately.
  The checker used here is free and offline ([quote-check](https://github.com/munimtechnologies/quote-check)).
- **Short quotes remain the risky ones** in direction (8.1% vs 3.6% here), as in audits 2-4, though this
  dataset has too few long quotes to test it.

## Deviations from the plan

None in data, method, tests or verdict rules. The within-short-quote breakdown by rank, the persuasive vs
source-based pooling and the note on the rewrite-cue filter's reach are observations made after seeing the
results, and are labelled as such.

## Reproduce

```bash
sh setup-5.sh          # fetches the pinned checker, audit.py and explain.py and the data; hash-checks all
python -m unittest -v
python speceval.py --data speceval_dataset.json --out speceval.json
```

Apache-2.0 (code), CC BY 4.0 (text). MV2, Munim, Inc., mv2@munimtech.com.
