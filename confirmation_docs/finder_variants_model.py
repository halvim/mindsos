"""CORE-C3R1 — standalone model of ConjunctionFinder.find, three phase-2 variants.

Mirrors mindsos_capacity/pipeline.py phase 1 (ds_reachable / cap_satisfiable
with a cycle stack) and phase 2 (fire + the `fired` memo) exactly. Only the
producer-admission rule differs:

  old       cap_satisfiable(p, frozenset())   -- shipped today; discards the stack
  new       p in fired or cap_satisfiable(p, live_stack)   -- the CR fix shape
  inflight  new, plus: a capacity currently under construction is ineligible

Run: python3 finder_variants_model.py
"""
import random
ALL,ANY,FOLD="all_required","any_of","fold"
class Blew(Exception): pass
class NotFound(Exception): pass

def find(caps,target,starts,variant="new",max_depth=8):
    starts_f=frozenset(starts)
    producers_of=lambda d: sorted(i for i,(_,o,_) in caps.items() if d in o)
    def ds_reachable(d,stack):
        if d in starts_f: return True
        if d in stack: return False
        return any(cap_satisfiable(c,stack|{d}) for c in producers_of(d))
    def cap_satisfiable(c,stack):
        ins=caps[c][0]
        if not ins: return True
        if caps[c][2]==ANY: return any(ds_reachable(d,stack) for d in ins)
        return all(ds_reachable(d,stack) for d in ins)
    if target in starts_f: return []
    if not any(cap_satisfiable(c,frozenset()) for c in producers_of(target)):
        raise NotFound("no satisfiable producer")
    steps,edges,fired,inflight=[],[],{},set()
    def eligible(c,stack):
        if variant=="old": return cap_satisfiable(c,frozenset())
        if variant=="inflight" and c in inflight: return False
        return c in fired or cap_satisfiable(c,stack)
    def fire(c,depth,stack):
        if c in fired: return fired[c]
        if depth>max_depth: raise Blew("depth")
        inflight.add(c)
        ins,outs,g=caps[c]; inc=[]
        for d in ins:
            if d in starts_f: inc.append((-1,d)); continue
            nxt=stack|{d}
            sat=[p for p in producers_of(d) if eligible(p,nxt)]
            if g==FOLD:
                for p in sat: inc.append((fire(p,depth+1,nxt),d))
            elif sat: inc.append((fire(sat[0],depth+1,nxt),d))
            elif g==ALL:
                inflight.discard(c); raise NotFound(f"required input {d} of {c} unproducible")
        i=len(steps); steps.append(c); fired[c]=i; inflight.discard(c)
        for pi,d in inc: edges.append((pi,i,d))
        return i
    tp=sorted(p for p in producers_of(target) if cap_satisfiable(p,frozenset()))
    fire(tp[0],0,frozenset())
    return steps,edges

def res(v,caps,t,st):
    try: s,e=find(caps,t,st,variant=v); return f"OK steps={s}"
    except Exception as ex: return f"{type(ex).__name__}: {ex}"

G={"c0":(("d2","d5"),("d5",),ANY),"c1":(("d5",),("d2",),FOLD),
   "c2":((),("d2",),ANY),"c3":((),("d2",),FOLD),"c4":((),("d5",),ANY)}
for v in ("old","new","inflight"):
    print(f"  {v:9s}:", res(v,G,"d5",{"d3","d4"}))

S1={"make_out":(("x",),("out",),ALL),"a_loop":(("out",),("x",),ALL),"b_direct":(("seed",),("x",),ALL)}
S2={"mk_root":((),("root",),ALL),"to_a":(("root",),("a",),ALL),"to_b":(("root",),("b",),ALL),"combine":(("a","b"),("out",),ALL)}
S3={"gen_0":((),("d",),ALL),"gen_1":((),("d",),ALL),"gen_2":((),("d",),ALL),"reduce":(("d",),("out",),FOLD)}
print("\nregressions:")
for nm,(c,t,s) in {"S1":(S1,"out",{"seed"}),"S2":(S2,"out",set()),"S3":(S3,"out",set())}.items():
    print(f"  {nm}: new={res('new',c,t,s)} | inflight={res('inflight',c,t,s)}")

random.seed(23); blew_new=blew_if=diff=0; n=0; ex=[]
for _ in range(20000):
    dss=[f"d{i}" for i in range(random.randint(3,6))]; caps={}
    for i in range(random.randint(2,6)):
        k=random.randint(0,2)
        caps[f"c{i}"]=(tuple(random.sample(dss,min(k,len(dss)))),(random.choice(dss),),random.choice([ALL,ANY,FOLD]))
    t=random.choice(dss); st=set(random.sample(dss,random.randint(0,2)))
    a=res("new",caps,t,st); b=res("inflight",caps,t,st); n+=1
    if a.startswith("Blew"): blew_new+=1
    if b.startswith("Blew"): blew_if+=1
    if a!=b:
        diff+=1
        if len(ex)<2: ex.append((caps,t,sorted(st),a,b))
print(f"\nsweep {n}: max_depth blowups  new={blew_new}  inflight={blew_if};  results differ {diff}")
for caps,t,st,a,b in ex:
    print("="*56)
    for k in sorted(caps): print("  ",k,"->",caps[k])
    print("   target",t,"starts",st); print("   new     :",a); print("   inflight:",b)
