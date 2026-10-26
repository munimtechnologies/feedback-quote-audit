# Plan 1b: why are most of GLM-4.7's quotes not character-exact?

feedback-quote-audit, follow-up to audit 1. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-26 after audit 1's results and before this pass ran. Apache-2.0 (code), CC BY 4.0 (text).

## Why, and what was already seen

Audit 1 ([RESULTS.md](RESULTS.md)) found that only 37.7% of the 50,742 primary-set quotes in GLM-4.7's
published IELTS feedback are character-exact copies of the essay, while 92.3% keep the student's words
(only punctuation, spacing or capitals differ) and 7.7% change words. Before writing this plan we had seen
those aggregates and the 30-pair review sample of changed-words quotes. In that sample about half of the
"changed words" quotes left words out with an ellipsis ("..."), which the checker counts as changed words;
about a quarter put a word in Markdown bold (a marked correction the rewrite-cue rule missed); the rest
changed the student's words without marking them. This pass measures those patterns on every quote. It
is exploratory: the predictions below are fixed before the full pass, but they are informed by the
sample, so they are not blind tests like audit 1's hypotheses.

## Data and code

The same pinned file as audit 1 (SHA-256 `3b5eea94...69494`), the same checker (feedback-commons v0.8.0)
and audit 1's own code (`audit.py` at commit `0d1c75a`, imported, not copied): the same quotes, the same
primary set (at least 4 words, no rewrite cue, not a quote of the question) and the same categories. The
pass must reproduce audit 1's totals (50,742 primary-set quotes, 19,148 exact, in `evaluation`); if it
does not, that is reported first.

## Method (fixed)

For each primary-set quote, the first step after which the quote is found in the essay as a substring
(steps are cumulative; each is applied to both quote and essay unless said otherwise):

0. exact: as audit 1.
1. emphasis: Markdown `*` and `__` removed.
2. typography: curly quotes and apostrophes made straight, the ellipsis character made "...", en/em
   dashes made "-".
3. spacing: runs of spaces and line breaks made one space, no space before , . ; : ! ? ) ] or after ( [,
   one space after , ; : ! ? when a letter follows.
4. edges (quote only): spaces, punctuation, brackets, quote marks and ellipses at the quote's two ends
   dropped.
5. case: capitals ignored.
6. elision: the quote is split at each inner ellipsis ("...", ". . .", "[...]"); every piece is found in
   the essay, in order, without overlap.

Quotes not found after step 6: "other punctuation" if audit 1 called them exact or same words (for
example a hyphen added); "elision (words)" if the pieces between ellipses are each a run of the essay's
words in order (punctuation inside differs); otherwise "word changed". A word-changed quote is "marked" if
it contains Markdown emphasis. For unmarked word-changed quotes without an ellipsis, what differs from
audit 1's closest essay passage: a negation word added or dropped (not, no, never, n't, ...); a
one-for-one word change with character similarity >= 0.6 ("spelling or form", e.g. way/ways); another
word swap; a word added or dropped. A quote can have several kinds.

Rates are pooled over quotes; 95% CIs by percentile bootstrap over essays, 10,000 resamples, seed
`feedback-quote-audit-1b-20261026` (evaluation only; the same counts for `reasoning` are descriptive).

## Predictions (evaluation field; verdict on the point estimate, CI reported)

- **P1**: after the formatting steps 1-5, at least 80% of primary-set quotes match the essay.
- **P2**: between 30% and 70% of the quotes audit 1 called "changed words" are explained by elision
  (step 6 or elision-words).
- **P3**: at most 5.0% of primary-set quotes change the student's words once elision is allowed.
- **P4**: at least 20% of those word-changed quotes are marked with Markdown emphasis.
- **P5**: unmarked word changes are between 1.0% and 4.0% of primary-set quotes.

Floors: 300 quotes for P1, P3, P5; 100 for the denominators of P2 and P4.

## Limits known in advance

- Elision is read generously: the pieces only have to appear in order, however far apart.
- Markdown emphasis inside a quote is taken as marking a correction; bold can also just highlight the
  student's own words, in which case the words would match and the quote would not be counted here.
- Change kinds are read against audit 1's closest passage, which can be off by a word at the edges.
- What was seen before this plan is stated above.

## Outputs

`explain.json` (aggregate counts only; no essay or feedback text, as in audit 1) and an unpublished
sample of up to 30 unmarked word-changed pairs for a human read, summarised in words in RESULTS-1b.md.
