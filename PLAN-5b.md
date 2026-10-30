# Audit 5b plan: what the rewrite-cue filter set aside in SpecEval

Preregistered by MV2 of Munim, Inc. on 2026-10-30, before any of the quotes below was counted. Made with AI
agents working in his name. This file is committed to the repository before the sealed run starts; the run's
setup waits until this exact file is public and stops if it never is.

**Written after audit 5's results were known** (aggregate counts only, in `speceval.json` and
[RESULTS-5.md](RESULTS-5.md); no quote or feedback text was read). G1-G3 ask about quotes audit 5 never
counted on their own. G4 replays audit 5's E3 comparison on a wider set, and its direction was chosen after
seeing E3's underpowered point estimate, so G4 is **exploratory**, like follow-up 1b.

## Why

Audit 5 kept only 519 quotes of 14,413 double-quoted passages in SpecEval's feedback. The rewrite-cue rule,
imported unchanged from audit 1, set aside 79% of passages. It was built to drop suggested rewrites
("instead", "better", "should be"), but its cue list also includes phrases that introduce genuine quotes of
the student: "for example", "such as" and "e.g.". On IELTS feedback that cost little. In SpecEval it may
have hidden most of the real quoting, which left E2 and E3 underpowered. This pass counts those quotes
separately. As far as we could find, no one has checked SpecEval's quotes (see PLAN-5.md), and no audit of
AI feedback quotes has tested how a rewrite filter's cue list changes the measured set.

## Data and code

- Same file as audit 5: `speceval_dataset.json` (SHA-256 `3d7e88527155194cbf597a9de75ee06d45b79871a68a06bbb6ab04f089bd996b`),
  read in memory; counts only, no essay or feedback text published.
- Same checker, `audit.py` (commit 0d1c75a) and `explain.py` (commit d298ed9), hash-checked by `setup-5b.sh`,
  plus audit 5's `speceval.py` for loading and ranking, fetched from the commit that added it (`95028e0`);
  its SHA-256 is recorded in the output. New code: `cues.py`, tests in `test_cues.py`.

## Sets (each quote is in at most one)

Every quote is classified by `audit.classify` exactly as in audit 5. Only quotes that the checker **matches**
to the essay (exact, punctuation-only, or altered at similarity >= 0.6) and that have **at least 4 words**
are counted. Among them:

- **primary**: no rewrite cue in the 60 characters before the quote (audit 5's primary set, unchanged);
- **cited**: a cue is there, but every cue in that window is a citation cue: "for example", "such as",
  "e.g." (matched case-insensitively; "for instance" is also treated as a citation phrase, although it is
  not on the cue list);
- **edit-cued**: any other cue is in that window ("instead", "better", "should be", "could write" and the
  rest of `audit.CUE_RE`), with or without a citation cue.

**Wide** = primary + cited. Word-changed, short (4-6 words), long (11+), tight/loose (0.8) and rank
(top / middle / bottom from pair membership) are defined as in audit 5. 95% CIs are percentile bootstraps over
essays (10,000 replicates, seed `feedback-quote-audit-5b-20261030`), paired by essay.

## Predictions (fixed now)

- **G1. The citation cues hid at least as much quoting as the filter kept.** The cited set has at least as
  many quotes as the primary set. "held" or "did not hold" on the counts.
- **G2. Cited quotes are as faithful as primary quotes.** Word-changed rate, cited minus primary, paired by
  essay: "held" if the whole 95% CI lies within -3.0 to +3.0 points; "did not hold" if the whole CI lies
  above +3.0 or below -3.0; otherwise "inconclusive"; under 100 quotes on a side, "underpowered".
- **G3. Edit-cued quotes change words more often than cited quotes** (they include real suggested rewrites
  that resemble the student's text). Edit-cued minus cited: "held" if the CI is above zero, "reversed" if
  below, else "no clear difference"; under 100 on a side, "underpowered".
- **G4 (exploratory). On the wide set, bottom-ranked feedback changes words more often than top-ranked.**
  Bottom minus top, paired by essay: "held" if the CI is above zero, "reversed" if below, else "no clear
  difference"; under 100 on a side, "underpowered". A bias to note: if top-ranked feedback quotes longer
  passages, the short-quote pattern favours G4.

## Reported without a prediction

For each set and rank: quotes, word-changed rate (with CI), short and long counts and rates, the loose share of
changed quotes, and feedback texts holding at least one quote of the set.

## Honest limits, stated in advance

- A citation cue can sit before a suggested rewrite ("such as" followed by a better phrase). The checker
  cannot tell those apart from misquotes; only a human reading a sample can, and this pass reads none.
- Only double-quoted passages; ASAP tokens like @PERSON1 count as words; rank is pair membership only.
- G4 is exploratory and cannot confirm audit 5's E3 on its own; it reuses the same essays.

## Outputs

`cues.json` (counts and rates only). Results will be written up in RESULTS-5b.md whether the predictions hold
or not.

-- MV2, Munim, Inc., mv2@munimtech.com
