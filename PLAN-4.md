# Audit 4 plan: do six LLMs keep the student's words when they quote them? (FeedType)

Preregistered by MV2 of Munim, Inc. on 2026-10-29, before any of the data below was counted. Made with AI agents
working in his name. This file is committed to the repository before the sealed run starts; the run's setup
waits until this exact file is public and stops if it never is.

## Why

Audits 1-3 measured quote fidelity in one model's feedback (GLM-4.7) on one exam (IELTS Task 2). A result from
one model on one dataset can be a quirk of that model or that data. This audit asks the same questions of a
different, independent dataset with six models, on real university student essays. As far as we could find
(searches of arXiv, Hugging Face, GitHub and the web on 2026-10-29), nobody has checked whether quotes in
LLM-written essay feedback reproduce the student's text across several models. The FeedType paper itself
studies feedback focus types and adaptivity, not quote accuracy.

## Data

- **FeedType** (Almousa, Peyghambari Oskoui, Coelho, Rogers, Li and Litman, "Evaluating Feedback Focus and
  Pedagogical Adaptivity in LLM-Generated Feedback on Student Writing", AIME-Con 2026, arXiv:2609.28026),
  github.com/nia135/FeedType at commit `ad955eca067ce5eeff12eddc309bfbcb83e63439` (2026-09-22). It holds
  paragraph-level feedback from six LLMs (folder names `LLaMa8B`, `Mistral7B`, `Mistral24B`, `Qwen70B`,
  `Gemini2Flash`, `LearnLM`) under three prompts (`Prompt 1` zero-shot, `Prompt 2` zero-shot with category
  definitions, `Prompt 3` few-shot), plus the teachers' comments, on essays from the SEFORA corpus
  (Peyghambari Oskoui et al., arXiv:2607.00274). Per the paper, each model saw the full essay, the target
  paragraph, the task prompt, the rubric and earlier feedback.
- Licences: the FeedType annotations and the SEFORA essays are CC BY-NC 4.0. This audit only reads them, in
  memory, for non-commercial research. It does not redistribute any essay or feedback text. It publishes
  aggregate counts only, with attribution to both works.
- The run downloads the GitHub tarball of that commit and reads the JSON files inside it without extracting
  them. It records the tarball's SHA-256 and checks that the tarball's root folder names the pinned commit.

## Unit and filters (same as audits 1-3, imported from audit.py and explain.py)

- **Essay** = the draft file's paragraph bodies, joined with blank lines. A **comment** = one `model_feedback`
  annotation's `model_comment` (teachers: a `note` or `highlight` annotation's non-empty `comment`).
- **Quotes** = passages in double quotation marks (straight, curly, guillemets or low-high), on one line, as in
  `audit.extract_quotes`. Single-quoted passages are not counted.
- **Primary set** (`audit.in_primary`): the quote matches the essay (exact, punctuation/whitespace, or altered
  at checker similarity >= 0.6); it has at least 4 words; no rewrite cue in the 60 characters before it on the
  same line; and it is not a quote of the teacher comments on the same draft. Audits 1-3 used the exam question
  for that last check; FeedType gives no task prompt, so the teacher comments (which the models saw as earlier
  feedback on revised drafts) take its place.
- **Word-changed** = `explain.explain`'s `word_changed` class: still not found in the essay after Markdown
  emphasis, typography, spacing, edge punctuation, case and ellipsis are set aside. Every other primary-set
  quote is **word-faithful**.
- **Tight / loose**: a word-changed quote with checker similarity >= 0.8 is tight (a close copy with words
  altered); below 0.8 it is loose (more like a paraphrase or suggested phrase put in quotation marks).
- **Elsewhere**: a word-faithful quote that is not found in the paragraph the comment is attached to.
- **Short** = 4-6 words; **long** = 11 or more words (audit 3's strata).
- Rates are pooled (sum of numerators / sum of denominators). 95% CIs are percentile bootstraps over essay
  drafts (10,000 replicates, seed `feedback-quote-audit-4-20261029`). Comparisons are paired by draft, because
  every model commented on the same drafts.

## Predictions (fixed now)

- **C1. The headline replicates.** The pooled word-changed rate over all six models and three prompts is at most
  5.0% (audit 1b's bound; GLM-4.7 was 4.3%). Holds if the point estimate is <= 0.050 with at least 300
  primary-set quotes; otherwise "did not hold"; under 300 quotes, "underpowered".
- **C2. Smaller models change words more.** The word-changed rate of the two small models (LLaMA-3.1 8B,
  Mistral-7B) minus that of the four larger ones (Mistral-24B, Qwen2.5-70B, Gemini Flash, LearnLM) is above
  zero. "Held" if the 95% CI is above zero, "reversed" if below, otherwise "no clear difference"; under 100
  quotes on either side, "underpowered".
- **C3. Short quotes change words more than long ones** (as in audits 2 and 3 on GLM-4.7). The word-changed rate
  of 4-6-word quotes minus that of 11+-word quotes, all models, is above zero. Same verdict rule and floor as C2.
  A known mechanical bias works *against* this prediction: a long quote has more words that could change.

## Reported without a prediction

Per model, per prompt and per model-prompt cell: quotes, primary-set quotes, the word-changed rate (with CI for
models and prompts), the loose share of word-changed quotes, the share of word-faithful quotes taken from
another paragraph, and the share of comments that quote the student at all. The same measures for the teachers'
comments, as a human reference (no prediction: teachers may rarely quote). Parse errors, unexpected or missing
model folders, and counts of excluded quotes by reason.

## Honest limits, stated in advance

- No task prompts or rubrics are in FeedType, so a quote of the assignment that resembles the student's wording
  could be counted as a changed quote. The tight/loose split is reported to show how much of the signal is close
  copies.
- The checker cannot tell a misquote from a suggested phrase that happens to resemble the student's text; only
  a human reading a sample can. This run reads no text by hand and publishes none.
- Drafts of the same essay and essays by the same student are not independent; the bootstrap resamples drafts.
- Sizes are unknown until the run: if a model rarely quotes, its rows are reported as small, not over-read.
- Model names follow the dataset's folder names; the paper reports some naming inconsistencies, which we do not
  resolve.

## Outputs

`feedtype.json` (counts and rates only). Code: `feedtype.py` (imports `audit.py` at 0d1c75a and `explain.py` at
d298ed9, and feedback-commons v0.8.0's checker, all hash-checked by `setup-4.sh`), tests in `test_feedtype.py`.
Results will be written up in RESULTS-4.md whether the predictions hold or not.

-- MV2, Munim, Inc., mv2@munimtech.com
