# Audit 6b design note: the label without the learner

Written on 2026-10-30 (about 20:00 UTC) by MV2 of Munim, Inc., while audit 6's two sealed runs were still
generating and before any of their counts had been seen. Made with AI agents working in his name. Text
CC BY 4.0. This is a design note, not a plan: the plan (PLAN-6b.md) and its predictions will be committed
before any 6b feedback is generated, and may only narrow what is written here.

## Question

Audit 6 asks whether excerpts from English language learners' essays change the student's words more often
than excerpts from matched non-ELL essays (S1), and whether saying "the student is an English language
learner" moves that rate on ELL essays (L1). In audit 6 the label is always true, so a label effect and an
essay effect can only be separated within ELL essays. 6b asks the remaining half: **does the same sentence
change quote fidelity on essays by students who are not ELL?** If the label alone makes a model "fix"
words while quoting, it should show here too, where the essay itself gives less reason to.

## Design (fixed now, before audit 6's results)

- Same data, pairs, models, settings and classifier as audit 6 (`audit6.py`, PLAN-6.md), unchanged.
- One new call per pair: the matched non-ELL essay with the label prompt (**no_label**). The label sentence
  is identical to audit 6's. Audit 6's no_base is deterministic (temperature 0, seed 0, same pinned model
  and wheel), so 6b compares no_label with no_base per pair; the run re-generates a fixed 10% of no_base
  calls first and stops if any differs from audit 6's counts.
- Pairs in audit 6's order, up to the number audit 6 completed for that model, or 480 minutes.
- Comparison: no_label minus no_base word-changed rate, bootstrap over pairs (10,000), the same
  4-point equivalence band and 300-excerpt floor as L1. A second, descriptive comparison: the label effect
  on non-ELL essays against audit 6's label effect on ELL essays.

## Why it is new

Our 2026-10-30 search (see PLAN-6.md) found no test of quote fidelity under any student-attribute prompt.
*Marked Pedagogies* (arXiv:2603.12471) varied attributes, including counterfactual ones, but measured the
wording of feedback, not whether its excerpts were faithful.

## Limits known now

- The label is false for these students on purpose. No real student is affected: the essays are a public
  research corpus and no feedback is shown to anyone. Only counts are published.
- Two small CPU models, as in audit 6.
- If audit 6 stops early for a model, 6b for that model is limited to the same pairs.

-- MV2, Munim, Inc., mv2@munimtech.com
