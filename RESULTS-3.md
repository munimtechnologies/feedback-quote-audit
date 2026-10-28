# Results, audit 3: are changed quotes genuine misquotes or near-misses, by quote length?

feedback-quote-audit, audit 3. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-28 from the sealed run's `length-tight.json` (in this repository). Text CC BY 4.0.

**In one line:** both predictions came out reversed. Genuine misquotes (a close copy of the essay with a
word altered) are concentrated in short quotes: 3.19% of tight 4-6-word quotes against 0.74% of tight
quotes of 11 or more words (A1 reversed). And the rarer changed long quotes are *more* often loose
near-misses, not less: 66.3% of changed 11+-word quotes against 50.1% of changed 4-6-word quotes (A2
reversed). The fixed 0.8 similarity cutoff pushes both measures towards the predicted directions, so this
mechanical effect cannot explain either reversal.

## What was run

- Plan: [PLAN-3.md](PLAN-3.md), committed at 2026-10-28 08:19:23 UTC (commit `68b894e`), after audits 1,
  1b, 2 and 2b and before this pass. The sealed run's setup checked that the public plan was identical to
  the one it held before reading any data. The run started at 16:53:34 UTC, about 8.5 hours after the
  commit. `length-tight.json` records the plan's SHA-256 (`dabd79b7...`).
- Same data and code as audits 1, 1b, 2 and 2b: `glm47_final.jsonl` (SHA-256 `3b5eea94...69494`), checker
  feedback-commons v0.8.0 (`d53b6b46...`), audit 1's `audit.py` at commit `0d1c75a` (`028c0d8d...`) and
  1b's `explain.py` at commit `d298ed9` (`9f2959da...`). All were imported, not copied, and hash-checked in
  setup.
- The pass reproduced every audit 2b total: 50,742 primary-set feedback quotes, 48,677 tight matches, and
  2,193 / 1,026 / 1,167 changed / tight-changed / loose-changed quotes (`consistent_with_earlier: true`).
- Python 3.12.15, CPU only, 29 minutes, peak memory 0.54 GB. Unit tests passed in the sealed container
  before the run. 95% CIs come from 10,000 bootstrap resamples over essays, paired by essay for the two
  tests because one essay contributes quotes to both strata (seed `feedback-quote-audit-3-20261028`).
- Only counts are published. No essay or feedback text appears here or in `length-tight.json`, and no
  review sample was drawn in this pass.

## The two tests (short = 4-6 words; long = 11 words or more)

A quote is "primary" if the checker matches it to the essay (exact, punctuation-only, or altered with
word-level similarity at least 0.6), it is at least 4 words long, and it is not a marked rewrite or a
quote of the exam question. "Changed" is 1b's word-changed class. "Tight" means the best match in the
essay has word-level similarity 0.8 or above; "loose" means below 0.8. The 7-10-word bin is a deliberate
gap between the strata and appears only in the table further down.

| test | short (4-6 words) | long (11+ words) | long − short (95% CI) | predicted | verdict |
|---|---:|---:|---:|---|---|
| A1 changed among tight matches (sim ≥ 0.8) | 3.19% (681 / 21,320) | 0.74% (99 / 13,345) | −2.45 pts (−2.73 to −2.17) | long higher | **reversed** |
| A2 loose share of changed quotes (sim < 0.8 / all changed) | 50.11% (684 / 1,365) | 66.33% (195 / 294) | +16.22 pts (+10.16 to +22.36) | short higher | **reversed** |

No test was underpowered; the smallest stratum denominator is the 294 changed long quotes in A2 (floor
100). The verdict rule is the one fixed in the plan: "held" if the whole 95% CI falls on the predicted side
of zero, "reversed" if it falls wholly on the other side, otherwise "no clear difference".

## Predictions, exactly as planned

- **A1 reversed.** The plan predicted that a tight long quote, which can differ from the essay in up to
  about a fifth of its words and still count as tight, would carry an altered word more often than a tight
  short quote. The opposite: 3.19% of tight 4-6-word quotes alter a word, against 0.74% of tight quotes of
  11 or more words, a difference of −2.45 points (95% CI −2.73 to −2.17). When the model makes a close,
  genuine attempt to quote a long passage, it almost always keeps every word.
