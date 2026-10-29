# Results, audit 4: do six LLMs keep the student's words when they quote them? (FeedType)

feedback-quote-audit, audit 4. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-29 from the sealed run's `feedtype.json` (in this repository). Text CC BY 4.0.

**In one line:** the first cross-model check, and all three preregistered predictions held. Across six
LLMs and three prompts on the public FeedType benchmark (SEFORA university essays), 1.18% of the 27,462
primary-set feedback quotes change the student's words (C1, bound was 5%), the two small models change
words more often than the four larger ones (C2, 3.85% vs 0.81%), and short quotes change words more than
long ones (C3, 2.29% vs 0.68%). After three IELTS audits whose point predictions mostly reversed, the
pattern replicates on an independent dataset — but with two honest caveats below.

## Why this audit is different

Audits 1-3 measured one model (GLM-4.7) on one exam (IELTS Task 2). This is the first time the same
questions are asked of a different, independent dataset built from **six** models on **real university
student essays**. As far as we could find (arXiv, Hugging Face, GitHub and web searches, 2026-10-14 to
2026-10-29), no prior tool or paper checks whether quotes inside LLM-written essay feedback reproduce the
student's text across several models. The FeedType paper itself studies feedback focus types and
pedagogical adaptivity, not quote accuracy.

## What was run

- Plan: [PLAN-4.md](PLAN-4.md), committed 2026-10-29 before this pass, after audits 1, 1b, 2, 2b and 3.
  The sealed run's setup checked that the public plan matched its own held copy (SHA-256
  `8c14d2dc...`) before reading any data, and refused to start until the plan was public.
- Data: **FeedType** (Almousa, Peyghambari Oskoui, Coelho, Rogers, Li and Litman, "Evaluating Feedback
  Focus and Pedagogical Adaptivity in LLM-Generated Feedback on Student Writing", AIME-Con 2026,
  arXiv:2609.28026), [github.com/nia135/FeedType](https://github.com/nia135/FeedType) at commit
  `ad955eca067ce5eeff12eddc309bfbcb83e63439`. The run downloaded that commit's tarball (SHA-256
  `a1b395af...`), confirmed its root folder named the pinned commit (`commit_in_root: true`), and read
  4,805 JSON files in memory: 4,607 model-feedback files across six models and three prompts, plus 198
  teacher files. Essays are from the SEFORA corpus (arXiv:2607.00274). Both works are CC BY-NC 4.0; this
  audit reads them for non-commercial research and republishes no essay or feedback text, only counts.
- Same checker and code as audits 1-3, imported and hash-checked in setup, not copied: feedback-commons
  v0.8.0 checker (`d53b6b46...`), audit 1's `audit.py` at commit `0d1c75a` (`028c0d8d...`) and 1b's
  `explain.py` at commit `d298ed9` (`9f2959da...`). Code for this pass: `feedtype.py`, tests in
  `test_feedtype.py`.
- Python 3.12.15, CPU only, 6 minutes wall, peak memory 0.15 GB. Unit tests passed in the sealed
  container before the run. 0 parse errors; no missing or unexpected model folders. 95% CIs are 10,000
  bootstrap resamples over essay drafts, paired by draft because every model commented on the same drafts
  (seed `feedback-quote-audit-4-20261029`).

## Unit and filters (as preregistered)

A **comment** is one model's `model_comment` on a paragraph (teachers: a `note`/`highlight` comment). A
**quote** is a double-quoted passage. A quote is **primary** if the checker matches it to the essay
(exact, punctuation-only, or altered at word-level similarity at least 0.6), it has at least 4 words, it
has no rewrite cue in the 60 characters before it, and it is not a quote of the teacher comments the model
saw. (FeedType gives no task prompt, so the teacher comments stand in for audits 1-3's exam-question
filter.) **Word-changed** is 1b's class: still not found after Markdown emphasis, typography, spacing,
edge punctuation, case and ellipsis are set aside. **Tight** means the best essay match has similarity at
least 0.8; **loose** is below. **Short** = 4-6 words; **long** = 11+ words.

The pass found 51,851 double-quoted passages in all. The filters set aside quotes under four words
(19,876), quotes with a rewrite cue before them (6,743), quotes not found in the essay (2,734), and
quotes of the teacher comments (527); a quote can fall under more than one reason, so these do not simply
sum. What remains is the **primary set of 27,462 quotes**, from 5,049 quoting comments over 271 drafts.

## The three predictions, exactly as planned

| test | measure | result | predicted | verdict |
|---|---|---|---|---|
| **C1** | pooled word-changed rate, 6 models × 3 prompts | 1.18% (325 / 27,462), 95% CI 0.83–1.76% | ≤ 5% | **held** |
| **C2** | word-changed rate, 2 small − 4 larger models (paired) | +3.05 pts (3.85% vs 0.81%), CI +1.48 to +5.57 | > 0 | **held (small higher)** |
| **C3** | word-changed rate, short − long quotes (paired) | +1.61 pts (2.29% vs 0.68%), CI +0.97 to +2.54 | > 0 | **held (short higher)** |

No test was underpowered (C1 needed 300 primary quotes and had 27,462; C2's small side had 3,399; C3's
long side had 14,161). The verdict rule is the one fixed in the plan: for C2/C3, "held" if the whole 95%
CI is on the predicted side of zero.

- **C1 held.** The IELTS headline (GLM-4.7 changed words in about 4.3% of quotes once formatting was set
  aside) replicates loosely across six different models on a different corpus: pooled, 1.18% change the
  student's words, well under the 5% bound. Most feedback quotes keep the student's words.
