# feedback-quote-audit

When AI feedback has already been *published*, does it quote the student's words exactly?

When feedback quotes a student's sentence, the quote should be what the student wrote. If a model quietly
fixes a spelling or a verb form while copying, the student never sees their own error.
MV2's preregistered studies in [feedback-commons](https://github.com/munimtechnologies/feedback-commons)
measured this for small local models generating feedback themselves (about 93% of matched quotes exact
in v5). This repository audits public datasets of AI-written essay feedback instead, starting with
feedback from a large model and now covering three datasets and at least eight generating models.

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0; text CC BY 4.0.

**Track record: [`PREDICTIONS.md`](PREDICTIONS.md)** lists all 24 preregistered predictions across the audits
below with their verdicts (10 held, 9 reversed, 2 did not hold, 1 no clear difference, 2 underpowered;
`predictions.json` has the same table).

## Audit 1: GLM-4.7 feedback on IELTS essays (preregistered, done)

- Data: [`Jackrong/IELTS-writing-feedback-reasoning`](https://huggingface.co/datasets/Jackrong/IELTS-writing-feedback-reasoning),
  pinned to revision `326db2de39a2da62b4f25c0fad80b10c844c56df`. It holds 8,946 IELTS Writing Task 2
  essays with Markdown feedback and reasoning text from GLM-4.7.
- Plan: [`PREREG.md`](PREREG.md), committed before any quote was checked.
- **Results: [`RESULTS.md`](RESULTS.md)** (`results.json` has the counts). The primary set has 50,742
  quotes. 37.7% of them are character-exact copies of the essay, so H1 (at least 95%) did not hold.
  92.3% keep the student's words and 7.7% change words. H2 and H3 came out reversed.
- Only counts are published, never essay or feedback text. The essays' upstream dataset lists no licence.

## Follow-up 1b: where the gap comes from (exploratory, planned before running, done)

- Plan: [`PLAN-1b.md`](PLAN-1b.md). Code: `explain.py`.
- **Results: [`RESULTS-1b.md`](RESULTS-1b.md)** (`explain.json` has the counts). All five predictions
  held.
- Once Markdown formatting and "..." are allowed for, 95.7% of quotes keep the student's words. The low
  exact rate was mostly formatting: 47.5% of quotes differ only in punctuation or quote marks at their two
  ends.
- 4.3% change the student's words. A third of those show the change in bold, so 2.8% of all quotes
  change the words without marking it.
- Audit 1's H3 reversal (reasoning vs feedback) disappears after the same normalisation.

## Audit 2: quote length and essay band (planned before running, done)

- Plan: [`PLAN-2.md`](PLAN-2.md). Code: `length.py` (`setup-2.sh` fetches the pinned code and waits until
  the plan is public).
- **Results: [`RESULTS-2.md`](RESULTS-2.md)** (`length.json` has the counts). All five predictions came out
  reversed.
- Short quotes change the student's words most often: 6.1% of 4-6-word quotes against 1.5% of quotes over
  25 words. 71% of the unmarked changes are in 4-6-word quotes, and each word in a long quote is also less
  likely to change.
- Essays at band 7.0 or above get more changed quotes than essays at 5.5 or below, even with quote length
  held fixed (4.1% vs 2.5% unmarked).
- Audit 1's band gap in the exact rate survives holding length fixed (+11.8 points). Most of it is
  formatting.

## Audit 2b: why do stronger essays get more changed quotes? (planned before running, done)

- Plan: [`PLAN-2b.md`](PLAN-2b.md). Code: `band.py` (`setup-2b.sh` fetches the pinned code and waits until
  the plan is public).
- **Results: [`RESULTS-2b.md`](RESULTS-2b.md)** (`band.json` has the counts). Audit 2's reversed band
  finding was a surprise, and audit 2 read no quotes, so it left three explanations untested. This pass
  tested them on the same data with counts only.
- The reversal has two causes. Weaker essays have more of their quotes marked as rewrites and taken out of
  the measured set (T1: 49.2% vs 42.6% of eligible quotes), which leaves their remaining set cleaner. But
  even among tight, genuine quote attempts (word-level similarity at least 0.8) the strong band still
  changes words more often (T2: 3.03% vs 1.69%).
- There is no clear band difference in how loose the changed quotes are (T3), so "suggested phrasing" does
  not explain the strong band's higher rate; loose near-misses are common in both bands.

## Audit 3: genuine misquotes or near-misses, by quote length? (planned before running, done)

- Plan: [`PLAN-3.md`](PLAN-3.md). Code: `length_tight.py` (`setup-3.sh` fetches the pinned code and waits
  until the plan is public).
- **Results: [`RESULTS-3.md`](RESULTS-3.md)** (`length-tight.json` has the counts). Both predictions came
  out reversed.
- Genuine misquotes (tight matches, word-level similarity at least 0.8, that still alter a word) are a
  short-quote problem: 3.19% of tight 4-6-word quotes against 0.74% of tight quotes of 11 or more words.
- When a long quote does change the student's words, it is more often a loose near-miss than a one-word
  slip: 66.3% of changed 11+-word quotes are loose, against 50.1% of changed 4-6-word quotes.
- The fixed 0.8 cutoff favours both predicted directions, so it cannot explain either reversal. For a
  checker: show the similarity and the quote length together, not a single tight/loose label.

## Audit 4: six models on a second dataset — the first cross-model check (planned before running, done)

- Data: [FeedType](https://github.com/nia135/FeedType) at commit `ad955eca` (Almousa et al., AIME-Con 2026,
  arXiv:2609.28026), six LLMs × three prompts on SEFORA university essays (arXiv:2607.00274), CC BY-NC 4.0.
  Counts only, no essay or feedback text redistributed.
- Plan: [`PLAN-4.md`](PLAN-4.md). Code: `feedtype.py` (`setup-4.sh` fetches the pinned checker, `audit.py`
  and `explain.py`, hash-checks them, and waits until the plan is public).
- **Results: [`RESULTS-4.md`](RESULTS-4.md)** (`feedtype.json` has the counts). **All three predictions
  held** — the first audit to replicate rather than reverse.
- Across six models and three prompts, 1.18% of 27,462 primary-set quotes change the student's words (C1,
  bound 5%). Short quotes change words more than long ones (C3: 2.29% vs 0.68%).
