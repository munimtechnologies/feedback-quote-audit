# Results, audit 2b: why do stronger essays get more changed quotes in GLM-4.7's feedback?

feedback-quote-audit, audit 2b. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-28 from the sealed run's `band.json` (in this repository). Text CC BY 4.0.

**In one line:** the reversal has two causes, not one. Weaker essays have more of their quotes taken out
of the set as marked rewrites (T1 held), which leaves their remaining set cleaner; but even among the
tight, genuine quote attempts that survive, stronger essays still change the student's words more often
(T2 held, 3.03% vs 1.69%). There is no clear band difference in how loose the changed quotes are (T3). So
part of audit 2's surprise is composition and part is real: the model does change strong-essay words more.

## What was run

- Plan: [PLAN-2b.md](PLAN-2b.md), committed at 2026-10-28 00:55:25 UTC (commit `bc2a586`), after audits 1,
  1b and 2 and before this pass. The sealed run's setup checked that the public plan was identical to the
  one it held before reading any data. The run started at 01:34:58 UTC, about 40 minutes after the commit.
  `band.json` records the plan's SHA-256 (`86323dbb...`).
- Same data and code as audits 1, 1b and 2: `glm47_final.jsonl` (SHA-256 `3b5eea94...69494`), checker
  feedback-commons v0.8.0 (`d53b6b46...`), audit 1's `audit.py` at commit `0d1c75a` (`028c0d8d...`) and
  1b's `explain.py` at commit `d298ed9` (`9f2959da...`). All were imported, not copied, and hash-checked in
  setup.
- The pass reproduced every earlier total: 50,742 primary-set feedback quotes, and 20,520 / 2,712 quotes
  in the low / high band groups (`consistent_with_earlier: true`).
- Python 3.12.15, CPU only, 12 minutes, peak memory 0.52 GB. Unit tests passed in the sealed container
  before the run. 95% CIs come from 10,000 bootstrap resamples over essays, resampling the two band groups
  independently (seed `feedback-quote-audit-2b-20261028`).
- Only counts are published. No essay or feedback text appears here or in `band.json`, and no review sample
  was drawn in this pass.

## The three tests (weak = band 5.5 or below, 3,774 essays; strong = band 7.0 or above, 500 essays)

A quote is "eligible" if the checker matches it to the essay (exact, punctuation-only, or altered with
word-level similarity at least 0.6) and it is at least 4 words long. "Primary" is eligible and not a marked
rewrite and not a quote of the exam question. "Changed" is 1b's word-changed class. "Tight" means the best
match in the essay has word-level similarity 0.8 or above — a genuine quote attempt, not a near miss.

| test | weak band (≤5.5) | strong band (≥7.0) | weak − strong (95% CI) | predicted | verdict |
|---|---:|---:|---:|---|---|
| T1 rewrite-cue exclusion (marked rewrites / eligible) | 49.20% (19,950 / 40,550) | 42.56% (2,015 / 4,735) | +6.64 pts (+5.37 to +7.92) | weak higher | **held** |
| T2 word-changed among tight matches (sim ≥ 0.8) | 1.69% (335 / 19,855) | 3.03% (78 / 2,571) | −1.35 pts (−2.09 to −0.66) | strong higher | **held** |
| T3 loose share of changed quotes (sim < 0.8 / all changed) | 54.79% (406 / 741) | 52.44% (86 / 164) | +2.35 pts (−6.45 to +11.27) | strong higher | **no clear difference** |

No test was underpowered; the smallest group denominator is the strong band's 164 changed quotes in T3
(floor 100). The verdict rule is the one fixed in the plan: "held" if the whole 95% CI falls on the
predicted side of zero, "reversed" if it falls wholly on the other side, otherwise "no clear difference".

## Predictions, exactly as planned

- **T1 held.** The weak band takes 49.20% of its eligible quotes out of the primary set as marked
  rewrites, against 42.56% for the strong band — a difference of +6.64 points (95% CI +5.37 to +7.92).
  The model marks its corrections as rewrites more often on weaker essays, so the weak band's primary set
  is left cleaner. This is a composition mechanism that contributes to audit 2's reversal.
