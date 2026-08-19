"""S152.2 Q1: can S150.3's ordering invariant be defeated?

CORE-SIDE probe (no imports at all) — runnable anywhere:
    python scripts/critic/probe_ordering_defeat.py

The invariant under test, proposed in S150.3 by THIS lane: a member's verified
quote must fall between the offset of the claimant it is filed under and the
offset of the next claimant named in the document. Three prose shapes:

  [A] facts follow their own claimant — S150.2's shape; ordering CATCHES.
  [B] both names first, then both facts — ordering PASSES a misattribution.
  [C] a fact stated before its own claimant is named — ordering REJECTS a
      CORRECT attribution.

Composed by the critic: all three emails and the span set. No tree behaviour is
involved; this is arithmetic on offsets, which is the point. Repr-only;
verdicts in coordination S153."""

NAMES = ["C. Mensah", "D. Laurent"]


def name_offsets(doc, names):
    return {n: doc.index(n) for n in names if n in doc}


def ordering_ok(doc, names, filed, quote):
    offsets = name_offsets(doc, names)
    start = offsets[filed]
    later = [o for o in offsets.values() if o > start]
    end = min(later) if later else len(doc)
    return start < doc.index(quote) < end


def checks(doc, spans):
    return {"in_bounds": all(0 <= s < e <= len(doc) for s, e in spans),
            "non_empty": all(doc[s:e].strip() for s, e in spans),
            "disjoint": all(spans[i][1] <= spans[i + 1][0]
                            for i in range(len(spans) - 1))}


print("== raw output below this line ==")

A = ("C. Mensah was taken to hospital. His doctor says he will be off work for "
     "at least two weeks.\nD. Laurent hurt her wrist. Her doctor says she will "
     "be off work for at least six weeks.\n")
print(repr(("[A] name offsets:", name_offsets(A, NAMES),
            "two@", A.index("off work for at least two weeks"),
            "six@", A.index("off work for at least six weeks"))))
print(repr(("[A] misattribution D. Laurent<-two weeks passes ordering?",
            ordering_ok(A, NAMES, "D. Laurent", "off work for at least two weeks"))))

B = ("C. Mensah and D. Laurent were both hurt in the loading-dock collision. "
     "Mensah will be off work for at least two weeks; Laurent for at least six weeks.\n")
CUT = B.index("Mensah will be")
print(repr(("[B] name offsets:", name_offsets(B, NAMES),
            "two@", B.index("off work for at least two weeks"),
            "six@", B.index("for at least six weeks"))))
print(repr(("[B] checks:", checks(B, [(0, CUT), (CUT, len(B))]))))
print(repr(("[B] misattribution D. Laurent<-two weeks passes ordering?",
            ordering_ok(B, NAMES, "D. Laurent", "off work for at least two weeks"))))

C = ("Two people were hurt. Six weeks off work for the second claimant, "
     "D. Laurent; C. Mensah is expected back in two weeks.\n")
print(repr(("[C] name offsets:", name_offsets(C, NAMES),
            "six@", C.index("Six weeks off work"))))
print(repr(("[C] CORRECT attribution D. Laurent<-six weeks passes ordering?",
            ordering_ok(C, NAMES, "D. Laurent", "Six weeks off work"))))
