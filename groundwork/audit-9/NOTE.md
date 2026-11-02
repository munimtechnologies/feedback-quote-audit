# Audit 9 groundwork: do AI math tutors restate the student's answer correctly?

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0 (`probe9.py`, `test_probe9.py`),
text CC BY 4.0. Written 2026-11-02, before any audit-9 data was read.

## The idea

Audits 1-8 asked whether AI feedback quotes the student's essay or code faithfully. Tutoring dialogues raise the
same question in a sharper form: when an AI tutor replies to a student's wrong answer, it often restates it
("you said 45", "your answer of 12"). If the restated answer is not what the student said, the tutor is
correcting a mistake the student did not make.

The data is the BEA 2025 shared-task release of MRBench v3
([kaushal0494/UnifyingAITutorEvaluation](https://github.com/kaushal0494/UnifyingAITutorEvaluation), folder
`BEA_Shared_Task_2025_Datasets`, pinned to commit `12c258f3`, CC BY-SA 4.0; Maurya et al., NAACL 2025; Kochmar
et al., Findings of the BEA 2025 Shared Task). Each item is a math tutoring dialogue (from MathDial and Bridge)
cut where the student makes a mistake, followed by the next tutor turn written by several LLMs (GPT-4, Gemini,
Sonnet, Llama 3.1 8B and 405B, Mistral, Phi-3) and by human tutors (an expert and, for some items, a novice). The
dev set carries human labels for Mistake Identification, Mistake Location, Providing Guidance and Actionability.

## Prior art (searched 2026-11-02)

MRBench's eight dimensions include mistake location and coherence but no check of whether the reply restates
the student correctly. The BEA 2025 systems classify the four labels. The closest work perturbs replies for
factuality ("Towards Reward Modeling for AI Tutors in Math Mistake Remediation", arXiv:2603.24375) or writes
"should not contradict the student's answer" into a rubric (arXiv:2606.21502). We found no published count of
how often tutor replies misstate the student's own answer, by tutor, or of how that relates to the human
Mistake Location label.

## What this probe does

`probe9.py` counts opportunities only, per tutor and overall: dialogues, replies, double-quoted spans in replies
and their length in words, replies with any number, and sentences that pair a second-person cue ("you said",
"you got", "your answer", ...) with a number, plus the human label counts. It **never** checks whether a
quoted span or a number appears in the student's turns, so the plan can fix its floors and thresholds before
any outcome is known. Only counts are written; no dialogue text, reply text or ids.

## Draft questions for PLAN-9 (final wording after the probe)

- How often does a reply's restatement of the student (a quoted span, or a number in a "you said / your answer"
  sentence) match nothing the student said?
- Do LLM tutors misstate the student more or less often than the human tutors on the same dialogues?
- Are replies that misstate the student labelled "Yes" for Mistake Location less often?
- Which models? Per-tutor rates, with the same student-level (here: dialogue-level) bootstrap as earlier audits.

## Limits known now

About 300 dev dialogues: per-tutor counts may be small, so floors will matter. A number in a "you" sentence is
not always the student's (it may be from the problem). The dialogues are cut at the mistake, so only the
replies' first turn is seen. Licence CC BY-SA 4.0: we publish counts only and redistribute no text.
