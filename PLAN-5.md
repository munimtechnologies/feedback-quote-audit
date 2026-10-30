# Audit 5 plan: does feedback ranked "more specific" quote the student more faithfully? (FeedEval SpecEval)

Preregistered by MV2 of Munim, Inc. on 2026-10-30, before any quote in the data below was counted. Made with AI
agents working in his name. This file is committed to the repository before the sealed run starts; the run's setup
waits until this exact file is public and stops if it never is.

## Why

Audits 1-3 measured quote fidelity in one model's feedback (GLM-4.7, IELTS essays); audit 4 checked six models on
university essays (FeedType) and the two core patterns replicated: most quotes keep the student's words, and short
quotes change words more often than long ones. This audit tests both on a third dataset with a third generator,
and asks one new question that this dataset makes possible.

FeedEval (Chu, Kim and Yi, "FeedEval: Pedagogically Aligned Evaluation of LLM-Generated Essay Feedback", ACL
Findings 2026, arXiv:2601.04574) trains an evaluator of feedback **specificity** on SpecEval, a set of about 41K
chosen/rejected feedback pairs. Per the paper, the candidates were written by an LLM (the paper ties SpecEval to
GPT-4o) under three prompt designs that ask it to "quote or summarize the relevant parts of the essay", and each
pair was ranked by a specificity score computed by an LLM that extracts the essay segments the feedback quotes.
That score counts quotes; nothing in the paper says it checks that a quote reproduces the student's words. So:
does the feedback SpecEval ranks as more specific quote the student any more faithfully than the feedback it
ranks lower? As far as we could find (searches of arXiv, GitHub and the web from 2026-10-14 to 2026-10-30), nobody
has checked the quotes in SpecEval, or whether a specificity label tracks quote fidelity.

## Data

- `speceval_dataset.json` from the Google Drive folder linked in github.com/BBeeChu/FeedEval's README (folder
  `1yK7us2hKaYHDwjx7xK_yJQxP-X1roYDN`, file id `1G71f7CFVLVV2cx908Du8jGW6k2Y0OhcF`), SHA-256
  `3d7e88527155194cbf597a9de75ee06d45b79871a68a06bbb6ab04f089bd996b`, 92,393,348 bytes, a list of 41,730 records
  with fields `essay_id`, `essay_set`, `essay`, `chosen`, `rejected`, `chosen_score`, `rejected_score`, `split`.
  These facts come from a schema probe (2026-10-30) that recorded only shapes, sizes, hashes and counts of
  quoted spans per field in the first 2,000 records; it read no quote against any essay. The run stops if the
  file's hash differs.
- Licences: the FeedEval repository shows an MIT badge but has no LICENSE file; the essays come from ASAP/ASAP++,
  which have their own terms. This audit only reads the file, in memory, for non-commercial research. It does not
  redistribute any essay or feedback text. It publishes aggregate counts only, with attribution.

## Unit and filters (same as audits 1-4, imported from audit.py and explain.py)

- **Feedback text** = one distinct `chosen` or `rejected` string for an essay. The same candidate appears in
  several pairs, so each distinct (essay_id, text) is checked once. **Essay** = the record's `essay` field (if one
  essay_id carries different essay texts, the first is used and the conflicts are counted).
- **Rank** (from the pairs, not from any score): **top** = a text that appears only as `chosen`; **bottom** = only
  as `rejected`; **middle** = both. With three candidates per essay and trait, top is the best of the three and
  bottom the worst.
- **Quotes** = passages in double quotation marks on one line, as in `audit.extract_quotes`.
- **Primary set** (`audit.in_primary`): the quote matches the essay (exact, punctuation/whitespace, or altered at
  checker similarity >= 0.6); at least 4 words; no rewrite cue in the 60 characters before it on the same line.
  There is no exam question or teacher text to set aside here.
- **Word-changed** = `explain.explain`'s `word_changed` class (still not found after Markdown emphasis, typography,
  spacing, edge punctuation, case and ellipsis are set aside); every other primary-set quote is word-faithful.
  Tight / loose = similarity >= / < 0.8, as in audits 3-4. **Short** = 4-6 words; **long** = 11 or more.
- Rates are pooled. 95% CIs are percentile bootstraps over essays (10,000 replicates, seed
  `feedback-quote-audit-5-20261030`); comparisons are paired by essay.

## Predictions (fixed now)

- **E1. The headline replicates a third time.** The pooled word-changed rate over all distinct feedback texts is
  at most 5.0% (audit 1b's bound; GLM-4.7 4.3%, FeedType 1.18%). Holds if the point estimate is <= 0.050 with at
  least 300 primary-set quotes; otherwise "did not hold"; under 300, "underpowered".
- **E2. Short quotes change words more than long ones** (audits 2, 3 and 4). Word-changed rate of 4-6-word quotes
  minus that of 11+-word quotes is above zero: "held" if the 95% CI is above zero, "reversed" if below, else "no
  clear difference"; under 100 quotes on a side, "underpowered". A mechanical bias works against it (a long quote
  has more words that could change). The probe saw few long quotes, so "underpowered" is a real possibility.
- **E3 (new). The specificity ranking does not select for faithful quotes.** Word-changed rate of top-ranked
  feedback minus that of bottom-ranked feedback (per quote, paired by essay) is not below -1.0 point: "held" if
  the 95% CI's lower end is above -0.010; "did not hold" if its upper end is below zero (top-ranked feedback
  clearly more faithful, by more than the margin); otherwise "inconclusive"; under 100 quotes on a side,
  "underpowered". Possible biases: if top-ranked feedback quotes longer passages, the short-quote pattern pushes
  its rate down, against E3; the amount of quoting itself does not bias a per-quote rate.

## Reported without a prediction

By rank and by essay set: distinct feedback texts, the share that quote the student at all, primary-set quotes
per text, the share of texts with at least one word-changed quote, the word-changed rate (with CI for ranks), the
loose share of word-changed quotes. Counts of excluded quotes by reason, records by split, skipped records and
essay-text conflicts.

## Honest limits, stated in advance

- Essay sets 3-6 are source-based: students write about a reading the feedback model may also have seen. The
  source texts are not in the file, so a quote of the reading that resembles the student's wording could count as
  a changed quote; per-set rates and the tight/loose split are reported to show this.
- The checker cannot tell a misquote from a suggested phrase that resembles the student's text; only a human
  reading a sample can. This run reads no text by hand and publishes none.
- Rank comes from pair membership; the score fields are not used. If candidates were paired differently from
  what the paper describes, "top" and "bottom" still mean only-chosen and only-rejected.
- ASAP essays are anonymised (tokens like @PERSON1); the checker compares words, so such tokens count as words.
- The generator is named from the paper (GPT-4o; an appendix also mentions GPT-5.1); we do not resolve this.

## Outputs

`speceval.json` (counts and rates only). Code: `speceval.py` (imports `audit.py` at 0d1c75a and `explain.py` at
d298ed9, and feedback-commons v0.8.0's checker, all hash-checked by `setup-5.sh`), tests in `test_speceval.py`.
Results will be written up in RESULTS-5.md whether the predictions hold or not.

-- MV2, Munim, Inc., mv2@munimtech.com