- **T2 held.** Restricting to tight matches — exact and punctuation-only quotes plus altered quotes whose
  match is at similarity 0.8 or above — the strong band still changes the student's words more often:
  3.03% against 1.69%, a difference of −1.35 points (−2.09 to −0.66). So the reversal is not merely loose
  or suggested phrasing counted as a change: even among genuine quote attempts, strong-essay quotes change
  words more.
- **T3 no clear difference.** Among the changed quotes, the share that is a loose match (similarity below
  0.8) is about the same in both bands: 54.79% for the weak band and 52.44% for the strong, a difference of
  +2.35 points whose 95% CI (−6.45 to +11.27) spans zero. There is no evidence that the strong band's
  changed quotes are more often loose near-misses of the essay.

## Also reported, with no prediction

- **R0, raw word-changed rate by band.** 3.61% (741 / 20,520) for the weak band against 6.05% (164 /
  2,712) for the strong band, a difference of −2.44 points (95% CI −3.35 to −1.54). This reproduces audit
  2's B2 unstandardised figure (3.61% vs 6.05%), confirming the two passes count the same quotes. T1 and
  T2 together explain its two parts: the weak band's primary set is cleaner because more of its quotes are
  excluded as marked rewrites (T1), and within the tight matches that remain the strong band genuinely
  changes words more (T2).

## What this means

- **Audit 2's surprise is both composition and real.** The reversal — stronger essays getting more changed
  quotes — is partly a side-effect of how quotes are composed (the model marks more of its weak-essay
  corrections as rewrites, so those drop out of the measured set), and partly a real difference: on tight,
  genuine quote attempts the model still changes strong-essay words more often. Neither explanation alone
  accounts for it.
- **"Suggested phrasing" does not differ by band.** The near-miss / suggested-phrasing explanation (that
  strong-essay feedback puts recommended phrasing in quotes that only partly appear in the essay) would show
  up as the strong band's changed quotes being looser matches. They are not: T3 shows no band difference in
  looseness. Loose matches are common in *both* bands (about 53-55% of changed quotes), so looseness is a
  property of short changed quotes generally, not of the strong band in particular.
- **For a quote checker** (such as MV2's [quote-check](https://github.com/munimtechnologies/quote-check)):
  a changed short quote is about as likely to be a loose near-miss whether the essay is strong or weak, so
  a checker cannot use the essay's band to decide whether a flagged short quote is a real misquote or
  suggested phrasing. The length signal from audit 2 (short quotes change words most) remains the more
  useful sort.
- **Honest limit on the T2 conclusion.** T2 holds on the rates, but this pass still reads no quote text.
  "Genuine quote attempt" means only "the best match in the essay is tight"; it cannot by itself tell a
  real misquote from a suggested phrase that happens to match the essay closely. Only a human reading of a
  sample could. T2 narrows the explanation; it does not close it.

## Deviations from the plan

None in data, method, tests or verdict rules. T1 and T2 came out as the plan's predicted directions; T3
came out with no clear difference.

## Limits

- The predictions were informed by audits 1, 1b and 2, so this is not a blind test. It is exploratory.
- Similarity is `verbatim_quote_check`'s word-level best-match ratio, a proxy for "was this really quoted
  from the essay". It cannot by itself separate a suggested phrase from a real misquote.
- These are rates, not a reading of any quote. This pass reads no quote text.
- Band is the dataset's label, not a new rating. 1b's classes inherit 1b's limits: elision is read
  generously and bold is taken as a marked correction.
- This covers one model (GLM-4.7), one exam genre and one dataset.

## Reproduce

```bash
sh setup-2b.sh         # fetches the pinned checker, audit.py and explain.py and hash-checks them
python -m unittest -v
python band.py --data glm47_final.jsonl --out band.json --workers 3
```

Apache-2.0 (code), CC BY 4.0 (text). MV2, Munim, Inc., mv2@munimtech.com.
