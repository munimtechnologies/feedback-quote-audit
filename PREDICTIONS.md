# Prediction ledger: every preregistered prediction in this repository, and how it came out

By MV2 of Munim, Inc. Made with AI agents working in his name. Text CC BY 4.0.

Each audit here wrote its predictions into a plan committed before its sealed run read any quote. This page
puts all 24 of them in one place, with the verdict exactly as its RESULTS file states it, so nobody has to
read seven reports to see the track record. Numbers are copied from the RESULTS files; where this page and a
RESULTS file disagree, the RESULTS file is right. `predictions.json` holds the same table.

## Tally

| Verdict | Count |
|---|---|
| held | 10 |
| reversed (the whole 95% CI on the opposite side) | 9 |
| did not hold (level target missed, not a direction) | 2 |
| no clear difference (CI spans zero) | 1 |
| underpowered (too few quotes for the plan's floor; no verdict) | 2 |
| **Total** | **24** |

Audits 1-3 (one model, GLM-4.7, on one IELTS dataset, including 1b and 2b) got their *direction* wrong 9
times out of 12 direction predictions (2 held, 1 no clear difference). Their other 6 predictions were levels
or ranges: 1b's five held, but 1b's plan was written after audit 1's results were known and is labelled
exploratory, and audit 1's H1 did not hold. Audit 4, on an independent dataset with six models, held all
three. Audit 5, on a third dataset, missed its level target narrowly (6.17% against a 5% bound) and had too
few quotes to test its two comparisons.
The patterns that replicated across datasets: most quotes keep the student's words, and short quotes change
words more often than long ones (tested and held in audits 2-4; same direction but underpowered in audit 5).

## Audit 1: GLM-4.7 feedback on 8,946 IELTS essays ([PREREG.md](PREREG.md), [RESULTS.md](RESULTS.md))

| ID | Prediction | Observed | Verdict |
|---|---|---|---|
| H1 | At least 95.0% of primary-set quotes are character-exact | 37.7% (19,148 / 50,742), CI 37.2-38.3% | did not hold |
| H2 | Band 7.0+ essays have a higher exact rate than band 5.5 or below | 30.8% vs 41.8%, diff +11.0 pts for the weaker band (CI +9.0 to +12.9) | reversed |
| H3 | The final feedback quotes exactly more often than the reasoning text | feedback 37.7% vs reasoning 64.8%, paired +27.0 pts for reasoning (CI +26.4 to +27.6) | reversed |

Audit 1's exact rate mostly measures formatting (bold, ellipses, curly quotes); 1b explains it.

## Follow-up 1b: where the gap comes from ([PLAN-1b.md](PLAN-1b.md), [RESULTS-1b.md](RESULTS-1b.md); exploratory)

| ID | Prediction | Observed | Verdict |
|---|---|---|---|
| P1 | After formatting steps 1-5, at least 80% of quotes match the essay | 92.1% (CI 91.9-92.3%) | held |
| P2 | Elision explains 30-70% of audit 1's "changed words" quotes | 43.8% (CI 42.2-45.4%) | held |
| P3 | With elision allowed, at most 5.0% of quotes alter the student's words | 4.3% (CI 4.1-4.5%) | held |
| P4 | At least 20% of word-altered quotes mark the change with Markdown emphasis | 34.6% (CI 32.5-36.8%) | held |
| P5 | Unmarked word changes are 1.0-4.0% of all quotes | 2.8% (CI 2.7-3.0%) | held |

## Audit 2: quote length and essay band ([PLAN-2.md](PLAN-2.md), [RESULTS-2.md](RESULTS-2.md))

| ID | Prediction | Observed | Verdict |
|---|---|---|---|
| L1 | 26+-word quotes have a higher word-changed rate than 4-6-word quotes | 1.50% vs 6.09%, diff -4.59 pts (CI -5.12 to -4.05) | reversed |
| L2 | Same, for unmarked word changes | 1.47% vs 4.55%, diff -3.09 pts (CI -3.59 to -2.58) | reversed |
| L3 | 26+-word quotes have more changed words per 100 quoted words | 0.49 vs 1.99, diff -1.50 (CI -1.71 to -1.28) | reversed |
| B1 | Band 5.5 or below has a higher length-standardised unmarked word-changed rate than band 7.0+ | 2.53% vs 4.10%, diff -1.57 pts (CI -2.41 to -0.78) | reversed |
| B2 | Same, for all word changes | 3.61% vs 6.16%, diff -2.55 pts (CI -3.47 to -1.65) | reversed |

## Audit 2b: why stronger essays get more changed quotes ([PLAN-2b.md](PLAN-2b.md), [RESULTS-2b.md](RESULTS-2b.md))

| ID | Prediction | Observed | Verdict |
|---|---|---|---|
| T1 | The weak band has more quotes set aside as marked rewrites | 49.20% vs 42.56%, diff +6.64 pts (CI +5.37 to +7.92) | held |
| T2 | The strong band changes words more often even among tight matches (similarity at least 0.8) | weak 1.69% vs strong 3.03%, diff -1.35 pts (CI -2.09 to -0.66) | held |
| T3 | A larger share of the strong band's changed quotes are loose matches | weak 54.79% vs strong 52.44%, diff +2.35 pts (CI -6.45 to +11.27) | no clear difference |

## Audit 3: genuine misquotes or near-misses, by quote length ([PLAN-3.md](PLAN-3.md), [RESULTS-3.md](RESULTS-3.md))

| ID | Prediction | Observed | Verdict |
|---|---|---|---|
| A1 | Among tight matches, long quotes alter a word more often than short ones | short 3.19% vs long 0.74%, diff -2.45 pts (CI -2.73 to -2.17) | reversed |
| A2 | Changed short quotes are loose near-misses more often than changed long quotes | short 50.11% vs long 66.33%, diff +16.22 pts for long (CI +10.16 to +22.36) | reversed |

## Audit 4: six models on FeedType / SEFORA ([PLAN-4.md](PLAN-4.md), [RESULTS-4.md](RESULTS-4.md))

| ID | Prediction | Observed | Verdict |
|---|---|---|---|
| C1 | Pooled word-changed rate, 6 models x 3 prompts, is at most 5% | 1.18% (325 / 27,462), CI 0.83-1.76% | held |
| C2 | The two small models change words more than the four larger ones | 3.85% vs 0.81%, diff +3.05 pts (CI +1.48 to +5.57) | held |
| C3 | Short (4-6-word) quotes change words more than long (11+-word) quotes | 2.29% vs 0.68%, diff +1.61 pts (CI +0.97 to +2.54) | held |

C2 held as a pool, but LearnLM's volume (21,317 quotes at 0.22%) drives it, not model size: Mistral-24B, a
larger model, has the highest single-model rate (13.2%).

## Audit 5: FeedEval's SpecEval specificity pairs ([PLAN-5.md](PLAN-5.md), [RESULTS-5.md](RESULTS-5.md))

| ID | Prediction | Observed | Verdict |
|---|---|---|---|
| E1 | Pooled word-changed rate over all distinct feedback texts is at most 5% | 6.17% (32 / 519), CI 4.10-8.30% | did not hold |
| E2 | Short (4-6-word) quotes change words more than long (11+-word) quotes | 8.11% vs 3.57%, diff +4.54 pts (CI -1.59 to +9.73); 56 long quotes | underpowered |
| E3 | Top-ranked feedback is not more faithful than bottom-ranked by more than 1 point | 3.38% vs 12.16%, diff -8.78 pts (CI -18.09 to -0.90); 74 bottom-ranked quotes | underpowered |

Only 0.60% of SpecEval's 71,586 distinct feedback texts contain a primary-set quote, so the comparisons fell
under the plan's floor of 100 quotes a side. E3's point estimate leans against the prediction (top-ranked
feedback changed fewer words), but it gets no verdict.

## What the record says

- Point and direction guesses from intuition were unreliable on a single model: in audits 1-3, nine of
  twelve direction predictions came out reversed.
- The findings that held across datasets are the useful ones for a checker: most quotes keep the student's
  words (IELTS 4.3% word-changed after formatting; FeedType 1.18%; SpecEval 6.17%), and short quotes are where
  word changes concentrate (audits 2, 3 and 4).
- Model matters more than size: per-model word-changed rates on FeedType span 0.22% to 13.2%.
- Feedback that quotes rarely gives little to test: a power floor fixed in advance is what stopped audit 5
  from over-reading 16 changed quotes.

Limits are those of each audit: double quotes only, a heuristic for suggested rewrites, and similarity as a
proxy that no counts-only pass can replace with human reading.
