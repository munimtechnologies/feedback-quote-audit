# When AI feedback quotes your students: a short guide for teachers

What the finished audits of AI feedback (audits 1-8 and follow-ups 1b, 2b, 5b and 8b) found, and a five-minute
way to check a tool yourself. By MV2 of Munim, Inc. Made with AI agents working in his name; it has not yet been
reviewed by a teacher. Text CC BY 4.0.

## Why it matters

AI feedback often quotes a sentence from the student's essay and comments on it. If the quote is accurate,
the student sees their own words and their own mistake. If the model quietly changes a word while
"quoting" (fixes a spelling, a verb form, an article), the student is told about a sentence they did not
write, and the error they actually made goes unseen. A teacher skimming the feedback cannot tell either.

## What the audits found

All numbers are counts from public datasets; no essay, code or feedback text was read or published. Each audit
was planned in writing before any quote was counted (see [`PREDICTIONS.md`](PREDICTIONS.md) for the
44 predictions and how each came out).

1. **Most quotes keep the student's words, but a small share do not, and the share depends on the model.**
   - GLM-4.7 feedback on 8,946 IELTS essays: 95.7% of 50,742 quotes keep the student's words once
     formatting is allowed for; 4.3% change them, and 2.8% change them without marking the change
     ([`RESULTS-1b.md`](RESULTS-1b.md)).
   - Six models on university essays (FeedType): 1.18% of 27,462 quotes change the student's words, but
     single models range from 0.22% to 13.2% ([`RESULTS-4.md`](RESULTS-4.md)).
   - Feedback on school essays (SpecEval, ASAP++): 96.0% of 2,065 quotes keep the student's words
     ([`RESULTS-5b.md`](RESULTS-5b.md)).

2. **A character-for-character check is the wrong test.** Only 37.7% of the IELTS quotes were exact
   copies, and nearly half differed only in punctuation or quote marks at their two ends
   ([`RESULTS.md`](RESULTS.md), [`RESULTS-1b.md`](RESULTS-1b.md)). A strict copy check flags almost
   everything; check whether the *words* are the same.

3. **Short quotes are where changed words hide.** In the IELTS feedback, 6.1% of 4-6-word quotes changed
   the student's words against 1.5% of quotes over 25 words, and 71% of unmarked changes were in 4-6-word
   quotes ([`RESULTS-2.md`](RESULTS-2.md)). Close copies with one word altered were also mostly short
   (3.19% of close 4-6-word quotes against 0.74% of close 11+-word quotes, [`RESULTS-3.md`](RESULTS-3.md)).
   The same short-over-long pattern held across six models on a second dataset (2.29% vs 0.68%).

4. **Bigger is not automatically better.** Across the six FeedType models, the larger ones changed fewer
   words as a group (0.81% vs 3.85%), but that came from one model (LearnLM, 0.22%); a 24-billion-parameter model had the
   highest rate of all (13.2%) ([`RESULTS-4.md`](RESULTS-4.md)). Test the tool you actually use.

5. **Bold usually marks an intended correction.** About a third of the IELTS quotes that changed words
   showed the change in bold, which usually means "here is the corrected version" rather than a slip
   ([`RESULTS-1b.md`](RESULTS-1b.md)). The unmarked changes are the ones to read first.

6. **Strong writing gets misquoted too.** IELTS essays at band 7.0 or above got more unmarked changed
   quotes than essays at 5.5 or below, even at the same quote length (4.1% vs 2.5%,
   [`RESULTS-2.md`](RESULTS-2.md), [`RESULTS-2b.md`](RESULTS-2b.md)).

7. **Feedback ranked "more specific" quoted more faithfully, in one dataset.** In SpecEval, feedback
   ranked lower for specificity changed the student's words in 10.03% of its quotes against 2.48% for
   top-ranked feedback. This was an exploratory comparison ([`RESULTS-5b.md`](RESULTS-5b.md)).

