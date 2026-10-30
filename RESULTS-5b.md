# Results, follow-up 5b: what the rewrite-cue filter set aside in SpecEval

feedback-quote-audit, follow-up 5b. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-30 from the sealed run's `cues.json` (in this repository). Text CC BY 4.0.

**In one line:** audit 5's rewrite filter, carried over unchanged from IELTS, threw away most of SpecEval's
genuine quoting. Three times as many matched 4+-word quotes sit behind "for example", "such as" or "e.g." (1,546)
as in audit 5's primary set (519), so G1 **held**. Those cited quotes change the student's words at 3.2%, against
6.2% for primary quotes; the difference is under 3 points but its CI reaches past the band, so G2 is
**inconclusive**. G3 is **underpowered** (96 edit-cued quotes). On primary + cited quotes together, bottom-ranked
feedback changes the student's words four times as often as top-ranked feedback (10.0% vs 2.5%), so the
exploratory G4 **held**.

## Why this follow-up

Audit 5 ([RESULTS-5.md](RESULTS-5.md)) kept only 519 of 14,413 double-quoted passages in SpecEval's feedback,
which left two of its three predictions underpowered. The rewrite-cue rule it imported from audit 1 set aside 79%
of passages, and that rule's cue list includes phrases that introduce genuine quotes of the student ("for
example", "such as", "e.g."). This pass, planned before it counted anything, splits the matched quotes by the kind
of cue in front of them. As far as we could find, no audit of AI feedback quotes has tested how its own rewrite
filter changes the measured set.

## What was run

- Plan: [PLAN-5b.md](PLAN-5b.md), committed 2026-10-30 at 03:31 UTC (commit `0bd9a27`). The sealed run's setup
  waited until the public plan matched its own copy before touching data; the run recorded the plan's SHA-256
  (`a676def6...`). The plan was written after audit 5's counts were known, so G4 is labelled exploratory.
- Data: the same `speceval_dataset.json` as audit 5, SHA-256 `3d7e8852...` (`sha256_as_probed: true`). 41,730
  records, 10,398 essays, 71,586 distinct feedback texts; 0 records skipped, 0 essay-text conflicts. Read in
  memory; only counts are published.
- Code: the feedback-commons v0.8.0 checker (`d53b6b46...`), audit 1's `audit.py` (`028c0d8d...`), 1b's
  `explain.py` (`9f2959da...`) and audit 5's `speceval.py` from commit `95028e0` (`2286209b...`), all
  hash-checked in setup. New code: `cues.py`, tests in `test_cues.py` (7 tests passed in the sealed container
  before the run).
- Python 3.12.15, CPU only, about 4 minutes for setup and run together. 95% CIs are 10,000 bootstrap resamples
  over essays, paired by essay (seed `feedback-quote-audit-5b-20261030`).

## Sets

Every quote is classified exactly as in audit 5. Only quotes the checker **matches** to the essay with **at least
4 words** are counted: 2,161 of the 14,413 passages. Each falls in one set by the rewrite cues in the 60
characters before it:

