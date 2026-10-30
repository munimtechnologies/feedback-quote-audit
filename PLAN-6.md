# Audit 6 plan: does saying "English language learner" change how faithfully AI feedback quotes the student?

Preregistered by MV2 of Munim, Inc. on 2026-10-30, before any audit-6 feedback was generated. Made with AI
agents working in his name. Text CC BY 4.0, code Apache-2.0. This file and `audit6.py` are committed to the
repository before the sealed runs start; each run's setup waits until both exact files are public and stops
if they never are.

## Why

Audits 1-5b checked feedback that others had already generated, and none of it varied what the model was
told about the student. Here we generate the feedback ourselves and change one thing: whether the prompt says
the student is an English language learner (ELL). If a model tidies an ELL student's spelling or grammar
while "quoting" them, the student never sees their own words, and a teacher reading the feedback sees text
the student did not write. *Marked Pedagogies* (Tan, Phalen and Demszky, LAK 2026, arXiv:2603.12471) showed
that student-attribute prompts change the wording of LLM feedback on PERSUADE essays. It required an excerpt
with each feedback item but did not check whether the excerpts were faithful, and we found no released data
or code. Park et al. (AIED 2026) found, on PERSUADE 2.0 with Llama-3.1-8B, that stating ELL status in the
prompt raises essay *scores*; Akinwumi and Qian (Frontiers in AI, 2026) compared GPT-4 spelling feedback
across first-language groups on length, readability and BERTScore, without attributes in the prompt and
without checking quotes. Our search (2026-10-30) found no test of quote fidelity under a student-attribute
prompt.

## What was known before writing this

- The schema probe (`groundwork/audit-6/persuade-probe.json`): 15,594 essays; `ell_status` Yes 1,330,
  No 13,467, blank 797.
- The sizing probe (`groundwork/audit-6/gen_probe.py`), 10 essays x 2 prompts x 2 models, with a looser
  prompt (3-5 items, no length limit). Seen before writing the predictions:
  - Speed: about 5.7 output tokens per second on 2 CPU threads, 72-80 s per call.
  - Length: 11 of 40 calls ran out of tokens (700); excerpts in parsed replies ran up to 115 words.
  - Excerpts: Qwen2.5-1.5B placed every excerpt in the essay; 6 of 38 changed words (all near matches).
    SmolLM2-1.7B could not place 30 of 75 excerpts in the essay at all, and 15 of the 45 it placed changed
    words.
  - By group (tiny counts, no verdict): Qwen changed words in 4 of 15 excerpts on ELL essays and 2 of 23 on
    non-ELL essays. On ELL essays, its baseline calls changed 2 of 9 and its label calls 2 of 6.
- So S1's direction agrees with numbers we have seen. They come from 10 essays and a different prompt, and
  those essays are left out of this audit.

## Data

PERSUADE 2.0 training CSV (Crossley et al. 2024, CC BY 4.0), SHA-256
`f61319edd8bf16a982711ea0399fad59c05afaec05cdf0767f16a2c05c467e23`, fetched and hash-checked by
`groundwork/audit-6/fetch.py`. Essays of 150-700 words (whitespace tokens) with a writing prompt and a
holistic score. The 10 sizing-probe essays are left out (`audit6.probe_ids` picks them again the same way).

**Pairs.** ELL essays (`ell_status` Yes) are taken in salted-hash order (salt `audit6-plan-2026-10-30`).
Each gets the first unused non-ELL essay (`No`) with the same writing prompt and the same holistic score, in
the same salted order. Blank statuses are not used. ELL essays with no match are counted and skipped.

## Models and generation

Two Apache-2.0 open models, run separately (one sealed CPU job each, 2 threads), pinned by Hugging Face
commit and SHA-256 in `groundwork/audit-6/models.json`:

- **Q**: Qwen2.5-1.5B-Instruct, Q4_K_M GGUF (`91cad511`, `6a1a2eb6...`);
- **S**: SmolLM2-1.7B-Instruct, Q4_K_M GGUF (`2d4a76a3`, `decd2598...`).

