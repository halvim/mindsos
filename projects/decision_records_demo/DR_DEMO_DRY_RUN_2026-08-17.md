---
title: Decision Records — the first dry run against a live model, and the finding that re-froze v1
status: Current
date: 2026-08-17
basis: demo/decision-records `df57033` (tag `dr-ship-b-confirmed`), run on the Linux box; Screen B live in a browser
lane: the SECOND walk. Input to the §0.4 re-freeze — NOT a defect list
---

# The first dry run with Screen B, 2026-08-17

The owner ran all beats with a live frontier model beside MindsOS for the first
time, hand-pasting the intake. **Screen B had never been run at any beat.**
92 guards were green, Gate 7's mechanical clause was green, ships A and B were
merged, and none of it caught this — which is the point of the document.

## 1. The finding

**It is not a demonstration. It is a slide show.**

Owner, verbatim in substance: *I paste something into the LLM and it shows
intelligence; I paste something into MindsOS and it looks scripted, pre-made. I
didn't like it at all. Nothing should be paste-and-here-is-the-result —
otherwise I don't need MindsOS for the presentation, I just have to print
something correct on the screen.*

**The mechanism, and it is not a capability defect.** A chat model streams: the
room watches tokens appear and reads that as thinking. MindsOS renders a
finished page instantly and the room reads that as a lookup, or as something
typed earlier. **The reasoning is produced and never witnessed.** Ships A and B
put the reasoning ON the page; neither makes the room see it happen. Ship C as
scoped does not fix it either — a room that watches an input edit and a re-run
still never sees the system work.

⚠ **No ship on the frozen list addressed this**, and the freeze is why: §0.3
closed the list against exactly the kind of change that turns out to be needed
once someone performs the thing.

## 2. Two framings that were WRONG, both corrected by the owner

**(a) Beat 6's memory argument is a gotcha.** The design opened a new chat and
showed the model unable to retrace its decision. **A competent operator saves
the output** — so the failure is an artifact of how *we* chose to run it, and a
room will see it as cheating. The real difference was never recall: a saved
prose file is something you must TRUST; the Record is **re-derived from the
store in front of you** (`--from-root`, already built). The beat was arguing the
wrong thing with the right mechanism.

**(b) The claim is not a competition.** It is **MindsOS does the thinking, the
LLM processes the text** — a division of labour. So Screen B is not an
opponent, it is the SAME COMPONENT shown being used the way people use it
today: alone, doing both jobs. ⟹ This framing is also better aligned with ship
D's guard set than *"no model is present"* ever was: *no capacity in the
decision set consults the client, no verdict carries `read_by_model`, every
reading is quote-verified or refused* is a proof of the owner's sentence, where
absence-of-a-model was only a fact about a configuration.

## 3. What the demo must show instead — the real-world pipeline, both sides

Owner, and it is the shape of everything below:

1. an email arrives
2. a human pastes a **pre-made prompt** to extract the components it needs
3. the component set is stored
4. the component set is compared with the policy
5. a new artifact carries the components and the outcome

**Same five steps on both sides — and step 4 is deliberately NOT the same.**
The model does steps 2 AND 4: you paste the policy and it reasons. MindsOS uses
the model for step 2 ONLY and does step 4 itself. ⚠ **Presenting five identical
steps is the failure mode**: the room concludes *"the difference is that one is
code."* Declare the symmetry at 1, 2, 3 and 5; break it out loud at 4.

**The train of thought is the artifact.** For the model it lives in the prompt;
for MindsOS it is taught into the system. That is the sentence the demo exists
to make legible.

⚠ **THE PROMPT IS SHOWN ON SCREEN, IN FULL, AND IS NEVER PARAPHRASED.** If the
model's train of thought lives in a prompt we wrote, then we chose how good the
model is, and a skeptic will say so. **Mitigation is disclosure, and the strong
form is invitation: let the room improve the prompt live.** This converts the
demo's largest rigging risk into its best fairness move. Undisclosed, it is the
courted-refusal problem again, one level up and invisible.

⚠ **DO NOT FAKE SYMMETRY AT STEP 3.** On the model's side components land in a
FILE — that is what people do. On ours they land in the STORE. Writing a file to
look symmetric throws away the only difference that matters: a file is trusted,
a store is re-derived. **Show the asymmetry.**

## 4. Form B — chosen 2026-08-17 (owner), after three mockups

**Origin-per-fact.** The message stays on screen; each fact is lifted out of it
and marked with WHO produced it (`read_by_model` vs `read_from_source`); the
decision then cites which fact moved it. Rejected alternatives: a sequential
question-by-question reveal (buildable sooner, but still output-shaped), and a
needed/found/missing ledger (most judgement per second, least theatrical).

⚠ **The line that survives whatever is built: show the DELIBERATION, never the
MACHINERY.** *"It asks what severity was assessed"* is intelligence; *"the
severity reader capacity consumed the exposure DataState"* is architecture, and
it breaks G6 and the IP policy at once.

## 5. The model split, and it is a claim rather than a saving

**The cheapest model available does the extraction; the best available model
runs on Screen B.** Putting a weak model on Screen B would rig the comparison.
And cheap is SAFE on our side for a structural reason: quote-verification
locates the value in the source text, so a weak extractor that invents
something produces a **refusal**, not a wrong answer. It degrades honestly.

⟹ *The reading is done by the cheapest model on the market. The thinking is not
done by a model at all.*

## 6. What this dry run did NOT cover

- **The pipeline does not exist.** Every judgement above is about a demo built
  on STRUCTURED intake with the intake hand-pasted to the model. Nothing has
  been run end to end in the five-step form.
- **No transport exists.** `LiveLLM` takes a deployment-supplied callable and
  the piece that touches the network was never written.
- **Rehearsals remain at zero** in the counted sense: this was one run, and
  beats 0 and 7 were spoken for the first time.
