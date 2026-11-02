# PLAN-9: when a math tutor restates the student's work, is it what the student said?

Preregistered 2026-11-02 by MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0
(`audit9.py`, `test_audit9.py`), text CC BY 4.0.

## Why

Audits 1-8 asked whether AI feedback quotes a student's essay or code faithfully. A tutoring dialogue raises
the same question in a sharper form. When a tutor answers a student's wrong step, it often restates it: "you
said 45", "you calculated 15", "how did you get 56?". If the restated number is not one the student wrote, the
tutor is correcting a mistake the student did not make, and the student has to work out what went wrong
twice.

## What is known before this plan

Only the opportunity counts of the groundwork probe
([`groundwork/audit-9/probe9.json`](groundwork/audit-9/probe9.json), run 2026-11-02 06:06 UTC on the pinned files). The
dev set has 300 dialogues and 2,476 replies from 9 tutors (7 LLMs, Expert, and Novice on 76 dialogues). The
test set has 191 dialogues and 1,547 replies from anonymous tutors and no labels. In the dev set, 319 replies
have a sentence that pairs a second-person cue with a number (Llama 3.1 405B 98, Llama 3.1 8B 61, Mistral 47,
Sonnet 30, Expert 30, GPT-4 28, Gemini 12, Phi-3 8, Novice 5); the test set has 206. Mistral's 86 quoted replies
are almost all quotes of 7+ words. Nobody has checked any restatement against the student's turns, and no
reply or dialogue text has been read.

## Data

MRBench v3 as released for the BEA 2025 shared task: github.com/kaushal0494/UnifyingAITutorEvaluation at commit
`12c258f397d6df5892c773349499f5c36b7f567c`, folder `BEA_Shared_Task_2025_Datasets`, CC BY-SA 4.0 (Maurya et
al., NAACL 2025; Kochmar et al., BEA 2025). The job stops unless the files' SHA-256 values are
`a395feab801de50d44b73e1e9b88f84824a1f1d92e15ae86842d90c2b6dbf33c` (`mrbench_v3_devset.json`) and
`5a73434fd9e1dfc73026e146d3709f95f2483a51a5e5b354bc96d981448d92cd` (`mrbench_v3_testset.json`).

## Method (`audit9.py`)

- **Turns.** The history is split into Tutor and Student turns. The tutor turns hold the problem.
- **Restatement sentence (the unit).** A reply is split into sentences. A sentence counts if it has a
  restatement cue and, once "step 2", "line 3"-style references and ordinals ("2nd") are removed, at least
  one number. The cues are "you" + said, say, wrote, got, found, calculated, computed, mentioned, answered,
  stated, came up with, arrived at, counted, added, multiplied, subtracted, divided, used; the same with
  "you've" or "you have" + a past participle (not "you've got"); "your answer"; and "how/where/why did you"
  + get, come up with, arrive at, find, calculate, compute, work out. A cue does not count if one of the two
  words before it is if, when, once, whether, unless, until, can, could, would, should, will, might, may,
  must, shall, did, do, does, have, has or had (hypotheticals and questions such as "if you added 4").
- **Classes.** **student**: at least one of the sentence's numbers is in a student turn (digits, with
  thousands commas and trailing zeros normalised, or a number word such as "sixteen"). **equivalent**: none is,
  but one equals a student value in another form (a fraction a/b, a fraction times 100, a percent / 100,
  "half"). **context**: only in the tutor turns. **nowhere**: in no turn of the dialogue.
- **Unsourced** = context or nowhere: the sentence attributes to the student no number the student wrote.
  This rule is lenient on purpose: one shared number makes the whole sentence "student", so the rates below
  are a floor on misstatement, not an estimate of it.
- **Broad cues** ("you have", "you've", "you had", "you get", "your calculation / result / solution / total /
  work / final"), counted only when no strict cue is present, are reported without a verdict: those
  sentences often state the tutor's own working.
- **Quoted spans (descriptive only).** Double-quoted spans of 2+ words; a span that is 60% or more of the
  reply's words is a "wrapper" (a reply set in quotation marks) and is only counted. Others are "attributed"
  if "you" or "your" occurs in the 80 characters before them, and are classed student / context (exact
  lower-cased word run) / near (difflib similarity at least 0.8 to a window of a student turn) / nowhere.

## Predictions

95% CIs come from 10,000 bootstrap resamples of dialogues (seed 20261103; R2 uses 20261104 and R3 20261105).

| id | prediction | verdict rule | floor |
|---|---|---|---|
| R1 | More than 5% of restatement sentences are unsourced (all tutors, dev + test) | held if the whole CI is above 5%, did not hold if wholly below, else inconclusive | 150 sentences |
| R2 | More than 2% of restatement sentences carry numbers found nowhere in the dialogue | same rule at 2% | 150 sentences |
| R3 | In the dev set, the unsourced rate is higher in replies whose human label for Mistake Location is "No" or "To some extent" than in replies labelled "Yes" (difference in points) | held if the whole CI is above 0, reversed if below, else no clear difference | 30 sentences a side |

Why these: R1 and R2 ask whether misstatement is common enough to matter, at a level a teacher would notice
(1 in 20) and a level that cannot be a matter of phrasing (a number from nowhere, 1 in 50). R3 asks whether the
dataset's own annotators already catch it: if a tutor names a number the student never wrote, the annotators
should be less likely to say the reply located the mistake.

## Reported without a verdict

Class counts for strict and broad sentences; per-tutor counts and unsourced rates (test-set tutors stay
anonymous); LLM tutors against the human tutors on the dev set (Expert and Novice; the probe shows too few
human restatements for a powered test, so this is descriptive only, with a CI); counts by Mistake Location
label; quoted spans by class, attributed or not, per tutor, and wrappers per tutor.

## Limits, stated in advance

- A number in a restatement sentence is not always the student's: the tutor may restate and then correct in
  the same sentence. The lenient rule counts such a sentence as "student" whenever any number matches, so the
  bias runs toward fewer misstatements, not more.
- The reverse error exists too: a tutor may restate a value the student implied but never wrote (a unit
  change, a rounded value, a result the student was about to compute). The "equivalent" class removes only
  fractions, percents and number words. A counts-only audit cannot read the sentences, so R1 can overstate
  misstatement by that much; R2 is less exposed, since "nowhere" also excludes the problem's numbers.
- The cue list and sentence splitter are heuristics fixed here; cues the list misses are not counted.
- The dialogues stop at the mistake, so only the tutor's next turn is seen. Bridge dialogues may hold little
  of the problem in the tutor turns, which moves "context" cases to "nowhere".
- MRBench's replies were generated or written for a benchmark, not sent to real students in this form.
- Licence CC BY-SA 4.0: only counts are published. No dialogue text, reply text or ids.

## Procedure

One sealed CPU job (`audit9-mrbench-v1`) waits until this file, `audit9.py` and `test_audit9.py` are on the
repository's main branch, downloads the two files at the pinned commit and checks their SHA-256, runs the unit
tests, then `python audit9.py run`. Its output `audit9-mrbench.json` records the SHA-256 of this plan and the
script. Results go in RESULTS-9.md whatever they show.