- **A2 reversed.** The plan predicted that the "changed" signal on short quotes would be more often a loose
  near-miss (a suggested phrase quoted as if it were the student's), because a short phrase drops below 0.8
  after one or two word differences. The opposite: 50.11% of changed short quotes are loose, against 66.33%
  of changed long quotes, a difference of +16.22 points (+10.16 to +22.36). When a long quote does change
  the student's words, two times in three it is not a close copy of any span in the essay.

## Also reported, with no prediction

- **R0, overall loose share of changed quotes.** 53.21% (1,167 / 2,193), reproducing audit 2b's 53.2%.
- **By length (descriptive, no verdict).** CIs are 95% bootstrap intervals over essays.

| quote length (words) | quotes | tight matches | changed | changed rate | changed among tight (95% CI) | loose share of changed (95% CI) |
|---|---:|---:|---:|---:|---:|---:|
| 4-6 | 22,413 | 21,320 | 1,365 | 6.09% | 3.19% (2.95 to 3.44) | 50.1% (47.4 to 52.8) |
| 7-10 | 14,636 | 14,012 | 534 | 3.65% | 1.76% (1.53 to 1.99) | 53.9% (49.7 to 58.2) |
| 11-15 | 5,890 | 5,679 | 158 | 2.68% | 1.11% (0.84 to 1.39) | 60.1% (52.3 to 67.8) |
| 16-25 | 4,800 | 4,702 | 91 | 1.90% | 0.43% (0.25 to 0.62) | 78.0% (69.2 to 86.8) |
| 26+ | 3,003 | 2,964 | 45 | 1.50% | 0.54% (0.30 to 0.81) | 64.4% (51.1 to 77.8) |

The tight misquote rate falls steadily from 4-6 to 16-25 words and is flat after that. The loose share
rises from 4-6 to 16-25 words; the 26+ bin has only 45 changed quotes and a wide interval.

## What this means

- **The threshold caveat cuts the other way.** The plan warned that a fixed 0.8 cutoff is length-dependent:
  one or two changed words drop a short quote below 0.8, while a long quote stays tight until several words
  differ. That pushes changed short quotes towards "loose" and lets tight long quotes carry more edits, so
  it favours *both* predictions. Both came out reversed anyway. The mechanical effect therefore does not
  explain the result; if anything, it makes the measured differences smaller than they are.
- **Genuine misquotes are a short-quote problem.** Audit 2 showed that short quotes change words most
  often. This pass shows the same holds for the tight, close-copy changes alone, which are the ones that
  look most like a real misquote of the student: about 1 in 31 tight 4-6-word quotes, against about 1 in
  135 tight quotes of 11 or more words.
- **A changed long quote is usually not a one-word slip.** Long quotes rarely change (2.1% of 11+-word
  quotes), and when they do, two in three are loose: the quoted passage is not a close copy of anything in
  the essay. That is what a reworded or summarised passage put in quotation marks looks like, rather than
  one altered word in an otherwise faithful copy. These are still quotes that the checker matched to the
  essay at similarity 0.6 or above, so they are related to what the student wrote; but they are not the
  student's sentence.
- **For a quote checker** (such as MV2's [quote-check](https://github.com/munimtechnologies/quote-check)):
  a "changed words" flag on a short quote is about evenly split between a close misquote and a loose
  near-miss, so it is worth reading word by word. A flag on a long quote is less common, and more often
  means "this passage was reworded" than "one word was fixed", so it is worth comparing with the whole
  passage in the essay. The same fixed cutoff means different things at different lengths, so a checker
  should show the similarity and the length together rather than a single tight/loose label.
- **Honest limit.** "Loose" is a similarity band, not a reading. It cannot by itself tell a suggested
  phrase from a heavily altered misquote or a paraphrase in quotation marks; only a human reading of a
  sample could. This pass narrows where to look; it does not say what the loose long quotes are.

## Deviations from the plan

None in data, method, tests or verdict rules. Both predicted comparisons came out reversed. The plan's
threshold caveat expected the mechanical effect to work *for* A2; this write-up adds that it also works
for A1's stated reasoning, which is an interpretation made after seeing the results.

## Limits

- The predictions were informed by audits 1, 1b, 2 and 2b, so this is not a blind test. It is exploratory.
- Similarity is `verbatim_quote_check`'s word-level best-match ratio (difflib, over essay windows a little
  shorter and longer than the quote), a proxy for "was this really quoted from the essay".
- These are rates, not a reading of any quote. This pass reads no quote text.
- Long-quote counts are small: 294 changed quotes of 11 or more words in all, and 45 in the 26+ bin.
- Strata are by the checker's word count of the cleaned quote. 1b's classes inherit 1b's limits: elision is
  read generously and bold is taken as a marked correction ("changed" includes changes shown in bold).
- This covers one model (GLM-4.7), one exam genre and one dataset.

## Reproduce

```bash
sh setup-3.sh          # fetches the pinned checker, audit.py and explain.py and hash-checks them
python -m unittest -v
python length_tight.py --data glm47_final.jsonl --out length-tight.json --workers 3
```

Apache-2.0 (code), CC BY 4.0 (text). MV2, Munim, Inc., mv2@munimtech.com.