| set | rule | quotes | share of matched | feedback texts holding one |
|---|---|---:|---:|---:|
| primary | no cue (audit 5's set, unchanged) | 519 | 24.0% | 433 (0.60%) |
| cited | only "for example", "such as", "e.g." or "for instance" | 1,546 | 71.5% | 1,325 (1.85%) |
| edit-cued | any other cue ("instead", "better", "should be", ...) | 96 | 4.4% | 89 (0.12%) |
| wide | primary + cited | 2,065 | 95.6% | 1,701 (2.38%) |

Of the 1,642 matched quotes the filter set aside, 1,546 (94%) had only a citation cue in front of them.

## The four predictions, exactly as planned

| test | measure | result | predicted | verdict |
|---|---|---|---|---|
| **G1** | quotes in the cited set vs the primary set | 1,546 vs 519 | cited ≥ primary | **held** |
| **G2** | word-changed rate, cited − primary (paired by essay) | 3.23% vs 6.17%, −2.93 pts, CI −5.26 to −0.66 | whole CI within ±3.0 pts | **inconclusive** |
| **G3** | word-changed rate, edit-cued − cited (paired by essay) | 36.46% vs 3.23%, +33.22 pts, CI +24.01 to +42.61 | > 0 | **underpowered** (96 edit-cued quotes; floor 100) |
| **G4** (exploratory) | word-changed rate on wide set, bottom − top-ranked (paired by essay) | 10.03% vs 2.48%, +7.55 pts, CI +3.89 to +11.48 | > 0 | **held** |

- **G1 held.** The citation cues hid about three times as much quoting as the filter kept.
- **G2 is inconclusive.** The point estimate (−2.93 points) is inside the ±3-point band, but the CI's lower end
  (−5.26) is outside it, so the plan's rule gives neither "held" nor "did not hold". Not a verdict, but worth
  stating plainly: the CI lies wholly below zero, so if anything cited quotes changed the student's words *less*
  often than primary quotes, not more. The plan made no directional prediction here and we claim none.
- **G3 is underpowered.** Edit-cued quotes changed words in 35 of 96 cases, and 23 of those 35 (66%) are loose
  matches, which is what real suggested rewrites that resemble the student's text would look like. With 96
  quotes against a floor of 100 the plan gives no verdict, and we do not claim one.
- **G4 held, as an exploratory test.** On the wide set (2,065 quotes), feedback that only ever lost its pairs
  changed the student's words in 30 of 299 quotes; feedback that only ever won changed them in 18 of 726. The
  plan warned that if top-ranked feedback quoted longer passages, quote length alone could produce this gap; it
  did not: long (11+-word) quotes are 17.9% of top-ranked and 17.1% of bottom-ranked wide quotes. G4 reuses the
  essays and primary quotes behind audit 5's E3, so it is not an independent confirmation.

## By set (no prediction beyond G1-G3)

| set | quotes | word-changed | rate | 95% CI | short (4-6 words) | long (11+) | loose share of changed |
|---|---:|---:|---:|---:|---:|---:|---:|
| primary | 519 | 32 | 6.17% | 4.11–8.38% | 8.11% (27 / 333) | 3.57% (2 / 56) | 15.6% (5 / 32) |
| cited | 1,546 | 50 | 3.23% | 2.37–4.16% | 4.33% (37 / 855) | 2.42% (7 / 289) | 22.0% (11 / 50) |
| edit-cued | 96 | 35 | 36.46% | 27.66–45.74% | 45.95% (34 / 74) | 0.00% (0 / 5) | 65.7% (23 / 35) |
| wide | 2,065 | 82 | 3.97% | 3.14–4.88% | 5.39% (64 / 1,188) | 2.61% (9 / 345) | 19.5% (16 / 82) |

The primary CI differs slightly from audit 5's (4.10–8.30%) because this pass uses its own bootstrap seed; the
counts are identical. On the wide set, short quotes again change words more often than long ones (5.39% vs
2.61%), the same direction as audits 2-4. The plan reported this without a prediction, so it is descriptive.

## By rank (no prediction beyond G4)

| rank | distinct texts | texts with a wide quote | wide quotes per 1,000 texts | wide quotes | word-changed | rate | 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|
| top (only chosen) | 29,856 | 580 (1.94%) | 24.3 | 726 | 18 | 2.48% | 1.38–3.72% |
| middle (both) | 11,874 | 853 (7.18%) | 87.6 | 1,040 | 34 | 3.27% | 2.22–4.41% |
| bottom (only rejected) | 29,856 | 268 (0.90%) | 10.0 | 299 | 30 | 10.03% | 6.58–13.78% |

| rank | primary rate | cited rate | edit-cued rate |
|---|---:|---:|---:|
| top | 3.38% (7 / 207) | 2.12% (11 / 519) | 33.3% (12 / 36) |
| middle | 6.72% (16 / 238) | 2.24% (18 / 802) | 45.5% (20 / 44) |
| bottom | 12.16% (9 / 74) | 9.33% (21 / 225) | 18.8% (3 / 16) |

Observations made after seeing the results (labelled as such, not tests):

- The top-vs-bottom gap shows up in the cited quotes alone (2.12% vs 9.33%), which audit 5 never counted. These
  quotes come from the same feedback texts and essays, so this is a consistency check, not a replication.
- Among short 4-6-word wide quotes, the gap remains (top 14 of 414, 3.38%; bottom 20 of 164, 12.20%).
- Middle texts, which won one pair and lost another, quote the most by far (87.6 wide quotes per 1,000 texts), as
  in audit 5. We do not know why.

## Honest limits

- **The checker cannot read.** A citation cue can introduce a suggested phrase as well as a quote ("such as"
  followed by a better word choice), and an edit cue can sit next to a genuine quote. Only a human reading a
  sample could separate them; this pass reads none and publishes none.
- **G4 is exploratory.** Its direction was chosen after audit 5's underpowered E3 was known, and it shares
  essays and quotes with E3. It shows the gap is not an artefact of audit 5's small set; it does not show the
  gap generalises beyond SpecEval.
- **Rank is pair membership only**, as in audit 5; the score fields were not used. The generating model is
  named in the paper (GPT-4o; an appendix also mentions GPT-5.1), and we do not resolve this.
- Only double-quoted passages are checked; ASAP anonymisation tokens like @PERSON1 count as words.

## What this means

- **A rewrite filter tuned on one dataset can hide most of another dataset's quoting.** Audit 1's cue list,
  imported unchanged, set aside 76% of SpecEval's matched 4+-word quotes, almost all for a "for example" or
  "such as" in front of them. Anyone auditing quotes in AI feedback should treat citation phrases separately
  from edit cues and check how much each filter removes before trusting a small measured set.
- **Most SpecEval quotes keep the student's words.** On the wide set 96.0% do (3.97% change words), close to the
  other two datasets: GLM-4.7 on IELTS 95.7%, six models on FeedType 98.8%. Audit 5's 6.17% on the narrow
  primary set stands as its preregistered result.
- **In SpecEval, feedback ranked more specific is also more faithful** (exploratory): 2.5% vs 10.0% of quotes
  change the student's words. The ranking counts quotes and does not check them, so this is a correlation in
  this data, not something the label guarantees; one in forty top-ranked quotes still changes the student's
  words. Training on such labels does not replace checking the quotes.
- For [quote-check](https://github.com/munimtechnologies/quote-check), the free offline checker: quotes after
  "for example" or "such as" should be checked like any other quote, not set aside.

## Deviations from the plan

None in data, method, tests or verdict rules. The by-rank breakdown of each set, the long-quote shares by rank,
the short-quote comparison by rank and the 94% citation-only share are observations made after seeing the
results, and are labelled as such.

## Reproduce

```bash
sh setup-5b.sh         # fetches the pinned checker, audit.py, explain.py, speceval.py and the data; hash-checks all
python -m unittest -v
python cues.py --data speceval_dataset.json --out cues.json
```

Apache-2.0 (code), CC BY 4.0 (text). MV2, Munim, Inc., mv2@munimtech.com.
