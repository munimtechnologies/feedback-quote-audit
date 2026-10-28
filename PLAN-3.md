# Plan 3: are changed quotes genuine misquotes or near-misses, by quote length?

feedback-quote-audit, audit 3. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-28, after the results of audits 1, 1b, 2 and 2b and before this pass ran. The sealed
run's setup refuses to start until this file is public in the repository. Apache-2.0 (code), CC BY 4.0 (text).

## Why

Audit 2b ([RESULTS-2b.md](RESULTS-2b.md)) split the word-changed quotes in GLM-4.7's published IELTS
feedback into two kinds, using the checker's word-level best-match similarity:

- a **tight** change (similarity 0.8 or above) is a close copy of an essay span with a word altered --
  a genuine misquote of the student;
- a **loose** change (similarity below 0.8) matches no close span in the essay -- the signature of a
  *suggested* phrase quoted as if it were the student's, rather than a real misquote.

Across all the feedback, 1,167 of the 2,193 changed quotes (53.2%) are loose. Audit 2b measured this
split only as a whole and only to compare bands; it did not break it down by quote length. This pass
asks: **how does the tight/loose split of changed quotes vary with quote length?** That is directly
useful to [quote-check](https://github.com/munimtechnologies/quote-check), the free offline tool that
flags AI-feedback quotes that change a student's words: it says how much of the "changed words" signal
at each length is likely near-miss noise (a suggested phrase) rather than a real misquote of the essay.

This is exploratory. The predictions are informed by audits 1, 1b, 2 and 2b, but blind to the by-length
breakdown, which has never been computed or seen.

## What was already seen before this plan

Everything in RESULTS.md, RESULTS-1b.md, RESULTS-2.md, RESULTS-2b.md and their JSON, including:

- The whole-feedback tight/loose split of changed quotes: 2,193 changed, of which 1,026 tight and
  1,167 loose (53.2% loose); 50,742 primary-set quotes, 48,677 of them tight matches (band.json).
- Changes are concentrated in short quotes: audit 2 found 6.09% of 4-6-word quotes change words, vs
  1.50% of 26+-word quotes, and 71% of unmarked changes sit in 4-6-word quotes.
- Audit 2b's band tests: among tight matches the strong band still changes words more (T2 held); the
  loose share of changed did not differ by band (T3 no clear difference).

No breakdown of the tight-vs-loose split of changed quotes by quote length has been computed or seen.

## Data and code

The same pinned file as audits 1, 1b, 2 and 2b (`glm47_final.jsonl`, SHA-256 `3b5eea94...69494`), the
same checker (feedback-commons v0.8.0, SHA-256 `d53b6b46...5e04`), audit 1's `audit.py` (commit
`0d1c75a`, SHA-256 `028c0d8d...965c`) and 1b's `explain.py` (commit `d298ed9`, SHA-256
`9f2959da...14d6`). All three are imported, not copied, and hash-checked in setup. Only the feedback
field (`evaluation`). The pass must reproduce audit 2b's totals: 50,742 primary-set quotes, 48,677
tight matches, and 2,193 / 1,026 / 1,167 changed / tight-changed / loose-changed quotes. If it does
not, that is reported first.

Definitions, carried over unchanged: a quote is "matched" if `verbatim_quote_check` finds it exact,
punctuation/whitespace-only, or altered (word-level similarity of the best-matching span at least
0.6). "Primary" is matched, at least 4 words, not rewrite-cued, not a quote of the exam question.
"Changed" (word-changed) is 1b's class. "Tight" means similarity 0.8 or above; "loose" below 0.8.

Quote length is the checker's word count of the cleaned quote. Length bins (words, inclusive):
**4-6, 7-10, 11-15, 16-25, 26+**. For the predicted comparisons the bins are grouped into two strata:
**short = 4-6 words** and **long = 11 or more words** (bins 11-15, 16-25 and 26+ together). The 7-10
bin is a deliberate gap between the two strata; it still appears in the descriptive table.

## Method (fixed)

For each test the statistic is the **long-stratum rate minus the short-stratum rate**. Because the same
essay contributes quotes to both strata, its 95% CI is a percentile bootstrap **paired by essay**,
resampling essays, 10,000 resamples, seed `feedback-quote-audit-3-20261028`.

- **A1 (tight misquote rate by length).** Rate = tight changed quotes / tight matches (similarity
  >= 0.8 in both). This is how often a close, genuine quote attempt still alters a word.
- **A2 (loose share of changed by length).** Rate = loose changed quotes (similarity < 0.8) / all
  changed quotes. This is how much of the "changed" signal is a near-miss rather than a tight misquote.

## Predictions (verdict on the 95% CI of "long stratum minus short stratum")

- **A1 held** if the CI is above zero: among tight matches, long quotes alter a word more often than
  short ones. A tight match of a long quote may differ by up to ~20% of its words, so a longer genuine
  quote has more room to carry an edit, while a short tight quote is usually exact.
- **A2 held** if the CI is below zero: the loose (near-miss / suggested-phrasing) share of changed
  quotes is higher for short quotes than long ones. A short phrase crosses the 0.8 threshold with one
  or two word differences and short suggested phrases are easy to quote, so the "changed" signal on
  short quotes is expected to be more near-miss noise.

"Reversed" if the CI lies wholly on the other side of zero, otherwise "no clear difference". A test is
"underpowered" if either stratum has fewer than 100 quotes in that test's denominator.

## Also reported, with no prediction

- **R0:** the overall loose share of changed quotes across all lengths, to check it reproduces audit
  2b's 53.2%.
- A per-bin table (5 bins): quotes, tight matches, changed quotes, changed rate, tight misquote rate
  and loose share of changed, with 95% CIs on the last two. Descriptive; no verdict.

## Limits known in advance

- **The 0.8 similarity threshold is length-dependent by construction.** A 5-word quote falls below 0.8
  once two of its words differ; a 20-word quote stays tight until four or more words differ. So any
  difference in the loose share by length is partly mechanical, not only about the model's behaviour.
  A2 is reported with this caveat, and the per-bin table lets a reader see the raw counts. This is
  itself a useful caution for quote-check: a fixed similarity cutoff means different things at
  different lengths.
- Similarity is `verbatim_quote_check`'s word-level best-match ratio, a proxy for "was this really
  quoted from the essay". It cannot by itself separate a suggested phrase from a real misquote; only a
  human reading of a sample could. This pass reads no quote text.
- These are rates and counts, not a reading of any quote.
- The predictions are informed by audits 1, 1b, 2 and 2b. They are not blind to the dataset.
- One model, one exam genre, one dataset. 1b's classes inherit 1b's limits (elision read generously,
  bold taken as a marked correction).

## Outputs

`length-tight.json`: aggregate counts and rates only, with no essay or feedback text. No review sample
is drawn.
