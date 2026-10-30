# Audit 6 design note: does saying "English learner" change how AI feedback quotes the student?

feedback-quote-audit groundwork. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-30. Text CC BY 4.0, code Apache-2.0.

**This is a design note, not a preregistered plan.** No feedback has been generated or read for audit 6.
The plan (PLAN-6.md) will be committed before any audit data is touched, as with every earlier audit,
and its predictions will go into PREDICTIONS.md.

## Question

Audits 1-5b checked whether AI essay feedback quotes the student's words faithfully. None of them changed
what the model was told about the student. Audit 6 asks: when the prompt says the student is an English
language learner (ELL), does the model quote that student's words less faithfully, for example by quietly
"tidying" their grammar inside the quote, or by quoting them less often?

Two arms on the same essays:

- **Label arm (within essay):** the same essay with a baseline prompt and with a prompt that adds one
  sentence, "The student who wrote this essay is an English language learner." Paired by essay.
- **Recorded-status arm (between essays):** baseline prompt only; essays by students the corpus records as
  ELL vs not, matched by writing prompt and holistic score.

The label is synthetic prompt text, not a claim about any student. Results will say "prompt says ELL".

## Why this is new (prior art checked 2026-10-30)

- *Marked Pedagogies* (Tan, Phalen and Demszky, LAK 2026, arXiv:2603.12471) gave four LLMs 600 PERSUADE
  essays under 13 student-attribute prompts and required an essay excerpt with every feedback item. It
  measured shifts in wording (more praise, less critique), not whether the excerpts were faithful, and we
  found no released data or code.
- Our audits 1-5b measured quote fidelity without any attribute manipulation.

We found no public test of quote fidelity under student-attribute labels.

## Data

PERSUADE 2.0 (Crossley et al. 2024, CC BY 4.0), training CSV from the Google Drive link in
github.com/scrosseye/persuade_corpus_2.0. A counts-only schema probe (`persuade-probe.json`, code
`probe.py`) pinned it:

- SHA-256 `f61319edd8bf16a982711ea0399fad59c05afaec05cdf0767f16a2c05c467e23`, 616,894,963 bytes,
  173,266 rows (one per discourse element), 15,594 essays.
- `ell_status`: Yes 1,330, No 13,467, blank 797. `student_disability_status`: identified 1,516, not 10,576,
  blank 3,502. 15 writing prompts; holistic scores 1-6; grades 6-12.
- Median essay length 384 words (5th-95th percentile 184-796).

As in every audit, outputs will be counts only: no essay or feedback text.

## Generation

Compute jobs carry no secrets, so audit 6 uses small open-weight models on CPU. A sizing probe
(`gen_probe.py`, `fetch.py`, `models.json`, tests in `test_gen_probe.py`) runs 10 essays (5 ELL, 5 not) x
2 prompts x 2 Apache-2.0 models (Qwen2.5-1.5B-Instruct and SmolLM2-1.7B-Instruct, Q4_K_M GGUF pinned by
commit and SHA-256) with llama-cpp-python 0.3.36, and records seconds per call, JSON compliance, excerpts
per call and excerpt-fidelity category counts. It sizes the plan; its numbers are not results.

Lessons carried over from earlier audits:

- Explicit excerpt-JSON output, so quotes are unambiguous and no rewrite-cue filter is needed (5b showed
  a filter tuned on one dataset removed three quarters of another dataset's quotes).
- Power floors set in advance: at least 300 excerpts per side before a comparison counts (audit 5).
- An equivalence band only where the expected count lets the interval fit inside it (5b, G2).

## Limits known now

Small CPU models are not the models schools use, so results would describe these models only. The ELL
field in PERSUADE comes from school records and is blank for some essays. One label sentence is a narrow
manipulation; other attributes (for example disability) are left for later.
