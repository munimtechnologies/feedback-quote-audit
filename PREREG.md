# Preregistration: does a large model's published essay feedback quote students verbatim?

feedback-quote-audit, audit 1. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-26, before any quote in the dataset was checked. Apache-2.0 (code), CC BY 4.0 (text).

## Why

MV2's preregistered studies (feedback-commons, RESULTS-v3 to v5) found that two small local models
(llama3.2:3b, qwen2.5:3b) copied about 93% of their matched quotes from English learners' essays
exactly (v5: 1,314 of 1,416). Feedback that misquotes a student hides the student's own error. Those
studies asked small models for feedback themselves. This audit asks the same question of feedback that
a large model has *already published* as training data: a public dataset of about 8,900 IELTS Writing
Task 2 essays with feedback written by GLM-4.7.

Prior art (web, GitHub and arXiv searches, 2026-10-14 to 2026-10-26): tools that require feedback to
quote the essay exist (for example an IELTS scorer that rejects feedback quoting text not in the essay),
and papers ask models for exact excerpts, but we found no audit of quote fidelity in a published
AI-feedback dataset.

## Data

- `Jackrong/IELTS-writing-feedback-reasoning` on Hugging Face (tagged Apache-2.0), file
  `glm47_final.jsonl` at revision `326db2de39a2da62b4f25c0fad80b10c844c56df`. The dataset card says the
  essays come from `chillies/IELTS-writing-task-2-evaluation` and keep that dataset's terms; it lists
  no licence, so **no essay or feedback text is published**, only counts.
- Before writing this plan we read the dataset card and an AI summary of one row's layout: the model
  input (first `human` turn, same text as `topic`) is the question, a blank line, then the essay;
  `evaluation` is the Markdown feedback; `reasoning` is the model's `<think>` text; `band` is the score.
  No quote in the dataset was checked before this plan was fixed.

## Method (fixed)

- Source text: the model input split at its first blank line (else first newline) into *question* and
  *essay*. Quotes are checked against the essay.
- Quotes: every passage on one line inside "straight", “curly”, «guillemet» or „low-high“ double quotes
  (1-400 characters), in `evaluation` and, separately, in `reasoning`.
- Checker: `verbatim_quote_check.py` from feedback-commons tag v0.8.0 (also used by quote-check), default
  threshold 0.6: exact / punctuation_or_whitespace ("same words") / altered ("changed words") / not_found.
- **Primary set:** quotes that match the essay (exact, same words or changed words), have at least 4
  words, are not a quote of the question (a quote that is not exact in the essay but is exact or
  same-words in the question is set aside), and have no rewrite cue in the 60 characters before the
  opening quote mark on the same line (instead, rewrite, revise, replace, better, could write/say/use,
  should be/read/say, change, correct..., improv..., e.g., for example, such as, consider, try,
  suggest..., alternative, version, would be, and arrows → -> =>). The cue rule is deliberately broad: it
  sets aside suggested rewrites, which are meant to differ from the student's words.
- **Primary measure:** exact rate = exact quotes / primary-set quotes, pooled over essays, in
  `evaluation`. 95% CI: percentile bootstrap over essays, 10,000 resamples, seed
  `feedback-quote-audit-ielts-20261026`. Floor: 300 primary-set quotes, else "underpowered".

## Hypotheses and verdict rules

- **H1** (level): the exact rate in `evaluation` is at least 95.0%. Verdict on the point estimate; the CI
  is reported. Any comparison with feedback-commons v5's 92.8% is descriptive only (different essays,
  prompts and models).
- **H2** (band): the exact rate is lower for essays with band <= 5.5 (including "<4") than for band >= 7.0.
  Held if the 95% CI of (low - high) is entirely below 0; "reversed" if entirely above; otherwise "no
  clear difference". Each group needs 100 primary-set quotes.
- **H3** (thinking vs final text): the exact rate in `reasoning` is lower than in `evaluation`, paired
  by essay. Same rule as H2, floor 300 quotes in each.

## Also reported (descriptive, no hypothesis)

Quote counts and all four categories before filtering; how many quotes the cue, question and
under-4-words rules set aside; the same-words rate; the exact rate for 4-25-word quotes only and with no
cue/question filters; how many words differ in each changed-words quote (1, 2, 3, 4+); the split mode
of each input; the dataset file's SHA-256 and the generator values.

A random sample of up to 30 changed-words quotes with their closest essay passage (as lowercase words)
is written for a human check of what "changed" means here (for example a silent spelling fix or a
suggestion the cue rule missed). It is not published; how it reads will be summarised in RESULTS.

## Limits known in advance

- Quotes are found only by double quotation marks; single-quoted or unmarked quotes are not checked.
- The cue rule is a heuristic in both directions: it may set aside real quotes (for example "instead of
  writing ...") and may miss some suggested rewrites, which would then count as changed words and lower
  the exact rate.
- If the question spans more than one paragraph, its later paragraphs are counted as essay text.
- One model (GLM-4.7, temperature 0.3 per the card), one exam genre, one dataset.

## Deviations

Any change after the data is read will be listed in RESULTS with the reason.