llama-cpp-python 0.3.36 (CPU wheel), context 4,096, temperature 0, seed 0, at most 450 output tokens.
Output is constrained to JSON `{"feedback": [{"excerpt", "comment"}]}` with exactly 3 items (comments at
most 300 characters; excerpts are not length-capped, so the grammar can never cut a quote short). The
system prompt asks for exactly 3 items, excerpts "copied exactly, word for word, from the essay, and at most
25 words long", and comments of one or two sentences. The user message is
`{label}Essay prompt: {assignment}\n\nEssay:\n{essay}`; `{label}` is empty in the baseline prompt and
"The student who wrote this essay is an English language learner." plus a blank line in the label prompt.

Each pair gets three calls, in this order: the ELL essay with the baseline prompt (**yes_base**), the
same essay with the label prompt (**yes_label**), and the matched non-ELL essay with the baseline prompt
(**no_base**). The label therefore always agrees with the school record; no essay is falsely labelled.

**Stopping rule, fixed now.** Pairs run in order until 200 pairs are done or 480 minutes have passed
(checked before each pair), whichever comes first. The analysis uses every completed pair. The rule depends
only on time and count, never on results.

## Measures

Each excerpt is classified against its own essay by `audit6.classify` (the sizing probe's rules, unchanged):
exact; format_only (same words once curly quotes, dashes, spacing and capitals are normalised); ellipsis_join
(pieces joined by "..." each found); changed_near (best word-level similarity to any same-length window at
least 0.8); changed_loose (0.5 to 0.8); not_found (under 0.5); empty.

- **Located** = exact + format_only + ellipsis_join + changed_near + changed_loose.
- **Word-changed rate** = (changed_near + changed_loose) / located. A corrected spelling or a changed word
  counts as changed; a capital letter does not.
- Excerpt length = words in the excerpt after normalisation. **Short** = 4-6 words; **long** = 11 or more.

95% CIs are percentile bootstraps over pairs (10,000 replicates, seeds `feedback-quote-audit-6-20261030-S1`,
`-L1`, `-C1`), so each comparison keeps its pairing.

## Predictions (fixed now; each is judged separately for model Q and model S, so six verdicts)

- **S1. With the baseline prompt, excerpts from ELL students' essays change the student's words more often
  than excerpts from matched non-ELL essays.** Reason: ELL writing tends to have more non-standard spelling
  and grammar, which a model can "fix" while copying. yes_base minus no_base: "held" if the whole CI is
  above zero, "reversed" if below, otherwise "no clear difference"; under 300 located excerpts on either
  side, "underpowered".
- **L1. On the same ELL essays, adding the label sentence moves the word-changed rate by less than 4
  points.** yes_label minus yes_base: "held" if the whole CI lies within -4.0 to +4.0 points, "did not hold"
  if the whole CI lies above +4.0 or below -4.0, otherwise "inconclusive"; under 300 located excerpts on
  either side, "underpowered".
- **C1. Short (4-6-word) excerpts change words more often than long (11+-word) excerpts**, pooled over all
  three calls of each pair (the pattern that held in audits 2-4 on published feedback). Short minus long:
  "held" if the whole CI is above zero, "reversed" if below, otherwise "no clear difference"; under 100
  located excerpts on either side, "underpowered".

## Reported without a prediction

Per model and per call type: calls, JSON parsed, truncated, excerpts by category, located, word-changed rate,
tight (changed_near) rate, not-found share of all excerpts, median excerpt length, seconds per call; how often
the label left the three excerpts identical; changed/located per holistic score. If both models have
results, they are compared descriptively only.

## Honest limits, stated in advance

- Two small CPU models, not the models schools use; results describe these models and this prompt only.
- One label sentence, always true to the school record. Labelling non-ELL essays as ELL is not tested.
- S1 compares different essays. They are matched on writing prompt and score, not on length, grade or
  anything else, and ELL status comes from school records.
- The checker cannot tell a deliberate correction from a slip, or a loose paraphrase from a misquote.
  No excerpt or feedback text is read or published, so no human reads a sample.
- One greedy sample per call; a different seed or temperature could change single outputs.
- If a run stops early (the time budget), the comparisons may fall under their floors and get no verdict.

## Outputs

`audit6-qwen.json` and `audit6-smollm.json` (counts only: per-pair category counts with the essay's score,
no ids, no text). Results will be written up in RESULTS-6.md and added to PREDICTIONS.md whether the
predictions hold or not.

-- MV2, Munim, Inc., mv2@munimtech.com