- **C2 held, but not because model size predicts fidelity.** The two small models (LLaMA-3.1 8B, Mistral
  7B) pool to 3.85% against 0.81% for the four larger ones. **This is driven by one model, not by size.**
  The largest contributor to the "larger" pool is LearnLM, which quotes enormously (21,317 of the 27,462
  primary quotes) and almost always faithfully (0.22%), pulling the large-model average down. Mistral-24B,
  a *larger* model, has the **highest** single-model rate in the study (13.2%, 66 / 500). So "smaller
  models change words more" is true as a pooled comparison but is not monotonic in parameter count; see
  the per-model table.
- **C3 held.** Short 4-6-word quotes change words more than long 11+-word quotes (2.29% vs 0.68%), the
  same direction found on GLM-4.7 in audits 2 and 3. The plan noted a mechanical bias working *against*
  this (a long quote has more words that could change); the direction holds despite it.

## Per model (word-changed rate among primary-set quotes, 95% CI over drafts)

| model | primary quotes | word-changed | rate | 95% CI | loose share of changed | quote-from-elsewhere share |
|---|---:|---:|---:|---:|---:|---:|
| LearnLM | 21,317 | 47 | 0.22% | 0.12–0.42% | 40.4% | 95.3% |
| Mistral-7B | 933 | 14 | 1.50% | 0.59–3.29% | 21.4% | 72.1% |
| Gemini 2 Flash | 1,614 | 37 | 2.29% | 1.42–3.48% | 32.4% | 40.8% |
| LLaMA-3.1 8B | 2,466 | 117 | 4.74% | 3.08–7.42% | 23.9% | 61.6% |
| Qwen2.5-70B | 632 | 44 | 6.96% | 4.53–9.69% | 29.5% | 1.7% |
| Mistral-24B | 500 | 66 | 13.20% | 8.90–18.10% | 56.1% | 0.7% |

Rates span almost two orders of magnitude, from 0.22% (LearnLM) to 13.2% (Mistral-24B). The
"quote-from-elsewhere" share — a word-faithful quote found in a *different* paragraph than the one the
comment is attached to — also varies enormously (0.7% to 95.3%): LearnLM and Mistral-7B tend to pull in
text from across the whole essay, while Qwen-70B and Mistral-24B quote the local paragraph. This column
has no analogue in the IELTS audits, where feedback was essay-level.

## Per prompt (no prediction)

| prompt | primary quotes | word-changed | rate | 95% CI |
|---|---:|---:|---:|---:|
| Prompt 1 (zero-shot) | 11,946 | 116 | 0.97% | 0.63–1.55% |
| Prompt 2 (zero-shot + category definitions) | 13,130 | 106 | 0.81% | 0.56–1.21% |
| Prompt 3 (few-shot) | 2,386 | 103 | 4.32% | 2.85–6.83% |

Few-shot (Prompt 3) both quotes the least and changes the student's words the most. This was not
predicted; it is a lead for a future preregistered test, not a conclusion here.

## Teacher baseline

Human teachers almost never put a student's words in quotation marks: only 9 primary-set quotes across
all 198 teacher files (0.46% of teacher comments quote at all, against 16.4% of model comments). With 9
quotes the rate (8 changed) is meaningless as a fidelity estimate; the honest reading is that quoting the
student verbatim is something the models do and the teachers in this corpus essentially do not.

## Honest limits and data notes

- **One dataset quirk, reported not resolved.** Mistral-24B's "Prompt 1" and "Prompt 3" cells have
  byte-identical counts, so the FeedType release appears to carry the same Mistral-24B files under two
  prompt names. The paper itself flags naming inconsistencies; we do not resolve it, and it inflates
  Mistral-24B's share of the pooled total slightly. It does not affect the C-tests, which pool by model
  and by length.
- No task prompts or rubrics are in FeedType, so a model quoting the assignment in words close to the
  student's could be scored as a changed quote. The loose share (34.5% of changed quotes pooled) shows how
  much of the "changed" signal is not a close copy.
- "Loose" is a similarity band, not a reading. The checker cannot tell a genuine misquote from a suggested
  phrase in quotation marks; only a human reading a sample could, and this pass reads none and publishes
  none.
- Drafts of one essay and essays by one student are not independent; the bootstrap resamples drafts.
- These are counts, not a reading of any quote. Rates come from the checker's matches at similarity ≥ 0.6.

## What this means

- **The quote-fidelity question generalises.** The central IELTS finding — most AI feedback quotes keep
  the student's words, a small minority change them silently — now has independent support across six
  models and real university essays. Short quotes are the riskier ones in both settings.
- **"Bigger is more faithful" is false as stated.** A 24B model has the worst rate here and an instruction-
  tuned education model (LearnLM) the best. For anyone picking a model to generate student feedback, the
  lesson is to measure the specific model, not to trust size.
- **For a quote checker** (MV2's free offline [quote-check](https://github.com/munimtechnologies/quote-check)):
  the cross-model spread confirms the tool should flag per quote regardless of model, show similarity and
  length together, and not assume any model is safe.

## Deviations from the plan

None in data, method, tests or verdict rules. All three predictions held. The per-model nuance on C2
(LearnLM volume; Mistral-24B highest) and the Mistral-24B duplicate cell are observations made after
seeing the results and are labelled as such.

## Reproduce

```bash
sh setup-4.sh          # fetches the pinned checker, audit.py and explain.py and hash-checks them
python -m unittest -v
python feedtype.py --data feedtype.tar.gz --out feedtype.json --workers 3
```

Apache-2.0 (code), CC BY 4.0 (text). MV2, Munim, Inc., mv2@munimtech.com.