8. **English learners' words were changed more often, in one small model.** Audit 6 had two small open
   models (1.5 and 1.7 billion parameters) write feedback on grade 6-12 essays from PERSUADE 2.0, asking for
   excerpts "copied exactly, word for word"; they differed enormously (about 9 in 10 vs about 1 in 5 excerpts
   kept the student's words, [`RESULTS-6.md`](RESULTS-6.md)). Audit 7 re-ran the better one on 292 new pairs
   with room to finish its replies. An English language learner's words were changed in 15.8% of excerpts,
   against 10.0% for a classmate whose essay had the same prompt and score. Telling the model "this student is
   an English language learner" did not make it worse (it lowered the rate a little). Long replies changed
   words about twice as often as short ones ([`RESULTS-7.md`](RESULTS-7.md)). Check English learners'
   quoted sentences first.

9. **Telling the model to "copy the student's words exactly" made no clear difference.** In a separate
   preregistered test, adding that line to the prompt of two small local models gave 94.1% exact quotes
   against 94.3% without it; which model was used mattered far more (about 98-99% vs 88-90%)
   ([feedback-commons RESULTS-v6](https://github.com/munimtechnologies/feedback-commons/blob/main/research/RESULTS-v6.md)).
   A prompt instruction is not a check.

10. **Programming hints: names are right, code snippets need checking.** In a real introductory Python
    course (ProgFeed), gpt-4o-mini's hints named the student's own variables and functions almost perfectly
    (2 of 519 names were found nowhere). But 37 of 177 code snippets shown in the hints (21%) were neither in
    the student's file nor in the assignment, although the model was told not to suggest code
    ([`RESULTS-8.md`](RESULTS-8.md)). About half of those 37 (18) later appeared in that student's final
    submission, more often than in other students' final code (49% vs 30%); that does not prove the student
    copied it ([`RESULTS-8b.md`](RESULTS-8b.md)). When a hint says "your line `...`", find that line in the
    student's code, and if a hint is meant to give no code, read the code it shows.

## A five-minute check

1. Open the free [quote-check page](https://rawcdn.githack.com/munimtechnologies/quote-check/v0.4.0/quote-check.html)
   (English or Spanish). It works offline and sends nothing anywhere; you can also download the file.
2. Paste one student's text and the AI feedback on it, then press **Check quotes**. Tick **Changed quotes
   first** to put the rows worth reading at the top; each row keeps its number, so you can still find it in
   the feedback.
3. Read the rows in this order:
   - **Changed words**, shortest quotes first: the words were changed and nothing marks it. Compare the
     quote with "what the student actually wrote" in the same row. The **Where to look** column says
     whether 1 or 2 words differ (compare word by word) or 3 or more (compare with the whole passage; it may
     be a reworded passage or a suggested phrase).
   - **Changed words, marked**: the change is in bold or italics. Check that the feedback presents it as
     a correction, not as the student's own sentence.
   - **Not found**: often a suggested phrase. Check that the feedback does not present it as something
     the student wrote.
   - **Exact**, **Same words** and **Same words, some left out** keep the student's words.
4. Try it on three or four essays before trusting a tool or a prompt, including at least one strong essay
   (finding 6) and at least one by an English learner (finding 8).
5. For programming hints, the page checks double-quoted text only; search the student's file for each
   snippet in `code font` by hand (finding 10).

## For students

When feedback quotes you, find that sentence (or that line of code) in your draft before you fix it. If the
quote does not match what you wrote, the comment may be about something you never wrote.

## Limits

- The audits cover five public datasets (IELTS practice essays, university essays, two sets of US school
  essays and one university programming course) and the models that produced or were run on them, not the
  tools in any particular school.
- They measure copying, not whether the feedback is good or correct.
- Similarity is a proxy. No one read the quotes, so a heavily reworded misquote and a suggested phrase
  can look alike.
- The English-learner finding (8) comes from one small model and one prompt; it shows the effect can happen,
  not how often it happens in the tools schools use.

-- MV2, Munim, Inc., mv2@munimtech.com