- Small models change words more than large ones *as a pool* (C2: 3.85% vs 0.81%), but this is driven by
  LearnLM (21,317 faithful quotes, 0.22%) dragging the large pool down, not by size: Mistral-24B, a larger
  model, has the highest single-model rate (13.2%). Per-model rates span 0.22% to 13.2%.
- Teachers in this corpus almost never quote the student verbatim (9 primary quotes in 198 files).

## Audit 5: does feedback ranked "more specific" quote more faithfully? (planned before running, done)

- Data: SpecEval (`speceval_dataset.json`, SHA-256 `3d7e8852…`), the specificity preference set released with
  [FeedEval](https://github.com/BBeeChu/FeedEval) (Chu, Kim and Yi, ACL Findings 2026, arXiv:2601.04574):
  41,730 chosen/rejected pairs of LLM feedback on 10,398 ASAP++ student essays, ranked by a specificity score
  that counts the essay passages the feedback quotes. Counts only, no essay or feedback text redistributed.
- Plan: [`PLAN-5.md`](PLAN-5.md), committed before any quote was checked. Code: `speceval.py` (`setup-5.sh`
  fetches the pinned checker, `audit.py` and `explain.py`, hash-checks them and the data, and waits until the
  plan is public).
- **Results: [`RESULTS-5.md`](RESULTS-5.md)** (`speceval.json` has the counts). E1 **did not hold**, narrowly:
  6.17% of 519 primary-set quotes change the student's words (CI 4.10–8.30%; bound 5%). E2 and E3 are
  **underpowered**: the feedback rarely quotes the student at length (0.60% of 71,586 distinct texts), so the
  long-quote and bottom-ranked sides fell under the plan's floor of 100 quotes.
- Descriptively, top-ranked feedback changed fewer words than bottom-ranked (3.4% vs 12.2%), and 27 of the
  32 changed quotes are close copies with a word altered. Neither is a verdict.

## Follow-up 5b: what the rewrite-cue filter set aside in SpecEval (planned before running, running)

- Plan: [`PLAN-5b.md`](PLAN-5b.md), written after audit 5's counts were known and committed before this pass
  counts anything. Code: `cues.py` (`setup-5b.sh` fetches the pinned checker, `audit.py`, `explain.py` and
  audit 5's `speceval.py`, hash-checks the data, and waits until the plan is public).
- Audit 1's rewrite-cue rule set aside 79% of SpecEval's quoted passages, and its cue list includes "for
  example", "such as" and "e.g.", which also introduce genuine quotes. This pass splits matched 4+-word quotes
  into primary (no cue), cited (citation cues only) and edit-cued sets.
- Predictions: G1 the cited set is at least as large as the primary set; G2 cited quotes change words at a
  rate within 3 points of primary quotes; G3 edit-cued quotes change words more than cited ones; G4
  (exploratory) on primary + cited quotes, bottom-ranked feedback changes words more than top-ranked.
  Results will be posted as RESULTS-5b.md whether they hold or not.

## How it works

`audit.py` finds every passage the feedback puts in double quotation marks. It sets aside quotes of the
exam question (or, for FeedType, the teacher comments the model saw) and suggested rewrites, then checks
the rest against the essay with `verbatim_quote_check.py`. That file is a copy of feedback-commons
`tools/verbatim_quote_check.py`; the sealed run downloads it fresh from tag v0.8.0 and records its SHA-256
in the results. The same checker runs in the offline
[quote-check](https://github.com/munimtechnologies/quote-check) page. Each quote is exact, same words
(only punctuation, spacing or capitals differ), changed words, or not found. `explain.py` records the
first formatting step after which each quote matches. `length.py` breaks 1b's classes down by quote length
and essay band, `band.py` breaks the band difference down by rewrite-cue exclusion and match tightness,
`length_tight.py` breaks the tight/loose split down by length, `feedtype.py` runs the same primary-set
and word-changed logic over the FeedType dataset per model, per prompt and per model-prompt cell,
`speceval.py` runs it over each distinct SpecEval feedback text by its rank in the pairs, and `cues.py`
splits SpecEval's matched quotes by the kind of cue before them.

```bash
sh setup.sh
python -m unittest -v
python audit.py --data glm47_final.jsonl --out results.json --workers 3
python explain.py --data glm47_final.jsonl --out explain.json --workers 3
python length.py --data glm47_final.jsonl --out length.json --workers 3
python band.py --data glm47_final.jsonl --out band.json --workers 3
python length_tight.py --data glm47_final.jsonl --out length-tight.json --workers 3
python feedtype.py --data feedtype.tar.gz --out feedtype.json --workers 3
python speceval.py --data speceval_dataset.json --out speceval.json
python cues.py --data speceval_dataset.json --out cues.json
```

Python 3.10+, standard library only (`setup-5.sh` and `setup-5b.sh` use gdown to fetch SpecEval from Google
Drive).

## Limits

Only double-quoted passages are checked. The rule that sets aside suggested rewrites is a heuristic: it
misses rewrites marked with bold inside the quote, and its cue list ("for example", "such as") also sets
aside some genuine quotes, which matters most on SpecEval (79% of its quoted passages; follow-up 5b counts
them). Similarity is a proxy: no pass here reads quote text, so none can tell a suggested phrase from a
heavily altered misquote; only a human reading of a sample could. Audits 1-3 cover one model, one exam and
one dataset; audit 4 adds six models on a second dataset (FeedType/SEFORA, non-commercial); audit 5 adds a
third (SpecEval/ASAP++). See PREREG.md, RESULTS.md, PLAN-1b.md, RESULTS-1b.md, PLAN-2.md, RESULTS-2.md,
PLAN-2b.md, RESULTS-2b.md, PLAN-3.md, RESULTS-3.md, PLAN-4.md, RESULTS-4.md, PLAN-5.md, RESULTS-5.md,
PLAN-5b.md and PREDICTIONS.md.

## Licence

Apache-2.0 (see LICENSE). By MV2 of Munim, Inc., mv2@munimtech.com.
